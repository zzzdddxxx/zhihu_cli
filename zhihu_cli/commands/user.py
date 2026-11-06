"""User related commands."""

from __future__ import annotations

from datetime import datetime

import click
from rich.panel import Panel

from .. import client, payloads
from . import common


def _fmt_time(ts: int) -> str:
    if not ts:
        return ""
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")


def _require_cred():
    return common.require_login()


def _truncate(text: str, width: int = 100) -> str:
    text = (text or "").strip()
    return text if len(text) <= width else text[:width] + "…"


@click.command()
@click.argument("url_token")
@common.structured_output_options
def user(url_token, as_json, as_yaml):
    """查看用户主页资料。"""
    output_format = common.resolve_output_format(as_json=as_json, as_yaml=as_yaml)
    cred = _require_cred()
    try:
        info = common.run(client.get_user(url_token, cred))
    except Exception as exc:
        common.exit_error(f"获取用户信息失败: {exc}")
    if not info:
        common.exit_error(f"未找到用户: {url_token}", code="not_found")

    payload = common.success_payload({"user": payloads.normalize_user(info)})

    def render():
        name = info.get("name", "unknown")
        headline = info.get("headline", "").strip()
        ip_info = info.get("ip_info", "")
        gender = {-1: "未知", 0: "女", 1: "男"}.get(info.get("gender"), "未知")
        lines = [
            f"👤 [bold]{name}[/bold]  (@{info.get('url_token', '')})",
            f"📍 IP 属地 {ip_info}  |  ⚧ 性别 {gender}",
            f"👥 粉丝 {common.format_count(info.get('follower_count'))}  |  📝 回答 {common.format_count(info.get('answer_count'))}",
        ]
        if headline:
            lines.append(f"💬 {headline}")
        common.console.print(Panel("\n".join(lines), title="用户资料", border_style="green"))

    if common.emit_structured(payload, output_format):
        return
    render()


@click.command()
@click.argument("url_token")
@click.option("--offset", type=int, default=0, help="偏移量")
@click.option("--num", type=int, default=20, help="拉取条数（程序内自动翻页）")
@click.option("--full", is_flag=True, help="显示回答完整正文")
@common.structured_output_options
def answers(url_token, offset, num, full, as_json, as_yaml):
    """查看用户的回答列表。"""
    output_format = common.resolve_output_format(as_json=as_json, as_yaml=as_yaml)
    cred = _require_cred()
    try:
        items = common.run(_fetch(url_token, cred, client.get_user_answers, offset, num))
    except Exception as exc:
        common.exit_error(f"获取回答失败: {exc}")

    normalized = [payloads.normalize_answer(it) for it in items]
    payload = common.success_payload({"url_token": url_token, "answers": normalized})

    if common.emit_structured(payload, output_format):
        return

    if not normalized:
        common.console.print("[yellow]暂无回答[/yellow]")
        return
    for i, a in enumerate(normalized, 1):
        title = a.get("question_title", "")
        vote = common.format_count(a.get("voteup_count", 0))
        comment = common.format_count(a.get("comment_count", 0))
        flag = "  [yellow]⚠️已折叠[/yellow]" if not a.get("is_normal") else ""
        common.console.print(f"[{i}] [bold]{title}[/bold]{flag}  (👍 {vote}  💬 {comment})")
        if full:
            content = a.get("content", "") or a.get("excerpt", "")
            if content:
                common.console.print(content)
        else:
            excerpt = _truncate(a.get("excerpt", ""))
            if excerpt:
                common.console.print(f"    {excerpt}")
        common.console.print()


@click.command()
@click.argument("url_token")
@click.option("--offset", type=int, default=0, help="偏移量")
@click.option("--num", type=int, default=20, help="拉取条数（程序内自动翻页）")
@click.option("--full", is_flag=True, help="显示文章完整正文")
@common.structured_output_options
def articles(url_token, offset, num, full, as_json, as_yaml):
    """查看用户的文章列表。"""
    output_format = common.resolve_output_format(as_json=as_json, as_yaml=as_yaml)
    cred = _require_cred()
    try:
        items = common.run(_fetch(url_token, cred, client.get_user_articles, offset, num))
    except Exception as exc:
        common.exit_error(f"获取文章失败: {exc}")

    normalized = [payloads.normalize_article(it) for it in items]
    payload = common.success_payload({"url_token": url_token, "articles": normalized})

    if common.emit_structured(payload, output_format):
        return

    if not normalized:
        common.console.print("[yellow]暂无文章[/yellow]")
        return
    for i, a in enumerate(normalized, 1):
        title = a.get("title", "")
        vote = common.format_count(a.get("voteup_count", 0))
        comment = common.format_count(a.get("comment_count", 0))
        flags = []
        if a.get("is_paid"):
            flags.append("🔒付费")
        if not a.get("is_normal"):
            flags.append("[yellow]⚠️已折叠[/yellow]")
        flag_str = "  " + " ".join(flags) if flags else ""
        common.console.print(f"[{i}] [bold]{title}[/bold]{flag_str}  (👍 {vote}  💬 {comment})")
        if full:
            content = a.get("content", "") or a.get("excerpt", "")
            if content:
                common.console.print(content)
            if a.get("is_paid"):
                common.console.print("[yellow]（付费专栏内容，以上为免费预览，完整正文需付费）[/yellow]")
        else:
            excerpt = _truncate(a.get("excerpt", ""))
            if excerpt:
                common.console.print(f"    {excerpt}")
        common.console.print()


@click.command()
@click.argument("url_token")
@click.option("--offset", type=int, default=0, help="偏移量")
@click.option("--num", type=int, default=20, help="拉取条数（程序内自动翻页）")
@common.structured_output_options
def pins(url_token, offset, num, as_json, as_yaml):
    """查看用户的想法列表。"""
    output_format = common.resolve_output_format(as_json=as_json, as_yaml=as_yaml)
    cred = _require_cred()
    try:
        items = common.run(_fetch(url_token, cred, client.get_user_pins, offset, num))
    except Exception as exc:
        common.exit_error(f"获取想法失败: {exc}")

    normalized = [payloads.normalize_pin(it) for it in items]
    payload = common.success_payload({"url_token": url_token, "pins": normalized})

    if common.emit_structured(payload, output_format):
        return

    if not normalized:
        common.console.print("[yellow]暂无想法[/yellow]")
        return
    for i, p in enumerate(normalized, 1):
        content = _truncate(p.get("content", ""))
        like = common.format_count(p.get("like_count", 0))
        comment = common.format_count(p.get("comment_count", 0))
        day = _fmt_time(p.get("created", 0))
        common.console.print(f"[{i}] [{day}] {content}  (👍 {like}  💬 {comment})")


@click.command()
@click.argument("url_token")
@click.option("--offset", type=int, default=0, help="偏移量")
@click.option("--num", type=int, default=None, help="拉取条数（默认拉全部）")
@common.structured_output_options
def following(url_token, offset, num, as_json, as_yaml):
    """查看用户的关注列表（默认拉全部）。"""
    output_format = common.resolve_output_format(as_json=as_json, as_yaml=as_yaml)
    cred = _require_cred()
    try:
        items = common.run(_fetch(url_token, cred, client.get_followees, offset, num))
    except Exception as exc:
        common.exit_error(f"获取关注列表失败: {exc}")

    normalized = [payloads.normalize_followee(it) for it in items]
    payload = common.success_payload({"url_token": url_token, "followees": normalized})

    if common.emit_structured(payload, output_format):
        return

    if not normalized:
        common.console.print("[yellow]暂无关注[/yellow]")
        return
    for i, f in enumerate(normalized, 1):
        name = f.get("name", "")
        token = f.get("url_token", "")
        headline = f.get("headline", "")
        line = f"[{i}] [bold]{name}[/bold] (@{token})"
        if headline:
            line += f"  |  {_truncate(headline, 40)}"
        common.console.print(line)


async def _fetch(url_token, cred, client_fn, offset, num):
    async def page_fn(o, l):
        return await client_fn(url_token, cred, o, l)

    return await common.fetch_paged(page_fn, offset=offset, num=num)
