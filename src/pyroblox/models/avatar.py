"""Models for the Avatar API."""

from __future__ import annotations

from pyroblox.models.base import RobloxModel


class BodyColors(RobloxModel):
    head_color_id: int | None = None
    torso_color_id: int | None = None
    right_arm_color_id: int | None = None
    left_arm_color_id: int | None = None
    right_leg_color_id: int | None = None
    left_leg_color_id: int | None = None


class AvatarScale(RobloxModel):
    height: float | None = None
    width: float | None = None
    head: float | None = None
    depth: float | None = None
    proportion: float | None = None
    body_type: float | None = None


class AvatarAssetType(RobloxModel):
    id: int
    name: str | None = None


class AvatarAsset(RobloxModel):
    id: int
    name: str | None = None
    asset_type: AvatarAssetType | None = None


class Avatar(RobloxModel):
    player_avatar_type: str | None = None
    body_colors: BodyColors | None = None
    scales: AvatarScale | None = None
    assets: list[AvatarAsset] | None = None
    default_shirt_applied: bool = False
    default_pants_applied: bool = False


class Outfit(RobloxModel):
    id: int
    name: str | None = None
    is_editable: bool = True
