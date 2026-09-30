"""Models for groups.roblox.com: groups, members, roles, relationships, search."""

from __future__ import annotations

from datetime import datetime

from .base import RobloxModel


class GroupUser(RobloxModel):
    """A user as embedded in group payloads (owner, shout poster, member, role holder)."""

    user_id: int
    username: str | None = None
    display_name: str | None = None
    has_verified_badge: bool = False


GroupOwner = GroupUser


class GroupShout(RobloxModel):
    """A group's current shout (status message) and who posted it."""

    body: str | None = None
    poster: GroupUser | None = None
    created: datetime | None = None
    updated: datetime | None = None


class GroupRole(RobloxModel):
    """A role (rank) inside a group."""

    id: int
    name: str
    rank: int | None = None
    member_count: int | None = None
    color: int | None = None
    is_base: bool | None = None


class Group(RobloxModel):
    """A full group object (``GET /v1/groups/{id}``, allies/enemies, user memberships)."""

    id: int
    name: str
    description: str | None = None
    owner: GroupUser | None = None
    shout: GroupShout | None = None
    member_count: int | None = None
    is_builders_club_only: bool | None = None
    public_entry_allowed: bool | None = None
    is_locked: bool | None = None
    has_verified_badge: bool = False
    has_social_modules: bool | None = None


class GroupOwnerRef(RobloxModel):
    """Owner reference in the v2 batch group shape (``{id, type}``)."""

    id: int
    type: str | None = None


class GroupSummary(RobloxModel):
    """The compact v2 group record returned by ``GET /v2/groups?groupIds=``."""

    id: int
    name: str
    description: str | None = None
    owner: GroupOwnerRef | None = None
    created: datetime | None = None
    has_verified_badge: bool = False


class GroupMember(RobloxModel):
    """One ``{user, role}`` row of a group's member list."""

    user: GroupUser
    role: GroupRole | None = None


class SocialLink(RobloxModel):
    """A social link on a group's profile (Discord, YouTube, ...)."""

    id: int
    type: str
    url: str
    title: str | None = None


class GroupNameHistoryEntry(RobloxModel):
    """A previous name of a group."""

    name: str
    created: datetime | None = None


class UserGroupMembership(RobloxModel):
    """A group a user belongs to, with their role (``/v1/users/{id}/groups/roles``)."""

    group: Group
    role: GroupRole | None = None
    is_primary_group: bool | None = None


class GroupSearchResult(RobloxModel):
    """A hit from group search (``/v1/groups/search``) or name lookup."""

    id: int
    name: str
    description: str | None = None
    member_count: int | None = None
    previous_name: str | None = None
    public_entry_allowed: bool | None = None
    created: datetime | None = None
    updated: datetime | None = None
    has_verified_badge: bool = False
