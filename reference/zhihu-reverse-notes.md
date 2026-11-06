# 知乎逆向与登录技术笔记

> 沉淀自本次探索过程（2026-11-06），记录知乎反爬签名机制、登录方案选型、关键实测结论与分析方法论。

## 一、反爬签名机制（深度）

### 1.1 三个签名头

| 头 | 格式 | 用途 |
|---|---|---|
| `x-zse-96` | `2.0_<base64>` | 大多数 v3/v4 接口 |
| `x-zst-81` | `3_2.0<base64>` | sign_in 等敏感接口 |
| `x-zse-93` | 同族 | 与 x-zse-96 同源生成 |

### 1.2 平台前缀（x-zst-81 的 `3_2.0` 含义）

从签名 JS 里还原出的枚举：

```js
A.iOS = "5_2.0"
A.Android = "4_2.0"
A.Web = "3_2.0"
```

即前缀第一位 = 平台：`3`=Web、`4`=Android、`5`=iOS。

### 1.3 签名代码位置（从 HAR 精确定位）

在 `www.zhihu.com.har` 的 `static.zhihu.com` 167 个静态文件里，用关键词 `x-zse-96`/`x-zst-81`/`x-zse-93` 搜索，命中：

| 文件 | 大小 | 角色 |
|---|---|---|
| `shared-5a466425912c9d1a.js` | 59KB | **签名框架层**（拦截器、header 名、平台前缀） |
| `3964.app.js` | 3.5MB | **encryptor 加密核心**（实际算法） |
| `main.app.js` | 2.6MB | 部分加密逻辑 |

> 定位方法：搜索签名头字符串 → 命中文件 → 打印关键词上下文 → 追 webpack 模块引用（`e("xxx")`）。

### 1.4 签名架构（还原的调用链）

```
拦截器 Ao  ── 决定"何时签名、注入哪些 header"
   ├── x-zst-81  ← 外部传入 (A.xZst81)，非本地计算
   ├── x-zse-96  ← Ai() 现场算
   └── 平台前缀  ← z() 函数按平台选择

Ai(body, {zse93, xAppVersion, authId, xUDId, xZst81}, encryptor)
   └── encryptor  ← 真正加密算法，外部注入（在 3964.app.js）
```

关键结论：`shared-xxx.js` 只是"壳"，真正的加密器 `encryptor` 和 `x-zst-81` 生成逻辑是**外部注入**的，散在大 chunk 里。因此"下载即用"不可行，需要抠模块 + 补环境。

### 1.5 现成方案对照

- **MediaCrawler 的 `zhihu.js`**（约 200 行）：已从知乎 VMP 混淆 JS 抠好，提供 `get_sign(url, cookies)` 返回 `{x-zst-81, x-zse-96}`。
- 但其中 `x-zst-81` 是**硬编码常量**，只够普通 API 用，**不适用于 sign_in 登录**。
- sign_in 需要动态 `x-zst-81` + 加密请求体，是最难逆向的部分（连 MediaCrawler 都绕开、改用浏览器）。

## 二、登录方案（最终采用 Playwright）

### 2.1 为什么选 Playwright

| 方案 | 结论 |
|---|---|
| browser-cookie3 提取 Cookie | ❌ 实测不好使（Windows Chrome 加密，且缺签名） |
| 纯 HTTP + 逆向签名 | ❌ sign_in 动态签名 + 加密体逆向工作量大 |
| **Playwright 浏览器自动化** | ✅ 让真实浏览器代算签名，绕开逆向 |

核心思想：**登录动作在真实浏览器里完成，签名由浏览器内部自动算，我们只需"指挥浏览器 + 拿结果"**。

### 2.2 实现要点

```
qr_login()
  ├─ launch(channel="msedge")       # 复用系统 Edge，免下载 150MB chromium
  ├─ goto("/signin")                # 浏览器渲染 + 算好签名
  ├─ locator("canvas.Qrcode-qrcode").screenshot()  # 截二维码图
  ├─ 保存 PNG + os.startfile 打开   # 图片清晰，手机必扫得
  └─ 轮询 context.cookies() 检测 z_c0 出现 = 登录成功
```

关键 Cookie 提取：`z_c0`（登录凭证）、`d_c0`（设备指纹）、`_xsrf`（CSRF）。

### 2.3 踩坑记录

1. **终端 ASCII 二维码扫不了**：半块字符 `▀▄█` 让二维码纵向压缩变形，扫描器识别失败。→ 改为截图 PNG 自动打开。
2. **canvas 截图透明背景**：`convert("L")` 会把透明像素当黑色，产生噪点。→ 先合成白底再处理。
3. **playwright 装错环境**：pip 到了全局 Python 3.13，而 conda 环境是 3.12，`greenlet` 的 cp313 pyd 不兼容。→ 装回 conda 环境。
4. **无需下载 chromium**：`channel="msedge"` 直接复用系统 Edge/Chrome。

## 三、关键实测结论

1. **`/api/v4/me` 只需 `z_c0` Cookie，不需要 `x-zse-96` 签名**（已实测通过）。这暗示基础只读接口可能都不需要签名，只读功能开发门槛大大降低。
2. 扫码登录成功后，浏览器 Cookie 里 `q_c0` 可能为空，但 `z_c0` 才是核心，不影响鉴权。
3. 登录凭证有效期约 180 天（`expires_in: 15551999`）。

## 四、HAR 分析方法论（可复用）

五步漏斗：

1. **概览**：统计 host 分布，区分「业务接口 vs 静态资源 vs 埋点」，扔掉 80% 噪音。
2. **语义过滤**：用 URL 关键词（login/sign/token/qrcode/me）筛出目标接口。
3. **时间线排序**：用 `startedDateTime` 还原调用先后，识别依赖链。
4. **单请求深挖**：看 method/URL/关键 header/POST body/响应 set-cookie。
5. **凭证流转**：交叉验证凭证（cookie/token）如何在后续请求复用。

找签名代码的通用心法：**签名代码一定有特征字符串，搜特征字符串 → 定位文件 → 看上下文 → 追模块依赖 → 拼架构**。

工具：`tools/har_inspect.py`（`-H` 过滤域名、`-k` 关键词、`-t` 时间线、`-i` 深挖）。
