"""Models for presence.roblox.com: who is online and when users were last seen."""

from __future__ import annotations

from datetime import datetime

from .base import RobloxModel


class UserPresence(RobloxModel):
    """A user's presence (``userPresences`` rows): 0 offline, 1 online, 2 in game, 3 studio."""

    user_presence_type: int | None = None
    last_location: str | None = None
    place_id: int | None = None
    root_place_id: int | None = None
    game_id: str | None = None
    universe_id: int | None = None
    user_id: int
    last_online: datetime | None = None


class LastOnline(RobloxModel):
    """When a user was last online (``lastOnlineTimestamps`` rows)."""

    user_id: int
    last_online: datetime | None = None
