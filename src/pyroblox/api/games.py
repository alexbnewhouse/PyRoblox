"""Interface to games.roblox.com endpoints."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from pyroblox import _endpoints as ep
from pyroblox.models.games import Game
from pyroblox.pagination import CursorPage, paginate

if TYPE_CHECKING:
    from pyroblox.client import RobloxClient


class GamesAPI:
    """Methods for the Roblox Games API."""

    def __init__(self, client: RobloxClient) -> None:
        self._client = client

    def get_group_games(
        self, group_id: int, *, limit: int = 100, max_pages: int | None = None
    ) -> Iterator[Game]:
        """Lazily iterate games created by a group."""
        def fetch_page(cursor: str | None) -> CursorPage[Game]:
            path = ep.GROUP_GAMES.format(group_id=group_id)
            params: dict[str, str | int] = {
                "accessFilter": "All",
                "sortOrder": "Asc",
                "limit": limit,
            }
            if cursor:
                params["cursor"] = cursor
            resp = self._client.get("games", path, params=params)
            raw = resp.json()
            return CursorPage(
                data=[Game.model_validate(g) for g in raw.get("data", [])],
                next_page_cursor=raw.get("nextPageCursor"),
                previous_page_cursor=raw.get("previousPageCursor"),
            )

        return paginate(fetch_page, max_pages=max_pages)

    def get_user_games(
        self, user_id: int, *, limit: int = 50, max_pages: int | None = None
    ) -> Iterator[Game]:
        """Lazily iterate games created by a user."""
        def fetch_page(cursor: str | None) -> CursorPage[Game]:
            path = ep.USER_GAMES.format(user_id=user_id)
            params: dict[str, str | int] = {
                "accessFilter": "All",
                "sortOrder": "Asc",
                "limit": limit,
            }
            if cursor:
                params["cursor"] = cursor
            resp = self._client.get("games", path, params=params)
            raw = resp.json()
            return CursorPage(
                data=[Game.model_validate(g) for g in raw.get("data", [])],
                next_page_cursor=raw.get("nextPageCursor"),
                previous_page_cursor=raw.get("previousPageCursor"),
            )

        return paginate(fetch_page, max_pages=max_pages)

    def get_user_favorites(
        self, user_id: int, *, limit: int = 50, max_pages: int | None = None
    ) -> Iterator[Game]:
        """Lazily iterate a user's favorite games."""
        def fetch_page(cursor: str | None) -> CursorPage[Game]:
            path = ep.USER_FAVORITE_GAMES.format(user_id=user_id)
            params: dict[str, str | int] = {"limit": limit}
            if cursor:
                params["cursor"] = cursor
            resp = self._client.get("games", path, params=params)
            raw = resp.json()
            return CursorPage(
                data=[Game.model_validate(g) for g in raw.get("data", [])],
                next_page_cursor=raw.get("nextPageCursor"),
                previous_page_cursor=raw.get("previousPageCursor"),
            )

        return paginate(fetch_page, max_pages=max_pages)

    def get_info(self, universe_ids: list[int]) -> list[Game]:
        """Get information about games by universe IDs.

        Args:
            universe_ids: List of universe IDs.
        """
        resp = self._client.get(
            "games",
            ep.GAME_INFO,
            params={"universeIds": ",".join(str(uid) for uid in universe_ids)},
        )
        data = resp.json()
        return [Game.model_validate(g) for g in data.get("data", [])]
