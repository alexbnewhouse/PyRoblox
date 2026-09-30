"""User identity data from ``users.roblox.com``: single profiles, batch
id/username resolution, username history, and user search. Everything here
works without a cookie except :meth:`UsersAPI.get_authenticated`, which needs
one. Every method returns typed models from :mod:`pyroblox.models.users`.
"""

from __future__ import annotations

from typing import Iterable, List, Optional

from .client import PagedList, RobloxClient, chunked
from .errors import NotFoundError
from .models.users import User, UsernameHistoryEntry, UsernameMatch


class UsersAPI:
    """Lookups against the users.roblox.com domain."""

    BASE = "https://users.roblox.com"

    def __init__(self, client: RobloxClient):
        self.client = client

    def get_info(self, user_id: int) -> User:
        """Return the :class:`User` for ``user_id`` (id, name, display_name,
        description, created, is_banned, has_verified_badge,
        external_app_display_name). Roblox allows about 30 calls per minute
        unauthenticated; prefer :meth:`get_batch` for many users."""
        return User.model_validate(self.client.get(f"{self.BASE}/v1/users/{user_id}"))

    def get_batch(self, user_ids: Iterable[int],
                  exclude_banned: bool = False) -> List[User]:
        """Return a ``list[User]`` (id, name, display_name, has_verified_badge)
        for the given ids, POSTed in chunks of 100."""
        url = f"{self.BASE}/v1/users"
        out: List[User] = []
        for chunk in chunked(user_ids, 100):
            body = self.client.post(
                url, {"userIds": chunk, "excludeBannedUsers": exclude_banned})
            out.extend(User.from_list(body.get("data")))
        return out

    def get_by_usernames(self, usernames: Iterable[str],
                         exclude_banned: bool = False) -> List[UsernameMatch]:
        """Return a ``list[UsernameMatch]`` (requested_username, id, name,
        display_name, has_verified_badge) for the given usernames, POSTed in
        chunks of 100; names that do not exist are simply absent from the
        result."""
        url = f"{self.BASE}/v1/usernames/users"
        out: List[UsernameMatch] = []
        for chunk in chunked(usernames, 100):
            body = self.client.post(
                url, {"usernames": chunk, "excludeBannedUsers": exclude_banned})
            out.extend(UsernameMatch.from_list(body.get("data")))
        return out

    def resolve(self, username: str) -> UsernameMatch:
        """Return the single :class:`UsernameMatch` for ``username`` (see
        :meth:`get_by_usernames`); raises NotFoundError when Roblox knows no
        such user."""
        matches = self.get_by_usernames([username])
        if not matches:
            raise NotFoundError(f"username {username!r} not found",
                                url=f"{self.BASE}/v1/usernames/users")
        return matches[0]

    def get_username_history(self, user_id: int,
                             max_items: Optional[int] = None) -> PagedList[UsernameHistoryEntry]:
        """Return the user's past usernames as a
        ``PagedList[UsernameHistoryEntry]``, oldest first. Roblox allows about
        1 call per minute unauthenticated."""
        return self.client.fetch_all(
            f"{self.BASE}/v1/users/{user_id}/username-history",
            limit=100, max_items=max_items, sort_order="Asc",
            model=UsernameHistoryEntry)

    def search(self, keyword: str, max_items: Optional[int] = None) -> PagedList[User]:
        """Return a ``PagedList[User]`` matching ``keyword`` (id, name,
        display_name, has_verified_badge, previous_usernames). Roblox allows
        about 1 call per minute unauthenticated."""
        return self.client.fetch_all(
            f"{self.BASE}/v1/users/search", {"keyword": keyword},
            limit=100, max_items=max_items, model=User)

    def get_authenticated(self) -> User:
        """Return the :class:`User` for the logged-in account (id, name,
        display_name). Requires a cookie; raises AuthRequiredError otherwise."""
        return User.model_validate(self.client.get(f"{self.BASE}/v1/users/authenticated"))
