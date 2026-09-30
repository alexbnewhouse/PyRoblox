"""Group (community) data from ``groups.roblox.com``: group profiles, member
lists, roles, ally/enemy relationships, name history, search, and the groups a
user belongs to. Everything here is public except
:meth:`GroupsAPI.get_social_links`, which needs a ``.ROBLOSECURITY`` cookie.
Note that ``GET /v1/groups/{id}`` is throttled to about 7 calls per minute
unauthenticated, so use :meth:`GroupsAPI.get_batch` when you have many group
ids."""

from __future__ import annotations

from typing import Iterable, Optional

from .client import PagedList, RobloxClient, chunked
from .models.base import RobloxRecord
from .models.groups import (
    Group,
    GroupMember,
    GroupNameHistoryEntry,
    GroupRole,
    GroupSearchResult,
    GroupSummary,
    GroupUser,
    SocialLink,
    UserGroupMembership,
)


class GroupsAPI:
    """Read-only access to the groups.roblox.com endpoints.

    Every method returns typed models from :mod:`pyroblox.models.groups` (or
    a :class:`~pyroblox.client.PagedList` of them) with the obvious envelope
    (``data``, ``roles``) already unwrapped. Fields Roblox adds that the
    models do not declare are kept as extras (``group.communityTier``).
    """

    BASE = "https://groups.roblox.com"

    def __init__(self, client: RobloxClient):
        self.client = client

    # -- group profile --------------------------------------------------------

    def get_info(self, group_id: int) -> Group:
        """Return the :class:`Group` for ``group_id`` (owner, shout, member_count, is_locked; extras such as ``communityTier`` are kept). Roblox allows about 7 calls per minute unauthenticated; prefer :meth:`get_batch` for many groups."""
        return Group.model_validate(self.client.get(f"{self.BASE}/v1/groups/{group_id}"))

    def get_batch(self, group_ids: Iterable[int]) -> list[GroupSummary]:
        """Return the concatenated :class:`GroupSummary` records (id, name, description, owner{id,type}, created, has_verified_badge) for ``group_ids``, 100 per call. Roblox allows about 1 call per second unauthenticated."""
        url = f"{self.BASE}/v2/groups"
        out: list[GroupSummary] = []
        for chunk in chunked(group_ids, 100):
            body = self.client.get(url, {"groupIds": ",".join(str(i) for i in chunk)})
            out.extend(GroupSummary.from_list(body.get("data")))
        return out

    # -- membership -----------------------------------------------------------

    def get_members(self, group_id: int, max_items: Optional[int] = None,
                    sort_order: str = "Asc") -> PagedList[GroupMember]:
        """Return every member as a :class:`GroupMember` (``.user``, ``.role``), walking the cursor pagination 100 at a time."""
        return self.client.fetch_all(f"{self.BASE}/v1/groups/{group_id}/users",
                                     limit=100, max_items=max_items, sort_order=sort_order,
                                     model=GroupMember)

    def get_roles(self, group_id: int) -> list[GroupRole]:
        """Return the group's :class:`GroupRole` list (id, name, rank, member_count)."""
        body = self.client.get(f"{self.BASE}/v1/groups/{group_id}/roles")
        return GroupRole.from_list(body.get("roles"))

    def get_role_members(self, group_id: int, role_id: int,
                         max_items: Optional[int] = None) -> PagedList[GroupUser]:
        """Return the :class:`GroupUser` records (user_id, username, display_name) holding ``role_id`` in the group, 100 per page."""
        return self.client.fetch_all(
            f"{self.BASE}/v1/groups/{group_id}/roles/{role_id}/users",
            limit=100, max_items=max_items, sort_order="Asc", model=GroupUser)

    # -- relationships --------------------------------------------------------

    def get_allies(self, group_id: int, max_items: Optional[int] = None) -> PagedList[Group]:
        """Return the group's allied groups as full :class:`Group` objects (incl. member_count); locked groups raise BadRequestError."""
        return self.client.fetch_rows(f"{self.BASE}/v1/groups/{group_id}/relationships/allies",
                                      page_size=100, max_items=max_items, model=Group)

    def get_enemies(self, group_id: int, max_items: Optional[int] = None) -> PagedList[Group]:
        """Return the group's enemy groups as full :class:`Group` objects (incl. member_count); locked groups raise BadRequestError."""
        return self.client.fetch_rows(f"{self.BASE}/v1/groups/{group_id}/relationships/enemies",
                                      page_size=100, max_items=max_items, model=Group)

    # -- metadata -------------------------------------------------------------

    def get_social_links(self, group_id: int) -> list[SocialLink]:
        """Return the group's :class:`SocialLink` records (id, type, url, title). Requires a cookie."""
        body = self.client.get(f"{self.BASE}/v1/groups/{group_id}/social-links")
        return SocialLink.from_list(body.get("data"))

    def get_name_history(self, group_id: int,
                         max_items: Optional[int] = None) -> PagedList[GroupNameHistoryEntry]:
        """Return the group's previous names as :class:`GroupNameHistoryEntry` records (name, created), oldest first."""
        return self.client.fetch_all(f"{self.BASE}/v1/groups/{group_id}/name-history",
                                     limit=100, max_items=max_items, sort_order="Asc",
                                     model=GroupNameHistoryEntry)

    def get_guest_permissions(self, group_id: int) -> RobloxRecord:
        """Return the guest-role permissions as a :class:`RobloxRecord` (``groupId``, ``role``, ``permissions{...}`` in Roblox's own spelling)."""
        return RobloxRecord.model_validate(
            self.client.get(f"{self.BASE}/v1/groups/{group_id}/roles/guest/permissions"))

    # -- by user --------------------------------------------------------------

    def get_user_groups(self, user_id: int) -> list[UserGroupMembership]:
        """Return the groups a user belongs to as :class:`UserGroupMembership` records (``.group``, ``.role``, ``.is_primary_group``)."""
        body = self.client.get(f"{self.BASE}/v1/users/{user_id}/groups/roles")
        return UserGroupMembership.from_list(body.get("data"))

    def get_user_primary_group(self, user_id: int) -> Optional[UserGroupMembership]:
        """Return the user's primary group as a :class:`UserGroupMembership` (``.group``, ``.role``), or None if they have none (Roblox answers an empty or null body)."""
        body = self.client.get(f"{self.BASE}/v1/users/{user_id}/groups/primary/role")
        return UserGroupMembership.model_validate(body) if body else None

    # -- search ---------------------------------------------------------------

    def search(self, keyword: str, max_items: Optional[int] = None,
               prioritize_exact_match: bool = True) -> PagedList[GroupSearchResult]:
        """Return the :class:`GroupSearchResult` hits for ``keyword`` (id, name, description, member_count, previous_name, public_entry_allowed, created, updated), 100 per page."""
        params = {"keyword": keyword,
                  "prioritizeExactMatch": "true" if prioritize_exact_match else "false"}
        return self.client.fetch_all(f"{self.BASE}/v1/groups/search", params,
                                     limit=100, max_items=max_items, model=GroupSearchResult)

    def lookup(self, group_name: str) -> list[GroupSearchResult]:
        """Return the :class:`GroupSearchResult` records whose name matches ``group_name`` (id, name, member_count, has_verified_badge)."""
        body = self.client.get(f"{self.BASE}/v1/groups/search/lookup", {"groupName": group_name})
        return GroupSearchResult.from_list(body.get("data"))
