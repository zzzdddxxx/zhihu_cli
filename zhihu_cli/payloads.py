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


def _strip_html(text: object) -> str:
    """Remove HTML tags (e.g. <em> highlighted names)."""
    if not isinstance(text, str):
        return ""
    import re

    return re.sub(r"<[^>]+>", "", text).strip()


def html_to_text(html_str: object) -> str:
    """HTML 转纯文本，保留段落换行（用于回答/想法正文）。"""
    if not isinstance(html_str, str) or not html_str:
        return ""
    import html
    import re

    # 段落/换行类标签转成换行
    text = re.sub(r"<(?:p|br|div|li|h[1-6]|blockquote)[^>]*>", "\n", html_str)
    # 去掉剩余标签
    text = re.sub(r"<[^>]+>", "", text)
    # 处理 HTML 实体
    text = html.unescape(text)
    # 清理空白
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_search_user(obj: dict[str, Any]) -> dict[str, Any]:
    """Normalize a search result's user object (search_v3 → data[].object)."""
    return {
        "url_token": obj.get("url_token", ""),
        "name": _strip_html(obj.get("name", "")),
        "headline": obj.get("headline", ""),
        "gender": _to_int(obj.get("gender"), -1),
        "follower_count": _to_int(obj.get("follower_count"), 0),
        "answer_count": _to_int(obj.get("answer_count"), 0),
        "voteup_count": _to_int(obj.get("voteup_count"), 0),
    }


def normalize_answer(item: dict[str, Any]) -> dict[str, Any]:
    """Normalize an answer dict (members/{token}/answers → data[])."""
    question = item.get("question", {}) if isinstance(item.get("question"), dict) else {}
    author = item.get("author", {}) if isinstance(item.get("author"), dict) else {}
    return {
        "id": str(item.get("id", "")),
        "excerpt": _strip_html(item.get("excerpt", "")),
        "content": html_to_text(item.get("content", "")),
        "voteup_count": _to_int(item.get("voteup_count"), 0),
        "comment_count": _to_int(item.get("comment_count"), 0),
        "created_time": _to_int(item.get("created_time"), 0),
        "question_title": _strip_html(question.get("title", "")),
        "question_id": str(question.get("id", "")),
        "author_name": author.get("name", ""),
        "url": item.get("url", ""),
    }


def normalize_pin(item: dict[str, Any]) -> dict[str, Any]:
    """Normalize a pin/想法 dict (v2/pins/{token}/moments → data[])."""
    content = _strip_html(item.get("content", "")) or _strip_html(item.get("excerpt_title", ""))
    return {
        "id": str(item.get("id", "")),
        "content": content,
        "like_count": _to_int(item.get("like_count"), 0),
        "comment_count": _to_int(item.get("comment_count"), 0),
        "repin_count": _to_int(item.get("repin_count"), 0),
        "favorite_count": _to_int(item.get("favorite_count"), 0),
        "created": _to_int(item.get("created"), 0),
        "url": item.get("url", ""),
    }


def normalize_followee(obj: dict[str, Any]) -> dict[str, Any]:
    """Normalize a followee dict (members/{token}/followees → data[])."""
    return {
        "url_token": obj.get("url_token", ""),
        "name": _strip_html(obj.get("name", "")),
        "headline": obj.get("headline", ""),
        "gender": _to_int(obj.get("gender"), -1),
        "follower_count": _to_int(obj.get("follower_count"), 0),
        "answer_count": _to_int(obj.get("answer_count"), 0),
        "is_following": bool(obj.get("is_following")),
        "is_followed": bool(obj.get("is_followed")),
    }
