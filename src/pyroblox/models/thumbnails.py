"""Models for ``thumbnails.roblox.com`` lookups and for images saved to disk."""

from __future__ import annotations

from .base import RobloxModel


class Thumbnail(RobloxModel):
    """One thumbnail record (``targetId``, ``state``, ``imageUrl``); ``image_url`` is None unless ``state`` is ``Completed``."""

    target_id: int | None = None
    state: str | None = None
    image_url: str | None = None
    version: str | None = None
    #: set only for kind ``game-thumbnail``: the universe the image belongs to
    universe_id: int | None = None
    #: set only for kind ``game-thumbnail``: the image's own id
    thumbnail_target_id: int | None = None


class SavedThumbnail(RobloxModel):
    """A thumbnail image written to disk by :meth:`~pyroblox.thumbnails.ThumbnailsAPI.save`."""

    kind: str
    target_id: int | None = None
    url: str
    path: str
    sha256: str
