"""Exceptions raised by PyRoblox.

Every error the library raises on purpose derives from :class:`RobloxError`, so
callers can catch that one class to handle "anything Roblox-related went wrong".
The subclasses map to the HTTP outcomes that matter to a researcher:

* :class:`NotFoundError` (404) – the user, group, game, or asset does not exist
  or was deleted.
* :class:`PrivateError` (403) – it exists but Roblox will not show it to you
  (private inventory, hidden friends list, and so on).
* :class:`AuthRequiredError` (401) – the endpoint needs a logged-in cookie.
* :class:`BadRequestError` (400) – Roblox rejected the request, usually with a
  message such as "The user is invalid" for banned accounts.
* :class:`RateLimitedError` (429) – Roblox is throttling this IP and the retries
  were exhausted. Wait a minute and try again.
* :class:`ServerError` (5xx) – Roblox itself is failing.

:class:`AuthenticationError` is the shared parent of the 401 and 403 errors, and
the names ``PyRobloxError``, ``RobloxAPIError``, and ``RateLimitError`` are kept
as aliases for code written against the March 2026 ``pyroblox`` API.
"""

from __future__ import annotations

from typing import Any, Optional


class RobloxError(Exception):
    """Base class for all PyRoblox errors."""

    def __init__(self, message: str, *, status: Optional[int] = None,
                 url: Optional[str] = None, roblox_message: Optional[str] = None,
                 errors: Optional[list[dict[str, Any]]] = None):
        self.status = status
        self.url = url
        self.roblox_message = roblox_message
        #: Roblox's ``errors`` array from the response body, when there was one.
        self.errors: list[dict[str, Any]] = list(errors or [])
        text = message
        if roblox_message:
            text = f"{message} (Roblox says: {roblox_message})"
        if url:
            text = f"{text} [{url}]"
        super().__init__(text)

    @property
    def status_code(self) -> Optional[int]:
        """Alias of :attr:`status` (March 2026 API name)."""
        return self.status


class NotFoundError(RobloxError):
    """HTTP 404: the entity does not exist or has been deleted."""


class AuthenticationError(RobloxError):
    """Parent of the two access-denied errors (HTTP 401 and 403)."""


class PrivateError(AuthenticationError):
    """HTTP 403: the entity exists but is private or hidden from you."""


class AuthRequiredError(AuthenticationError):
    """HTTP 401: this endpoint needs a valid .ROBLOSECURITY cookie."""


class BadRequestError(RobloxError):
    """HTTP 400: Roblox rejected the request (for example a banned user id)."""


class RateLimitedError(RobloxError):
    """HTTP 429 persisted after every retry. Slow down and try again later."""


class ServerError(RobloxError):
    """HTTP 5xx persisted after every retry. Roblox is having problems."""


class EntityUnavailable(RobloxError):
    """A collector could not fetch the primary record for an entity.

    ``reason`` is a short machine-readable token: ``"not-found"``, ``"private"``,
    or ``"invalid"``.
    """

    def __init__(self, reason: str, message: str = ""):
        self.reason = reason
        super().__init__(message or f"entity unavailable: {reason}")


# Names used by the March 2026 pyroblox API, kept so that code keeps working.
PyRobloxError = RobloxError
RobloxAPIError = RobloxError
RateLimitError = RateLimitedError
