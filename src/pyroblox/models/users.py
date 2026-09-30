"""Models for ``users.roblox.com`` responses (profiles, batch lookups, search)."""

from __future__ import annotations

from datetime import datetime

from .base import RobloxModel


class User(RobloxModel):
    """A Roblox user as returned by ``/v1/users/{id}``, the batch endpoints, search, and ``/v1/users/authenticated``."""

    id: int
    name: str
    display_name: str | None = None
    description: str | None = None
    created: datetime | None = None
    is_banned: bool | None = None
    has_verified_badge: bool = False
    external_app_display_name: str | None = None
    previous_usernames: list[str] | None = None


class UsernameMatch(User):
    """A user matched by ``POST /v1/usernames/users``; carries the name that was asked for."""

    requested_username: str | None = None


class UsernameHistoryEntry(RobloxModel):
    """One past username from ``/v1/users/{id}/username-history``."""

    name: str
