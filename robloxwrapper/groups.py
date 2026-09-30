"""Group (community) data from ``groups.roblox.com``: group profiles, member
lists, roles, ally/enemy relationships, name history, search, and the groups a
user belongs to. Everything here is public except :meth:`GroupsAPI.social_links`,
which needs a ``.ROBLOSECURITY`` cookie. Note that ``GET /v1/groups/{id}`` is
throttled to about 7 calls per minute unauthenticated, so use
:meth:`GroupsAPI.batch_get` when you have many group ids."""

from __future__ import annotations

from typing import Iterable, List, Optional

from .client import PagedList, RobloxClient, chunked


class GroupsAPI:
    """Read-only access to the groups.roblox.com endpoints.

    All methods return Roblox's JSON as plain ``dict`` / ``list`` values with
    the obvious envelope (``data``, ``roles``) already unwrapped.
    """

    BASE = "https://groups.roblox.com"

    def __init__(self, client: RobloxClient):
        self.client = client

    # -- group profile --------------------------------------------------------

    def get(self, group_id: int) -> dict:
        """Return the full group object (owner, shout, memberCount, isLocked, communityTier...). Roblox allows about 7 calls per minute unauthenticated; prefer :meth:`batch_get` for many groups."""
        return self.client.get(f"{self.BASE}/v1/groups/{group_id}")

    def batch_get(self, group_ids: Iterable[int]) -> list:
        """Return the concatenated v2 group records (id, name, description, owner{id,type}, created, hasVerifiedBadge) for ``group_ids``, 100 per call. Roblox allows about 1 call per second unauthenticated."""
        url = f"{self.BASE}/v2/groups"
        out: List[dict] = []
        for chunk in chunked(group_ids, 100):
            body = self.client.get(url, {"groupIds": ",".join(str(i) for i in chunk)})
            out.extend(body.get("data") or [])
        return out

    # -- membership -----------------------------------------------------------

    def members(self, group_id: int, max_items: Optional[int] = None,
                sort_order: str = "Asc") -> PagedList:
        """Return every member as ``{"user": {...}, "role": {...}}`` records, walking the cursor pagination 100 at a time."""
        return self.client.fetch_all(f"{self.BASE}/v1/groups/{group_id}/users",
                                     limit=100, max_items=max_items, sort_order=sort_order)

    def roles(self, group_id: int) -> list:
        """Return the group's ``roles`` list (id, name, rank, memberCount)."""
        body = self.client.get(f"{self.BASE}/v1/groups/{group_id}/roles")
        return body.get("roles") or []

    def role_members(self, group_id: int, role_id: int,
                     max_items: Optional[int] = None) -> PagedList:
        """Return the users (userId, username, displayName) holding ``role_id`` in the group, 100 per page."""
        return self.client.fetch_all(
            f"{self.BASE}/v1/groups/{group_id}/roles/{role_id}/users",
            limit=100, max_items=max_items, sort_order="Asc")

    # -- relationships --------------------------------------------------------

    def allies(self, group_id: int, max_items: Optional[int] = None) -> PagedList:
        """Return the group's allied groups as full group objects (incl. memberCount); locked groups raise BadRequestError."""
        return self.client.fetch_rows(f"{self.BASE}/v1/groups/{group_id}/relationships/allies",
                                      page_size=100, max_items=max_items)

    def enemies(self, group_id: int, max_items: Optional[int] = None) -> PagedList:
        """Return the group's enemy groups as full group objects (incl. memberCount); locked groups raise BadRequestError."""
        return self.client.fetch_rows(f"{self.BASE}/v1/groups/{group_id}/relationships/enemies",
                                      page_size=100, max_items=max_items)

    # -- metadata -------------------------------------------------------------

    def social_links(self, group_id: int) -> list:
        """Return the group's social links (id, type, url, title). Requires a cookie."""
        body = self.client.get(f"{self.BASE}/v1/groups/{group_id}/social-links")
        return body.get("data") or []

    def name_history(self, group_id: int, max_items: Optional[int] = None) -> PagedList:
        """Return the group's previous names as ``{"name", "created"}`` records, oldest first."""
        return self.client.fetch_all(f"{self.BASE}/v1/groups/{group_id}/name-history",
                                     limit=100, max_items=max_items, sort_order="Asc")

    def guest_permissions(self, group_id: int) -> dict:
        """Return the guest-role permissions object (groupId, role, permissions{...})."""
        return self.client.get(f"{self.BASE}/v1/groups/{group_id}/roles/guest/permissions")

    # -- by user --------------------------------------------------------------

    def user_groups(self, user_id: int) -> list:
        """Return the groups a user belongs to as ``{"group": {...}, "role": {...}, "isPrimaryGroup"?}`` records."""
        body = self.client.get(f"{self.BASE}/v1/users/{user_id}/groups/roles")
        return body.get("data") or []

    def user_primary_group(self, user_id: int) -> Optional[dict]:
        """Return the user's primary group as ``{"group": {...}, "role": {...}}``, or None if they have none."""
        body = self.client.get(f"{self.BASE}/v1/users/{user_id}/groups/primary/role")
        return body if body else None

    # -- search ---------------------------------------------------------------

    def search(self, keyword: str, max_items: Optional[int] = None,
               prioritize_exact_match: bool = True) -> PagedList:
        """Return groups matching ``keyword`` (id, name, description, memberCount, previousName, publicEntryAllowed, created, updated), 100 per page."""
        params = {"keyword": keyword,
                  "prioritizeExactMatch": "true" if prioritize_exact_match else "false"}
        return self.client.fetch_all(f"{self.BASE}/v1/groups/search", params,
                                     limit=100, max_items=max_items)

    def lookup(self, group_name: str) -> list:
        """Return groups whose name matches ``group_name`` (id, name, memberCount, hasVerifiedBadge)."""
        body = self.client.get(f"{self.BASE}/v1/groups/search/lookup", {"groupName": group_name})
        return body.get("data") or []
