"""Models for ``friends.roblox.com`` responses (friends, followers, followings, counts)."""

from __future__ import annotations

from datetime import datetime

from .base import RobloxModel


class Friend(RobloxModel):
    """A user in a friends, followers, or followings list; Roblox sends a mix of these fields (names are blank unauthenticated)."""

    id: int
    name: str | None = None
    display_name: str | None = None
    has_verified_badge: bool = False
    is_online: bool | None = None
    is_deleted: bool | None = None
    friend_frequent_score: int | None = None
    friend_frequent_rank: int | None = None
    description: str | None = None
    created: datetime | None = None
    is_banned: bool | None = None


class FriendCounts(RobloxModel):
    """Friend, follower, and following totals assembled from the three ``/count`` endpoints (not a Roblox payload)."""

    friends: int
    followers: int
    followings: int
