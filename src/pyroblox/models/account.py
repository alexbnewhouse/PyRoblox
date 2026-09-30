"""Models for accountinformation.roblox.com: Roblox badges and promotion channels."""

from __future__ import annotations

from .base import RobloxModel


class RobloxBadge(RobloxModel):
    """One of Roblox's own (non-game) badges a user holds (``roblox-badges`` rows)."""

    id: int
    name: str
    description: str | None = None
    image_url: str | None = None


class PromotionChannels(RobloxModel):
    """A user's linked social channels; values are null without a cookie."""

    facebook: str | None = None
    twitter: str | None = None
    youtube: str | None = None
    twitch: str | None = None
    guilded: str | None = None
