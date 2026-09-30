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
"""

from __future__ import annotations

from typing import Optional


class RobloxError(Exception):
    """Base class for all PyRoblox errors."""

    def __init__(self, message: str, *, status: Optional[int] = None,
                 url: Optional[str] = None, roblox_message: Optional[str] = None):
        self.status = status
        self.url = url
        self.roblox_message = roblox_message
        text = message
        if roblox_message:
            text = f"{message} (Roblox says: {roblox_message})"
        if url:
            text = f"{text} [{url}]"
        super().__init__(text)


class NotFoundError(RobloxError):
    """HTTP 404: the entity does not exist or has been deleted."""


class PrivateError(RobloxError):
    """HTTP 403: the entity exists but is private or hidden from you."""


class AuthRequiredError(RobloxError):
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
