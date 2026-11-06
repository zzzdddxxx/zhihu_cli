# 知乎 CLI 功能设计

## 一、项目目标

用 Python 实现一个终端知乎客户端，参照 bilibili-cli 的架构与交互体验。

- 登录方式：扫码登录（Playwright 驱动系统 Edge）/ 手动粘贴 Cookie
- 输出格式：默认 rich 表格，支持 `--json` / `--yaml`

## 二、命令规划（参照 bilibili-cli）

```
zhihu login / logout / status / whoami      # 账号
zhihu me                                    # 个人主页
zhihu user <url_token 或 uid>               # 用户主页
zhihu search <关键词> [--type all|answer|question|user]
zhihu hot                                   # 热榜
zhihu feed                                  # 推荐时间线（需登录）
zhihu answer <问题ID> ...                   # 回答相关
zhihu question <问题ID> ...                 # 问题详情
zhihu like <回答ID>                         # 点赞（写操作，需 _xsrf + 签名）
zhihu follow <用户> / unfollow <用户>       # 关注（写操作）
```

> 写操作（点赞/评论/回答/关注）除了登录态，还需要 `x-zse-96` 签名，是后续难点。
> 只读操作优先实现。

## 三、包结构（对齐 bilibili-cli）

```
zhihu_cli/
├── zhihu_cli/              # 主包
│   ├── __init__.py         # __version__
│   ├── auth.py             # 登录认证（扫码 Playwright + 凭证存取）
│   ├── client.py           # API 客户端（薄封装 + 异常映射）
│   ├── cli.py              # click 入口
│   ├── exceptions.py       # 异常体系
│   ├── formatter.py        # 输出格式化（rich/json/yaml）
│   └── commands/           # 命令模块
│       ├── account.py      # login/logout/status/whoami
│       ├── common.py       # 共享辅助
│       └── ...
├── tools/                  # 辅助工具
│   └── har_inspect.py      # HAR 分析工具
├── reference/              # 设计文档
│   ├── zhihu-login-api.md  # 登录接口分析
│   └── zhihu-cli-design.md # 本文件
└── pyproject.toml
```

## 四、技术栈

| 组件 | 用途 | 依赖 |
|---|---|---|
| click | CLI 框架 | `click>=8.0` |
| rich | 终端美化输出 | `rich>=13.0` |
| aiohttp | HTTP 客户端 | `aiohttp>=3.0` |
| playwright | 扫码登录（驱动系统浏览器） | `playwright>=1.40` |
| pillow | 二维码图片处理 | `pillow>=10.0` |
| pyyaml | YAML 输出 | `pyyaml>=6.0` |

## 五、登录态校验

- 校验接口：`GET https://www.zhihu.com/api/v4/me`
- 返回：`{ name, url_token, uid, headline, ... }`
- 判断：HTTP 200 且包含 `url_token` 即视为已登录

## 六、异常体系

```python
ZhihuError           # 基类
├── NetworkError     # 网络/超时
├── AuthenticationError  # 未登录/凭证失效
├── RateLimitError   # 被限流（403/429）
├── NotFoundError    # 资源不存在
└── SignatureError   # 签名相关错误（后续）
```

## 七、待办里程碑

1. ✅ 登录（扫码 Playwright + 手动粘贴 Cookie）
2. ⬜ 只读接口：me / user / search / hot
3. ⬜ 时间线：feed（推荐流）
4. ⬜ 写操作：点赞 / 关注 / 评论（需签名 + _xsrf）

> 实测发现 `/api/v4/me` 只需 Cookie 不需签名，只读接口可能都无需签名，见 `zhihu-reverse-notes.md`。
