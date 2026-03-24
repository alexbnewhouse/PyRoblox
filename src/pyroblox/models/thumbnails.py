"""Models for the Thumbnails API."""

from __future__ import annotations

from pyroblox.models.base import RobloxModel


class Thumbnail(RobloxModel):
    target_id: int
    state: str | None = None
    image_url: str | None = None
    version: str | None = None
