"""Social-graph data from ``friends.roblox.com``: friends lists and the
friend/follower/following counts. The friends list and every ``count`` call
work without a cookie; the follower and following *lists* require one.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .client import PagedList, RobloxClient


class FriendsAPI:
    """Lookups against the friends.roblox.com domain."""

    BASE = "https://friends.roblox.com"

    def __init__(self, client: RobloxClient):
        self.client = client

    def friends(self, user_id: int) -> List[Dict[str, Any]]:
        """Return the user's complete friends list as (id, name, displayName)
        records in one call. Warning: Roblox now returns blank ``name`` /
        ``displayName`` unauthenticated; use ``client.users.batch_get`` on the
        ids to get names. About 20 calls per minute unauthenticated."""
        body = self.client.get(f"{self.BASE}/v1/users/{user_id}/friends")
        return body.get("data") or []

    def friend_ids(self, user_id: int) -> List[int]:
        """Return just the user ids from :meth:`friends`."""
        return [f["id"] for f in self.friends(user_id)]

    def friend_count(self, user_id: int) -> int:
        """Return the user's number of friends."""
        return self.client.get(f"{self.BASE}/v1/users/{user_id}/friends/count")["count"]

    def followers(self, user_id: int, max_items: Optional[int] = None) -> PagedList:
        """Return the users who follow ``user_id``, oldest first. Requires a
        cookie (Roblox answers 401 otherwise)."""
        return self.client.fetch_all(
            f"{self.BASE}/v1/users/{user_id}/followers",
            limit=100, max_items=max_items, sort_order="Asc")

    def follower_count(self, user_id: int) -> int:
        """Return how many users follow ``user_id``."""
        return self.client.get(f"{self.BASE}/v1/users/{user_id}/followers/count")["count"]

    def followings(self, user_id: int, max_items: Optional[int] = None) -> PagedList:
        """Return the users that ``user_id`` follows, oldest first. Requires a
        cookie (Roblox answers 401 otherwise)."""
        return self.client.fetch_all(
            f"{self.BASE}/v1/users/{user_id}/followings",
            limit=100, max_items=max_items, sort_order="Asc")

    def following_count(self, user_id: int) -> int:
        """Return how many users ``user_id`` follows."""
        return self.client.get(f"{self.BASE}/v1/users/{user_id}/followings/count")["count"]

    def counts(self, user_id: int) -> Dict[str, int]:
        """Return ``{"friends": n, "followers": n, "followings": n}`` from the
        three count endpoints (all work without a cookie)."""
        return {
            "friends": self.friend_count(user_id),
            "followers": self.follower_count(user_id),
            "followings": self.following_count(user_id),
        }
