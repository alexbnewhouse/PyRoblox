"""Models for games.roblox.com and its sibling hosts (apis, develop, inventory)."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .base import RobloxModel


class GameCreator(RobloxModel):
    """The user or group that owns a game or place."""

    id: int
    name: str | None = None
    type: str | None = None
    has_verified_badge: bool = False
    # Roblox spells this one ``isRNVAccount``, which the camelCase generator
    # would render as ``isRnvAccount``; pin the alias.
    is_rnv_account: bool | None = Field(default=None, alias="isRNVAccount")


class RootPlace(RobloxModel):
    """The root place reference in v2 game listings (``{id, type}``)."""

    id: int
    type: str | None = None


class Game(RobloxModel):
    """A game (universe): serves the v1 game object and the v2 user/group/favorite listings."""

    id: int
    name: str
    description: str | None = None
    creator: GameCreator | None = None
    root_place_id: int | None = None
    root_place: RootPlace | None = None
    created: datetime | None = None
    updated: datetime | None = None
    place_visits: int | None = None
    visits: int | None = None
    playing: int | None = None
    max_players: int | None = None
    genre: str | None = None
    # Roblox sends these two with an underscore (``genre_l1``), not camelCase.
    genre_l1: str | None = Field(default=None, alias="genre_l1")
    genre_l2: str | None = Field(default=None, alias="genre_l2")
    favorited_count: int | None = None
    is_content_restricted: bool | None = None
    price: int | None = None
    source_name: str | None = None
    source_description: str | None = None


class GameVotes(RobloxModel):
    """Up/down vote counts for a universe."""

    id: int
    up_votes: int = 0
    down_votes: int = 0


class GameServer(RobloxModel):
    """A running server instance of a place."""

    id: str | None = None
    max_players: int | None = None
    playing: int | None = None
    player_tokens: list[str] | None = None
    players: list | None = None
    fps: float | None = None
    ping: int | None = None


class GamePass(RobloxModel):
    """A game pass sold by a universe."""

    id: int
    product_id: int | None = None
    name: str | None = None
    display_name: str | None = None
    display_description: str | None = None
    is_for_sale: bool | None = None
    display_icon_image_asset_id: int | None = None
    created: datetime | None = None
    updated: datetime | None = None


class Place(RobloxModel):
    """A place inside a universe (``develop.roblox.com/v1/universes/{id}/places``)."""

    id: int
    universe_id: int | None = None
    name: str | None = None
    description: str | None = None


class GameMedia(RobloxModel):
    """A media entry (image or video) on a game's page."""

    asset_type_id: int | None = None
    asset_type: str | None = None
    image_id: int | None = None
    video_hash: str | None = None
    video_title: str | None = None
    approved: bool | None = None
    alt_text: str | None = None


class CreatedPlace(RobloxModel):
    """A place a user created (``inventory.roblox.com/v1/users/{id}/places/inventory``)."""

    universe_id: int
    place_id: int
    name: str | None = None
    creator: GameCreator | None = None
    price_in_robux: int | None = None
