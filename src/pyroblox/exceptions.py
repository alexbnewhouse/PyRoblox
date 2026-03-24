"""Exception hierarchy for pyroblox."""

from __future__ import annotations


class PyRobloxError(Exception):
    """Base exception for all pyroblox errors."""


class RobloxAPIError(PyRobloxError):
    """Raised when the Roblox API returns an error response."""

    def __init__(
        self, status_code: int, errors: list[dict[str, object]], url: str
    ) -> None:
        self.status_code = status_code
        self.errors = errors
        self.url = url
        messages = [str(e.get("message", "")) for e in errors if e.get("message")]
        detail = "; ".join(messages) if messages else f"HTTP {status_code}"
        super().__init__(f"{detail} (url={url})")


class RateLimitError(RobloxAPIError):
    """Raised when rate limited (HTTP 429) after exhausting retries."""

    def __init__(
        self,
        errors: list[dict[str, object]],
        url: str,
        retry_after: float | None = None,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(429, errors, url)


class AuthenticationError(RobloxAPIError):
    """Raised on 401/403 responses."""


class NotFoundError(RobloxAPIError):
    """Raised on 404 responses."""
