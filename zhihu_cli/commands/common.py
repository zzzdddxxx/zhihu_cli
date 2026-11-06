"""Shared helpers for CLI command modules."""

from __future__ import annotations

import logging
import sys

import click

from .. import auth
from ..exceptions import AuthenticationError, NetworkError, RateLimitError, ZhihuError
from ..formatter import (
    console,
    emit_structured,
    error_payload,
    exit_error,
    format_count,
    resolve_output_format,
    structured_output_options,
    success_payload,
)

__all__ = [
    "setup_logging",
    "run",
    "get_credential",
    "clear_credential",
    "print_login_required",
    "require_login",
    "console",
    "emit_structured",
    "error_payload",
    "exit_error",
    "format_count",
    "resolve_output_format",
    "structured_output_options",
    "success_payload",
    "AuthenticationError",
    "NetworkError",
    "RateLimitError",
    "ZhihuError",
    "fetch_paged",
]


def setup_logging(verbose: bool):
    """Configure global logging based on CLI verbosity."""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(name)s: %(message)s")


def run(coro):
    """Bridge async coroutine into synchronous click command."""
    import asyncio

    return asyncio.run(coro)


def get_credential(mode: auth.AuthMode = "read"):
    """Read credential from configured auth strategy."""
    return auth.get_credential(mode=mode)


def clear_credential():
    """Remove saved credential."""
    return auth.clear_credential()


def print_login_required(message: str | None = None):
    """Print a standard login-required warning message."""
    if message:
        console.print(f"[yellow]⚠️  {message}[/yellow]")
        return
    console.print("[yellow]⚠️  需要登录。使用 [bold]zhihu login[/bold] 登录。[/yellow]")


def require_login(require_write: bool = False, message: str | None = None):
    """Require login credential and optional write capability."""
    mode: auth.AuthMode = "write" if require_write else "read"
    cred = get_credential(mode=mode)
    if cred:
        return cred

    if require_write:
        saved = get_credential(mode="optional")
        if saved and saved.z_c0 and not saved.xsrf:
            exit_error(
                "当前登录凭证不支持写操作（缺少 _xsrf）。请执行 zhihu login 重新登录。",
                code="permission_denied",
            )

    print_login_required(message)
    sys.exit(1)


async def fetch_paged(page_fn, offset: int = 0, num: int | None = None, page_size: int = 20):
    """通用分页拉取。``page_fn(offset, limit) -> {"data": [...], "paging": {...}}``。

    - ``num=None``：拉全部（翻页到底，直到 ``paging.is_end``）
    - ``num=N``：最多拉 N 条
    - 翻页之间随机 sleep 0.5~1.5s，降低被限流风险
    """
    import asyncio
    import random

    results = []
    cur = offset
    first = True
    while num is None or len(results) < num:
        if not first:
            await asyncio.sleep(random.uniform(0.5, 1.5))
        first = False
        data = await page_fn(cur, page_size)
        items = data.get("data", []) if isinstance(data, dict) else []
        if not items:
            break
        results.extend(items)
        cur += len(items)
        paging = data.get("paging", {}) if isinstance(data, dict) else {}
        if paging.get("is_end"):
            break
    return results if num is None else results[:num]
