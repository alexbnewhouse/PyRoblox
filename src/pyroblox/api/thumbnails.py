"""Interface to thumbnails.roblox.com endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pyroblox import _endpoints as ep
from pyroblox.models.thumbnails import Thumbnail

if TYPE_CHECKING:
    from pyroblox.client import RobloxClient


class ThumbnailsAPI:
    """Methods for the Roblox Thumbnails API."""

    def __init__(self, client: RobloxClient) -> None:
        self._client = client

    def _get(
        self,
        path: str,
        ids_param: str,
        ids: list[int],
        size: str,
        fmt: str,
    ) -> list[Thumbnail]:
        """Shared helper for all thumbnail batch-fetch endpoints."""
        resp = self._client.get(
            "thumbnails", path,
            params={
                ids_param: ",".join(str(i) for i in ids),
                "size": size,
                "format": fmt,
            },
        )
        data = resp.json()
        return [Thumbnail.model_validate(t) for t in data.get("data", [])]

    def get_user_headshots(
        self, user_ids: list[int], *, size: str = "150x150", fmt: str = "Png"
    ) -> list[Thumbnail]:
        """Get headshot thumbnails for users.

        Args:
            user_ids: List of user IDs (up to 100).
            size: Image size (e.g. "48x48", "150x150", "420x420").
            fmt: Image format ("Png" or "Jpeg").
        """
        return self._get(ep.USER_HEADSHOT_THUMBNAILS, "userIds", user_ids, size, fmt)

    def get_user_avatars(
        self, user_ids: list[int], *, size: str = "150x150", fmt: str = "Png"
    ) -> list[Thumbnail]:
        """Get full avatar thumbnails for users."""
        return self._get(ep.USER_AVATAR_THUMBNAILS, "userIds", user_ids, size, fmt)

    def get_asset_thumbnails(
        self, asset_ids: list[int], *, size: str = "150x150", fmt: str = "Png"
    ) -> list[Thumbnail]:
        """Get thumbnails for assets."""
        return self._get(ep.ASSET_THUMBNAILS, "assetIds", asset_ids, size, fmt)

    def get_game_icons(
        self, universe_ids: list[int], *, size: str = "150x150", fmt: str = "Png"
    ) -> list[Thumbnail]:
        """Get icon thumbnails for games."""
        return self._get(
            ep.GAME_ICON_THUMBNAILS, "universeIds", universe_ids, size, fmt
        )

    def get_group_icons(
        self, group_ids: list[int], *, size: str = "150x150", fmt: str = "Png"
    ) -> list[Thumbnail]:
        """Get icon thumbnails for groups."""
        return self._get(ep.GROUP_ICON_THUMBNAILS, "groupIds", group_ids, size, fmt)

    def get_badge_icons(
        self, badge_ids: list[int], *, size: str = "150x150", fmt: str = "Png"
    ) -> list[Thumbnail]:
        """Get icon thumbnails for badges."""
        return self._get(ep.BADGE_ICON_THUMBNAILS, "badgeIds", badge_ids, size, fmt)
