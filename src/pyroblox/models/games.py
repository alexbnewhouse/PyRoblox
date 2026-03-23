"""Models for the Games API."""

from __future__ import annotations

from datetime import datetime

from pyroblox.models.base import RobloxModel


class GameCreator(RobloxModel):
    id: int
    name: str | None = None
    type: str | None = None
    is_roblox_verified: bool = False
    has_verified_badge: bool = False


class Game(RobloxModel):
    id: int
    name: str
    description: str | None = None
    creator: GameCreator | None = None
    root_place_id: int | None = None
    created: datetime | None = None
    updated: datetime | None = None
    place_visits: int | None = None
    playing: int | None = None
    max_players: int | None = None
    genre: str | None = None
