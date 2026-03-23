"""Models for the Friends API."""

from __future__ import annotations

from datetime import datetime

from pyroblox.models.base import RobloxModel


class Friend(RobloxModel):
    id: int
    name: str
    display_name: str | None = None
    description: str | None = None
    created: datetime | None = None
    is_online: bool | None = None
    is_deleted: bool | None = None
    has_verified_badge: bool = False


class FriendCount(RobloxModel):
    count: int
