# 知乎登录接口分析

> 来源：`D:\download\www.zhihu.com.har`（一次完整的手机扫码登录抓包，327 个请求）
> 工具：`tools/har_inspect.py`

## 一、登录态关键凭证

知乎登录后，身份凭证主要靠 Cookie 传递（不是 Authorization 头）：

| Cookie | 作用 | 是否必须 |
|---|---|---|
| `z_c0` | **登录凭证（核心）**，绝大多数接口用它鉴权 | ✅ 必须 |
| `q_c0` | 登录态辅助标识 | 建议保留 |
| `d_c0` | 设备指纹，未登录时也会有，用于反爬 | 建议保留 |
| `_xsrf` | CSRF token，写操作（点赞/评论/回答）需要 | 写操作必须 |

> 结论：只读接口（`/api/v4/me`、feed、搜索等）只要 `z_c0` 就能访问。

## 二、扫码登录完整流程（从 HAR 还原）

```
① GET  https://www.zhihu.com/                          预热，获取 d_c0/_xsrf 等基础 Cookie
② GET  /api/v3/oauth/captcha/v2                        探测是否需要验证码（本次未触发）
③ POST /api/v3/account/api/login/qrcode                生成二维码
       headers: x-zse-96 签名 + x-xsrftoken
       resp:    二维码 token（UUID 片段）
④ GET  /api/v3/account/api/login/qrcode/{token}/scan_info   轮询扫码状态（每 2s，本次轮询 9 次）
       状态：未扫码 → 已扫码待确认 → 已确认（下发临时凭证）
⑤ POST /api/account/prod/token/refresh                 刷新 token
⑥ POST /api/v3/oauth/sign_in                           正式登录（关键一步）
       headers: x-zst-81 签名
       body:    application/x-www-form-urlencoded 加密表单（前端 JS 加密）
       resp:    access_token + refresh_token + z_c0 + q_c0
⑦ GET  /api/v4/me                                      校验登录态 + 获取用户信息
```

### 实测时间线（2026-11-06）

```
05:42:55  GET  qrcode/{token1}/scan_info    查上一个遗留二维码
05:42:56  POST account/api/login/qrcode     生成新二维码
05:42:58→14 GET qrcode/{token2}/scan_info ×9 轮询扫码状态
05:43:15  POST account/prod/token/refresh   扫码成功刷新凭证
05:43:15  POST oauth/sign_in                正式登录
05:43:15  GET  api/v4/me ×3                 拉取用户信息
```

## 三、sign_in 响应示例

```json
{
  "uid": "26ac4ce6fcb1eb2126fea536842ae05f",
  "user_id": 1229742266949775360,
  "token_type": "bearer",
  "access_token": "2.1MSJWGgAAAACcQFSIPpjRGyY...",
  "refresh_token": "2.164971681a3aa940f1835424e",
  "expires_in": 15551999,
  "cookie": { "q_c0": "2|1:0|...", "z_c0": "2|1:0|..." }
}
```

## 四、反爬签名（登录的最大障碍）

| 头 | 格式 | 用途 | 难度 |
|---|---|---|---|
| `x-zse-96` | `2.0_<base64>` | 大多数 v3/v4 接口 | 社区有逆向实现 |
| `x-zst-81` | `3_2.0<base64>` | sign_in 等敏感接口 | 更强，需逆向 JS |
| `x-xsrftoken` | 明文 | CSRF，从 `_xsrf` Cookie 取 | 简单 |

> 这些签名由知乎前端 JS 动态生成，算法藏在 `static.zhihu.com` 的加密模块里（签名代码定位见 `zhihu-reverse-notes.md`）。

> **实测结论**：`/api/v4/me` 只需 `z_c0` Cookie，不需要签名。但 browser-cookie3 提取 Cookie 在 Windows 上实测不好使，最终采用 Playwright 扫码登录。

## 五、登录方案（最终采用）

实测后确定：

1. **扫码登录（主）**：Playwright 驱动系统 Edge，截图二维码图片自动打开，手机扫码。绕开签名，已跑通。
2. **手动粘贴 Cookie（兜底）**：`zhihu login --cookie "z_c0=...; d_c0=...; _xsrf=..."`

> browser-cookie3 提取 Cookie 实测不好使（Windows Chrome 加密），已弃用。
> 扫码登录实现细节与踩坑见 `zhihu-reverse-notes.md`。
