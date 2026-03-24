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


class GameVotes(RobloxModel):
    id: int
    up_votes: int = 0
    down_votes: int = 0


class GameServer(RobloxModel):
    id: str | None = None
    max_players: int | None = None
    playing: int | None = None
    player_tokens: list[str] | None = None
    fps: float | None = None
    ping: int | None = None
