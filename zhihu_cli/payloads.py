"""Stable structured payload builders for zhihu-cli commands."""

from __future__ import annotations

from typing import Any


def _to_int(value: object, default: int = 0) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default


def normalize_user(info: dict[str, Any]) -> dict[str, Any]:
    """Normalize a Zhihu user dict (from /api/v4/me or member endpoints)."""
    return {
        "id": str(info.get("id", "")),
        "uid": str(info.get("uid", "")),
        "url_token": info.get("url_token", ""),
        "name": info.get("name", ""),
        "headline": info.get("headline", ""),
        "gender": _to_int(info.get("gender"), -1),
        "ip_info": info.get("ip_info", ""),
        "answer_count": _to_int(info.get("answer_count"), 0),
        "question_count": _to_int(info.get("question_count"), 0),
        "favorite_count": _to_int(info.get("favorite_count"), 0),
        "voteup_count": _to_int(info.get("voteup_count"), 0),
        "thanked_count": _to_int(info.get("thanked_count"), 0),
        "following_count": _to_int(info.get("following_count"), 0),
        "follower_count": _to_int(info.get("follower_count"), 0),
    }
