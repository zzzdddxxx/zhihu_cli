"""Zhihu API client — thin async wrappers around raw HTTP calls.

All public functions are async and accept an optional Credential for
authenticated operations.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .auth import Credential
from .exceptions import AuthenticationError, NetworkError, RateLimitError, ZhihuError

logger = logging.getLogger(__name__)

_API_BASE = "https://www.zhihu.com"

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/133.0.0.0 Safari/537.36"
)


async def _request_json(
    path: str,
    credential: Credential | None = None,
    *,
    method: str = "GET",
    params: dict[str, Any] | None = None,
) -> Any:
    """Send a JSON API request to Zhihu and return parsed body.

    Attaches the login Cookie header when a credential is supplied, and maps
    HTTP/auth/network failures into local exception types.
    """
    headers = {
        "User-Agent": _USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.zhihu.com/",
    }
    if credential and credential.is_valid:
        headers["Cookie"] = credential.to_cookie_header()

    url = _API_BASE + path
    timeout = aiohttp.ClientTimeout(total=15)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.request(method, url, params=params, headers=headers) as resp:
                if resp.status in (401, 403):
                    raise AuthenticationError(f"请求 {path} 未授权 (HTTP {resp.status})")
                if resp.status == 429:
                    raise RateLimitError(f"请求 {path} 被限流 (HTTP 429)")
                if resp.status >= 400:
                    raise ZhihuError(f"请求 {path} 失败 (HTTP {resp.status})")
                try:
                    return await resp.json(content_type=None)
                except Exception:
                    return {}
    except (AuthenticationError, RateLimitError, ZhihuError):
        raise
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        raise NetworkError(f"请求 {path} 失败: {e}") from e


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------


async def get_self_info(credential: Credential) -> dict[str, Any]:
    """Get logged-in user's own info via /api/v4/me."""
    data = await _request_json("/api/v4/me", credential)
    return data if isinstance(data, dict) else {}
