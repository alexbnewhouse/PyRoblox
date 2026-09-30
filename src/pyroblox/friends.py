"""Social-graph data from ``friends.roblox.com``: friends lists and the
friend/follower/following counts. The friends list and every ``count`` call
work without a cookie; the follower and following *lists* require one.
List methods return :class:`~pyroblox.models.friends.Friend` models.
"""

from __future__ import annotations

from typing import List, Optional

from .client import PagedList, RobloxClient
from .models.friends import Friend, FriendCounts


class FriendsAPI:
    """Lookups against the friends.roblox.com domain."""

    BASE = "https://friends.roblox.com"

    def __init__(self, client: RobloxClient):
        self.client = client

    def get_friends(self, user_id: int) -> List[Friend]:
        """Return the user's complete friends list as a ``list[Friend]`` (id,
        name, display_name) in one call. Warning: Roblox now returns blank
        ``name`` / ``display_name`` unauthenticated; use
        ``client.users.get_batch`` on the ids to get names. About 20 calls per
        minute unauthenticated."""
        body = self.client.get(f"{self.BASE}/v1/users/{user_id}/friends")
        return Friend.from_list(body.get("data"))

    def get_friend_ids(self, user_id: int) -> List[int]:
        """Return just the user ids from :meth:`get_friends`."""
        return [f.id for f in self.get_friends(user_id)]

    def get_friend_count(self, user_id: int) -> int:
        """Return the user's number of friends."""
        return self.client.get(f"{self.BASE}/v1/users/{user_id}/friends/count")["count"]

    get_count = get_friend_count

    def get_followers(self, user_id: int, max_items: Optional[int] = None) -> PagedList[Friend]:
        """Return a ``PagedList[Friend]`` of the users who follow ``user_id``,
        oldest first. Requires a cookie (Roblox answers 401 otherwise)."""
        return self.client.fetch_all(
            f"{self.BASE}/v1/users/{user_id}/followers",
            limit=100, max_items=max_items, sort_order="Asc", model=Friend)

    def get_follower_count(self, user_id: int) -> int:
        """Return how many users follow ``user_id``."""
        return self.client.get(f"{self.BASE}/v1/users/{user_id}/followers/count")["count"]

    def get_followings(self, user_id: int, max_items: Optional[int] = None) -> PagedList[Friend]:
        """Return a ``PagedList[Friend]`` of the users that ``user_id``
        follows, oldest first. Requires a cookie (Roblox answers 401
        otherwise)."""
        return self.client.fetch_all(
            f"{self.BASE}/v1/users/{user_id}/followings",
            limit=100, max_items=max_items, sort_order="Asc", model=Friend)

    def get_following_count(self, user_id: int) -> int:
        """Return how many users ``user_id`` follows."""
        return self.client.get(f"{self.BASE}/v1/users/{user_id}/followings/count")["count"]

    def get_counts(self, user_id: int) -> FriendCounts:
        """Return the :class:`FriendCounts` (friends, followers, followings)
        assembled from the three count endpoints (all work without a
        cookie)."""
        return FriendCounts(
            friends=self.get_friend_count(user_id),
            followers=self.get_follower_count(user_id),
            followings=self.get_following_count(user_id),
        )
