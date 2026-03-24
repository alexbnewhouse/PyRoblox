"""Models for the Inventory API."""

from __future__ import annotations

from datetime import datetime

from pyroblox.models.base import RobloxModel


class AssetOwnerUser(RobloxModel):
    id: int
    type: str | None = None
    name: str | None = None


class CollectibleAsset(RobloxModel):
    user_asset_id: int
    asset_id: int
    name: str | None = None
    serial_number: int | None = None
    asset_stock: int | None = None
    recent_average_price: int | None = None
    original_price: int | None = None
    builders_club_member_only: bool | None = None


class InventoryItem(RobloxModel):
    asset_id: int | None = None
    name: str | None = None
    asset_type: str | None = None
    created: datetime | None = None


class AssetOwner(RobloxModel):
    id: int
    serial_number: int | None = None
    owner: AssetOwnerUser | None = None
    created: datetime | None = None
    updated: datetime | None = None
