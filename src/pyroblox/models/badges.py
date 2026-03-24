"""Models for the Badges API."""

from __future__ import annotations

from datetime import datetime

from pyroblox.models.base import RobloxModel


class BadgeStatistics(RobloxModel):
    past_day_awarded_count: int = 0
    awarded_count: int = 0
    win_rate_percentage: float = 0.0


class BadgeCreator(RobloxModel):
    id: int
    type: str | None = None
    name: str | None = None


class Badge(RobloxModel):
    id: int
    name: str
    description: str | None = None
    display_name: str | None = None
    display_description: str | None = None
    enabled: bool = True
    icon_image_id: int | None = None
    display_icon_image_id: int | None = None
    awarder: BadgeCreator | None = None
    statistics: BadgeStatistics | None = None
    created: datetime | None = None
    updated: datetime | None = None


class BadgeAwardDate(RobloxModel):
    badge_id: int
    awarded_date: datetime | None = None
