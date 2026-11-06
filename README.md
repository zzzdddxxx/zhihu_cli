# zhihu-cli

终端里的知乎客户端（Python）。

## 功能

- 登录：扫码登录（Playwright 驱动系统浏览器，终端显示二维码）
- 账号：`login` / `logout` / `status` / `whoami`

## 环境

- Python（conda 环境，如 `zhihu`）
- 依赖：`click` / `rich` / `aiohttp` / `playwright` / `pillow` / `pyyaml`
- 浏览器：系统自带 Edge / Chrome（Playwright 直接调用，无需下载 chromium）

```bash
pip install playwright click rich aiohttp pillow pyyaml
```

## 使用（源码运行，无需安装）

```bash
# 在项目根目录执行
python -m zhihu_cli.cli --help
python -m zhihu_cli.cli login              # 扫码登录（终端显示二维码）
python -m zhihu_cli.cli login --headed     # 弹出浏览器窗口扫码
python -m zhihu_cli.cli login --cookie "z_c0=...; d_c0=...; _xsrf=..."  # 手动粘贴
python -m zhihu_cli.cli status             # 检查登录状态
python -m zhihu_cli.cli whoami             # 查看当前用户信息
python -m zhihu_cli.cli logout             # 注销
```

## 目录结构

```
zhihu_cli/           主包
tools/               辅助工具（har_inspect.py）
reference/           设计文档（接口分析、功能设计）
```

## 说明

- 登录态凭证保存在 `~/.zhihu-cli/credential.json`
- 扫码登录通过 Playwright 驱动系统 Edge/Chrome，登录态写入浏览器 Cookie 后提取保存
- 写操作（点赞/评论/回答）需要 `x-zse-96` 签名，暂未实现
