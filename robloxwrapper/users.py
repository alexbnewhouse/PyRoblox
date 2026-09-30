"""User identity data from ``users.roblox.com``: single profiles, batch
id/username resolution, username history, and user search. Everything here
works without a cookie except :meth:`UsersAPI.authenticated`, which needs one.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .client import PagedList, RobloxClient, chunked
from .errors import NotFoundError


class UsersAPI:
    """Lookups against the users.roblox.com domain."""

    BASE = "https://users.roblox.com"

    def __init__(self, client: RobloxClient):
        self.client = client

    def get(self, user_id: int) -> Dict[str, Any]:
        """Return one user's profile object (id, name, displayName, description,
        created, isBanned, hasVerifiedBadge, externalAppDisplayName). Roblox
        allows about 30 calls per minute unauthenticated; prefer batch_get for
        many users."""
        return self.client.get(f"{self.BASE}/v1/users/{user_id}")

    def batch_get(self, user_ids: Iterable[int],
                  exclude_banned: bool = False) -> List[Dict[str, Any]]:
        """Return a list of (id, name, displayName, hasVerifiedBadge) records
        for the given ids, POSTed in chunks of 100."""
        url = f"{self.BASE}/v1/users"
        out: List[Dict[str, Any]] = []
        for chunk in chunked(user_ids, 100):
            body = self.client.post(
                url, {"userIds": chunk, "excludeBannedUsers": exclude_banned})
            out.extend(body.get("data") or [])
        return out

    def by_usernames(self, usernames: Iterable[str],
                     exclude_banned: bool = False) -> List[Dict[str, Any]]:
        """Return a list of (requestedUsername, id, name, displayName,
        hasVerifiedBadge) records for the given usernames, POSTed in chunks of
        100; names that do not exist are simply absent from the result."""
        url = f"{self.BASE}/v1/usernames/users"
        out: List[Dict[str, Any]] = []
        for chunk in chunked(usernames, 100):
            body = self.client.post(
                url, {"usernames": chunk, "excludeBannedUsers": exclude_banned})
            out.extend(body.get("data") or [])
        return out

    def resolve(self, username: str) -> Dict[str, Any]:
        """Return the single match for ``username`` (see by_usernames); raises
        NotFoundError when Roblox knows no such user."""
        matches = self.by_usernames([username])
        if not matches:
            raise NotFoundError(f"username {username!r} not found",
                                url=f"{self.BASE}/v1/usernames/users")
        return matches[0]

    def username_history(self, user_id: int,
                         max_items: Optional[int] = None) -> PagedList:
        """Return the user's past usernames as ``{"name": ...}`` records, oldest
        first. Roblox allows about 1 call per minute unauthenticated."""
        return self.client.fetch_all(
            f"{self.BASE}/v1/users/{user_id}/username-history",
            limit=100, max_items=max_items, sort_order="Asc")

    def search(self, keyword: str, max_items: Optional[int] = None) -> PagedList:
        """Return users matching ``keyword`` (id, name, displayName,
        hasVerifiedBadge, previousUsernames[]). Roblox allows about 1 call per
        minute unauthenticated."""
        return self.client.fetch_all(
            f"{self.BASE}/v1/users/search", {"keyword": keyword},
            limit=100, max_items=max_items)

    def authenticated(self) -> Dict[str, Any]:
        """Return the logged-in account (id, name, displayName). Requires a
        cookie; raises AuthRequiredError otherwise."""
        return self.client.get(f"{self.BASE}/v1/users/authenticated")
