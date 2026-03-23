"""Interface to friends.roblox.com endpoints."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from pyroblox import _endpoints as ep
from pyroblox.models.friends import Friend, FriendCount
from pyroblox.pagination import CursorPage, paginate

if TYPE_CHECKING:
    from pyroblox.client import RobloxClient


class FriendsAPI:
    """Methods for the Roblox Friends API."""

    def __init__(self, client: RobloxClient) -> None:
        self._client = client

    def get_friends(self, user_id: int) -> list[Friend]:
        """Get a user's friends list."""
        path = ep.USER_FRIENDS.format(user_id=user_id)
        resp = self._client.get("friends", path)
        data = resp.json()
        return [Friend.model_validate(f) for f in data.get("data", [])]

    def get_count(self, user_id: int) -> int:
        """Get a user's friend count."""
        path = ep.USER_FRIEND_COUNT.format(user_id=user_id)
        resp = self._client.get("friends", path)
        return FriendCount.model_validate(resp.json()).count

    def get_followers(
        self, user_id: int, *, limit: int = 100, max_pages: int | None = None
    ) -> Iterator[Friend]:
        """Lazily iterate a user's followers with automatic pagination."""
        def fetch_page(cursor: str | None) -> CursorPage[Friend]:
            path = ep.USER_FOLLOWERS.format(user_id=user_id)
            params: dict[str, str | int] = {"sortOrder": "Asc", "limit": limit}
            if cursor:
                params["cursor"] = cursor
            resp = self._client.get("friends", path, params=params)
            raw = resp.json()
            return CursorPage(
                data=[Friend.model_validate(f) for f in raw.get("data", [])],
                next_page_cursor=raw.get("nextPageCursor"),
                previous_page_cursor=raw.get("previousPageCursor"),
            )

        return paginate(fetch_page, max_pages=max_pages)

    def get_followings(
        self, user_id: int, *, limit: int = 100, max_pages: int | None = None
    ) -> Iterator[Friend]:
        """Lazily iterate users that a user is following."""
        def fetch_page(cursor: str | None) -> CursorPage[Friend]:
            path = ep.USER_FOLLOWINGS.format(user_id=user_id)
            params: dict[str, str | int] = {"sortOrder": "Asc", "limit": limit}
            if cursor:
                params["cursor"] = cursor
            resp = self._client.get("friends", path, params=params)
            raw = resp.json()
            return CursorPage(
                data=[Friend.model_validate(f) for f in raw.get("data", [])],
                next_page_cursor=raw.get("nextPageCursor"),
                previous_page_cursor=raw.get("previousPageCursor"),
            )

        return paginate(fetch_page, max_pages=max_pages)
