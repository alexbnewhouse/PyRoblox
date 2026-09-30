"""Models for badges.roblox.com: game badges, their statistics and award dates."""

from __future__ import annotations

from datetime import datetime

from .base import RobloxModel


class BadgeStatistics(RobloxModel):
    """Award statistics attached to a badge (``statistics``)."""

    past_day_awarded_count: int = 0
    awarded_count: int = 0
    win_rate_percentage: float = 0.0


class AwardingUniverse(RobloxModel):
    """The experience (universe) that awards a badge (``awardingUniverse``)."""

    id: int
    name: str | None = None
    root_place_id: int | None = None


class Badge(RobloxModel):
    """A badge an experience awards, as returned by badge lookups and listings."""

    id: int
    name: str
    description: str | None = None
    display_name: str | None = None
    display_description: str | None = None
    enabled: bool | None = None
    icon_image_id: int | None = None
    display_icon_image_id: int | None = None
    created: datetime | None = None
    updated: datetime | None = None
    statistics: BadgeStatistics | None = None
    awarding_universe: AwardingUniverse | None = None


class BadgeAwardDate(RobloxModel):
    """When a user earned one badge (``badges/awarded-dates`` rows)."""

    badge_id: int
    awarded_date: datetime | None = None
