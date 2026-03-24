"""Interface to avatar.roblox.com endpoints."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from pyroblox import _endpoints as ep
from pyroblox.models.avatar import Avatar, Outfit
from pyroblox.pagination import CursorPage, paginate

if TYPE_CHECKING:
    from pyroblox.client import RobloxClient


class AvatarAPI:
    """Methods for the Roblox Avatar API."""

    def __init__(self, client: RobloxClient) -> None:
        self._client = client

    def get_avatar(self, user_id: int) -> Avatar:
        """Get a user's avatar details (worn assets, body colors, scales)."""
        path = ep.USER_AVATAR.format(user_id=user_id)
        resp = self._client.get("avatar", path)
        return Avatar.model_validate(resp.json())

    def get_currently_wearing(self, user_id: int) -> list[int]:
        """Get asset IDs currently worn by a user."""
        path = ep.USER_CURRENTLY_WEARING.format(user_id=user_id)
        resp = self._client.get("avatar", path)
        return resp.json().get("assetIds", [])  # type: ignore[no-any-return]

    def get_outfits(
        self, user_id: int, *, limit: int = 50, max_pages: int | None = None
    ) -> Iterator[Outfit]:
        """Lazily iterate a user's saved outfits.

        Note: The v2 outfits endpoint uses non-standard pagination tokens
        (``nextPageToken``/``paginationToken`` instead of ``nextPageCursor``),
        so this method cannot use ``paginate_endpoint``.
        """
        def fetch_page(cursor: str | None) -> CursorPage[Outfit]:
            path = ep.USER_OUTFITS.format(user_id=user_id)
            params: dict[str, str | int] = {"itemsPerPage": limit}
            if cursor:
                params["paginationToken"] = cursor
            resp = self._client.get("avatar", path, params=params)
            raw = resp.json()
            next_cursor = (
                raw.get("nextPageToken")
                or raw.get("paginationToken")
                or raw.get("nextPageCursor")
            )
            return CursorPage(
                data=[Outfit.model_validate(o) for o in raw.get("data", [])],
                next_page_cursor=next_cursor,
                previous_page_cursor=raw.get("previousPageCursor"),
            )

        return paginate(fetch_page, max_pages=max_pages)
