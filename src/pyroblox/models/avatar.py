"""Models for avatar.roblox.com: a user's avatar, worn assets and outfits."""

from __future__ import annotations

from .base import RobloxModel


class AvatarAssetType(RobloxModel):
    """The asset type of a worn avatar asset (``assetType``)."""

    id: int
    name: str | None = None


class AvatarAsset(RobloxModel):
    """One asset a user is wearing (``assets[]`` of the avatar object)."""

    id: int
    name: str | None = None
    asset_type: AvatarAssetType | None = None
    current_version_id: int | None = None
    supports_head_shapes: bool | None = None


class BodyColors(RobloxModel):
    """BrickColor ids per body part (``bodyColors``)."""

    head_color_id: int | None = None
    torso_color_id: int | None = None
    right_arm_color_id: int | None = None
    left_arm_color_id: int | None = None
    right_leg_color_id: int | None = None
    left_leg_color_id: int | None = None


class AvatarScales(RobloxModel):
    """Avatar scaling values (``scales``)."""

    height: float | None = None
    width: float | None = None
    head: float | None = None
    depth: float | None = None
    proportion: float | None = None
    body_type: float | None = None


class Avatar(RobloxModel):
    """A user's current avatar: type, colours, scales and worn assets."""

    player_avatar_type: str | None = None
    body_colors: BodyColors | None = None
    scales: AvatarScales | None = None
    assets: list[AvatarAsset] = []
    default_shirt_applied: bool | None = None
    default_pants_applied: bool | None = None
    emotes: list | None = None


class Outfit(RobloxModel):
    """A saved outfit (``users/{id}/outfits`` rows)."""

    id: int
    name: str | None = None
    is_editable: bool | None = None
    outfit_type: str | None = None
