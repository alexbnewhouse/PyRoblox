"""Interface to users.roblox.com endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pyroblox import _endpoints as ep
from pyroblox.models.users import User

if TYPE_CHECKING:
    from pyroblox.client import RobloxClient


class UsersAPI:
    """Methods for the Roblox Users API."""

    def __init__(self, client: RobloxClient) -> None:
        self._client = client

    def get_info(self, user_id: int) -> User:
        """Get information about a user."""
        path = ep.USER_INFO.format(user_id=user_id)
        resp = self._client.get("users", path)
        return User.model_validate(resp.json())

    def get_batch(self, user_ids: list[int]) -> list[User]:
        """Get information about multiple users in a single request.

        Args:
            user_ids: List of user IDs (max 100 per request).
        """
        resp = self._client.post(
            "users",
            ep.USERS_BATCH,
            json={"userIds": user_ids, "excludeBannedUsers": False},
        )
        data = resp.json()
        return [User.model_validate(u) for u in data.get("data", [])]

    def search(self, keyword: str, *, limit: int = 10) -> list[User]:
        """Search for users by keyword.

        Args:
            keyword: Search term.
            limit: Max results (default 10).
        """
        resp = self._client.get(
            "users",
            ep.USER_SEARCH,
            params={"keyword": keyword, "limit": limit},
        )
        data = resp.json()
        return [User.model_validate(u) for u in data.get("data", [])]
