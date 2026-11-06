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


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


async def search(
    keyword: str,
    credential: Credential | None = None,
    search_type: str = "people",
    offset: int = 0,
    limit: int = 20,
) -> dict[str, Any]:
    """Search Zhihu. ``search_type`` maps to the ``t`` param.

    Supported types: people / content / answer / article / pin / zvideo.
    """
    params = {
        "t": search_type,
        "q": keyword,
        "correction": 1,
        "offset": offset,
        "limit": limit,
    }
    data = await _request_json("/api/v4/search_v3", credential, params=params)
    return data if isinstance(data, dict) else {}


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------


_USER_INCLUDE = (
    "allow_message,is_followed,is_following,is_org,is_blocking,employments,"
    "answer_count,articles_count,follower_count,follower_count_text,gender,"
    "badge[?(type=best_answerer)].topics"
)

_ANSWERS_INCLUDE = (
    "data[*].is_normal,admin_closed_comment,reward_info,is_collapsed,annotation_action,"
    "annotation_detail,collapse_reason,collapsed_by,suggest_edit,comment_count,can_comment,"
    "content,editable_content,attachment,voteup_count,reshipment_settings,comment_permission,"
    "created_time,updated_time,review_info,excerpt,paid_info,reaction_instruction,is_labeled,"
    "label_info,relationship.is_authorized,voting,is_author,is_thanked,is_nothelp,reaction,"
    "vessay_info;data[*].author.badge[?(type=best_answerer)].topics;data[*].author.kvip_info;"
    "data[*].author.vip_info;data[*].question.has_publishing_draft,relationship"
)

_PINS_INCLUDE = "data[*].upvoted_followees,admin_closed_comment,reaction"

_FOLLOWEES_INCLUDE = (
    "data[*].answer_count,articles_count,gender,follower_count,follower_count_text,"
    "is_followed,is_following,badge[?(type=best_answerer)].topics"
)

_ARTICLES_INCLUDE = (
    "data[*].comment_count,suggest_edit,is_normal,thumbnail_extra_info,thumbnail,can_comment,"
    "comment_permission,admin_closed_comment,content,voteup_count,created,updated,"
    "upvoted_followees,voting,review_info,reaction_instruction,is_labeled,label_info,reaction,"
    "vessay_info;data[*].author.badge[?(type=best_answerer)].topics;data[*].author.kvip_info;"
    "data[*].author.vip_info"
)


async def get_user(url_token: str, credential: Credential | None = None) -> dict[str, Any]:
    """Get a user profile via /api/v4/members/{url_token}."""
    data = await _request_json(
        f"/api/v4/members/{url_token}", credential, params={"include": _USER_INCLUDE}
    )
    return data if isinstance(data, dict) else {}


async def get_user_answers(
    url_token: str,
    credential: Credential | None = None,
    offset: int = 0,
    limit: int = 20,
) -> dict[str, Any]:
    """Get a user's answers via /api/v4/members/{url_token}/answers."""
    params = {"offset": offset, "limit": limit, "sort_by": "created", "include": _ANSWERS_INCLUDE}
    data = await _request_json(f"/api/v4/members/{url_token}/answers", credential, params=params)
    return data if isinstance(data, dict) else {}


async def get_user_articles(
    url_token: str,
    credential: Credential | None = None,
    offset: int = 0,
    limit: int = 20,
) -> dict[str, Any]:
    """Get a user's articles (专栏文章) via /api/v4/members/{url_token}/articles."""
    params = {"offset": offset, "limit": limit, "sort_by": "created", "include": _ARTICLES_INCLUDE}
    data = await _request_json(f"/api/v4/members/{url_token}/articles", credential, params=params)
    return data if isinstance(data, dict) else {}


async def get_user_pins(
    url_token: str,
    credential: Credential | None = None,
    offset: int = 0,
    limit: int = 20,
) -> dict[str, Any]:
    """Get a user's pins (想法) via /api/v4/v2/pins/{url_token}/moments."""
    params = {"offset": offset, "limit": limit, "includes": _PINS_INCLUDE}
    data = await _request_json(f"/api/v4/v2/pins/{url_token}/moments", credential, params=params)
    return data if isinstance(data, dict) else {}


async def get_followees(
    url_token: str,
    credential: Credential | None = None,
    offset: int = 0,
    limit: int = 20,
) -> dict[str, Any]:
    """Get a user's followees (关注列表) via /api/v4/members/{url_token}/followees."""
    params = {"offset": offset, "limit": limit, "include": _FOLLOWEES_INCLUDE}
    data = await _request_json(f"/api/v4/members/{url_token}/followees", credential, params=params)
    return data if isinstance(data, dict) else {}
