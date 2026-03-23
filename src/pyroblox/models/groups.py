"""Models for the Groups API."""

from __future__ import annotations

from pyroblox.models.base import RobloxModel


class GroupOwner(RobloxModel):
    user_id: int | None = None
    username: str | None = None
    display_name: str | None = None
    has_verified_badge: bool = False


class Group(RobloxModel):
    id: int
    name: str
    description: str | None = None
    owner: GroupOwner | None = None
    shout: dict[str, object] | None = None
    member_count: int | None = None
    is_builders_club_only: bool | None = None
    public_entry_allowed: bool | None = None
    has_verified_badge: bool = False


class GroupRole(RobloxModel):
    id: int
    name: str
    rank: int | None = None
    member_count: int | None = None


class GroupMember(RobloxModel):
    user: GroupOwner
    role: GroupRole | None = None


class SocialLink(RobloxModel):
    id: int
    type: str
    url: str
    title: str
