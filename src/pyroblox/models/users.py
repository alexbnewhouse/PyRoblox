"""Models for the Users API."""

from __future__ import annotations

from datetime import datetime

from pyroblox.models.base import RobloxModel


class User(RobloxModel):
    id: int
    name: str
    display_name: str | None = None
    description: str | None = None
    created: datetime | None = None
    is_banned: bool | None = None
    external_app_display_name: str | None = None
    has_verified_badge: bool = False
