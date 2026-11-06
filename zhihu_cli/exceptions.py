"""Custom exceptions for zhihu-cli."""


class ZhihuError(Exception):
    """Base exception for zhihu-cli errors."""


class NetworkError(ZhihuError):
    """Raised when upstream network/API requests fail."""


class AuthenticationError(ZhihuError):
    """Raised when authentication data is missing or invalid."""


class RateLimitError(ZhihuError):
    """Raised when Zhihu rate-limits the request (HTTP 403/429)."""


class NotFoundError(ZhihuError):
    """Raised when a question, answer, or user is not found."""


class SignatureError(ZhihuError):
    """Raised when x-zse-96/x-zst-81 signature generation fails."""
