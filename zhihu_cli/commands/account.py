"""Account and authentication related commands."""

from __future__ import annotations

import sys

import click
from rich.panel import Panel

from .. import auth, client, payloads
from . import common


@click.command()
@click.option("--cookie", default=None, help="手动粘贴知乎 Cookie（z_c0=...; d_c0=...; _xsrf=...）")
@click.option("--headed", is_flag=True, help="弹出浏览器窗口扫码（默认无头模式，截图二维码图片）")
def login(cookie, headed):
    """扫码登录知乎（默认截图二维码图片并自动打开，用知乎 App 扫码）。"""
    try:
        if cookie:
            auth.login_with_cookie(cookie)
        else:
            auth.qr_login(headless=not headed)
    except common.AuthenticationError as e:
        common.exit_error(str(e))
    except Exception as e:
        common.exit_error(f"登录失败: {e}")

    common.console.print("[green]✅ 登录成功，凭证已保存[/green]")


@click.command()
def logout():
    """注销并清除保存的凭证。"""
    common.clear_credential()
    common.console.print("[green]✅ 已注销，凭证已清除[/green]")


@click.command()
@common.structured_output_options
def status(as_json: bool, as_yaml: bool):
    """检查登录状态。"""
    output_format = common.resolve_output_format(as_json=as_json, as_yaml=as_yaml)
    cred = common.get_credential(mode="read")
    if not cred:
        payload = common.error_payload("not_authenticated", "未登录。使用 zhihu login 登录。")
        if common.emit_structured(payload, output_format):
            raise SystemExit(1) from None
        common.print_login_required("未登录。使用 [bold]zhihu login[/bold] 登录。")
        sys.exit(1)

    try:
        info = common.run(client.get_self_info(cred))
    except Exception as exc:
        common.exit_error(f"检查登录状态失败: {exc}")

    payload = common.success_payload(
        {"authenticated": True, "user": payloads.normalize_user(info)}
    )

    def render() -> None:
        name = info.get("name", "unknown")
        url_token = info.get("url_token", "unknown")
        common.console.print(f"[green]✅ 已登录：[bold]{name}[/bold]  (url_token: {url_token})[/green]")

    if common.emit_structured(payload, output_format):
        return
    render()


@click.command()
@common.structured_output_options
def whoami(as_json: bool, as_yaml: bool):
    """查看当前登录用户的详细信息。"""
    output_format = common.resolve_output_format(as_json=as_json, as_yaml=as_yaml)
    cred = common.get_credential(mode="read")
    if not cred:
        payload = common.error_payload("not_authenticated", "未登录。使用 zhihu login 登录。")
        if common.emit_structured(payload, output_format):
            raise SystemExit(1) from None
        common.print_login_required("未登录。使用 [bold]zhihu login[/bold] 登录。")
        sys.exit(1)

    try:
        info = common.run(client.get_self_info(cred))
    except Exception as exc:
        common.exit_error(f"获取用户信息失败: {exc}")

    payload = common.success_payload({"user": payloads.normalize_user(info)})

    def render() -> None:
        name = info.get("name", "unknown")
        url_token = info.get("url_token", "")
        headline = info.get("headline", "").strip()
        ip_info = info.get("ip_info", "")
        gender = {-1: "未知", 0: "女", 1: "男"}.get(info.get("gender"), "未知")

        lines = [
            f"👤 [bold]{name}[/bold]  (@{url_token})",
            f"📍 IP 属地 {ip_info}  |  ⚧ 性别 {gender}",
            f"📝 回答 {common.format_count(info.get('answer_count'))}  |  ❓ 提问 {common.format_count(info.get('question_count'))}",
            f"👍 获赞 {common.format_count(info.get('voteup_count'))}  |  💝 被感谢 {common.format_count(info.get('thanked_count'))}",
        ]
        if headline:
            lines.append(f"💬 {headline}")

        common.console.print(Panel("\n".join(lines), title="个人信息", border_style="green"))

    if common.emit_structured(payload, output_format):
        return
    render()
