"""Interface to groups.roblox.com endpoints."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from pyroblox import _endpoints as ep
from pyroblox.models.groups import Group, GroupMember, GroupRole, SocialLink
from pyroblox.pagination import CursorPage, paginate

if TYPE_CHECKING:
    from pyroblox.client import RobloxClient


class GroupsAPI:
    """Methods for the Roblox Groups API."""

    def __init__(self, client: RobloxClient) -> None:
        self._client = client

    def get_info(self, group_id: int) -> Group:
        """Get information about a group."""
        path = ep.GROUP_INFO.format(group_id=group_id)
        resp = self._client.get("groups", path)
        return Group.model_validate(resp.json())

    def get_allies(self, group_id: int) -> list[Group]:
        """Get all allied groups."""
        path = ep.GROUP_ALLIES.format(group_id=group_id)
        resp = self._client.get("groups", path, params={
            "model.startRowIndex": 0,
            "model.maxRows": 100,
        })
        data = resp.json()
        return [Group.model_validate(g) for g in data.get("relatedGroups", [])]

    def get_enemies(self, group_id: int) -> list[Group]:
        """Get all enemy groups."""
        path = ep.GROUP_ENEMIES.format(group_id=group_id)
        resp = self._client.get("groups", path, params={
            "model.startRowIndex": 0,
            "model.maxRows": 100,
        })
        data = resp.json()
        return [Group.model_validate(g) for g in data.get("relatedGroups", [])]

    def get_members(
        self, group_id: int, *, limit: int = 100, max_pages: int | None = None
    ) -> Iterator[GroupMember]:
        """Lazily iterate all group members with automatic pagination.

        Args:
            group_id: The group to list members for.
            limit: Members per page (max 100).
            max_pages: Safety limit on total pages fetched.
        """
        def fetch_page(cursor: str | None) -> CursorPage[GroupMember]:
            path = ep.GROUP_MEMBERS.format(group_id=group_id)
            params: dict[str, str | int] = {"sortOrder": "Asc", "limit": limit}
            if cursor:
                params["cursor"] = cursor
            resp = self._client.get("groups", path, params=params)
            raw = resp.json()
            return CursorPage(
                data=[GroupMember.model_validate(m) for m in raw.get("data", [])],
                next_page_cursor=raw.get("nextPageCursor"),
                previous_page_cursor=raw.get("previousPageCursor"),
            )

        return paginate(fetch_page, max_pages=max_pages)

    def get_roles(self, group_id: int) -> list[GroupRole]:
        """Get all roles in a group."""
        path = ep.GROUP_ROLES.format(group_id=group_id)
        resp = self._client.get("groups", path)
        data = resp.json()
        return [GroupRole.model_validate(r) for r in data.get("roles", [])]

    def get_social_links(self, group_id: int) -> list[SocialLink]:
        """Get group social links. Requires authentication."""
        path = ep.GROUP_SOCIAL_LINKS.format(group_id=group_id)
        resp = self._client.get("groups", path)
        data = resp.json()
        return [SocialLink.model_validate(s) for s in data.get("data", [])]
