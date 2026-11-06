"""Search commands."""

from __future__ import annotations

import click

from .. import client, payloads
from . import common


@click.command()
@click.argument("keyword")
@click.option(
    "--type", "search_type", required=True,
    type=click.Choice(["people", "content", "answer", "article", "pin", "zvideo"]),
    help="搜索类型",
)
@click.option("--top", type=int, default=None, help="取前 N 个（people 下按粉丝数降序）")
@click.option("--num", type=int, default=20, help="拉取条数（程序内自动翻页）")
@click.option("--offset", type=int, default=0, help="偏移量")
@common.structured_output_options
def search(keyword, search_type, top, num, offset, as_json, as_yaml):
    """搜索知乎内容（用户 / 文章 / 回答等）。"""
    output_format = common.resolve_output_format(as_json=as_json, as_yaml=as_yaml)
    cred = common.get_credential(mode="optional")

    try:
        items = common.run(_search(keyword, search_type, top, num, offset, cred))
    except Exception as exc:
        common.exit_error(f"搜索失败: {exc}")

    normalized = [_normalize_item(search_type, it) for it in items]
    payload = common.success_payload(
        {"keyword": keyword, "type": search_type, "results": normalized}
    )

    if common.emit_structured(payload, output_format):
        return
    _render(normalized)


async def _search(keyword, search_type, top, num, offset, cred):
    count = top if top is not None else num

    async def page_fn(o, l):
        return await client.search(keyword, cred, search_type, o, l)

    items = await common.fetch_paged(page_fn, offset=offset, num=count)
    if search_type == "people" and top is not None:
        items.sort(
            key=lambda it: (it.get("object", {}) or {}).get("follower_count", 0),
            reverse=True,
        )
        items = items[:top]
    return items


def _normalize_item(search_type, item):
    if search_type == "people":
        return payloads.normalize_search_user(item.get("object", {}) or {})
    return item.get("object", item)


def _render(normalized):
    if not normalized:
        common.console.print("[yellow]未找到结果[/yellow]")
        return
    for i, u in enumerate(normalized, 1):
        name = u.get("name", "")
        token = u.get("url_token", "")
        follower = common.format_count(u.get("follower_count", 0))
        headline = u.get("headline", "")
        line = f"[{i}] [bold]{name}[/bold] (@{token})  粉丝 {follower}"
        if headline:
            line += f"  |  {headline}"
        common.console.print(line)
