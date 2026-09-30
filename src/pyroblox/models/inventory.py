"""Models for inventory.roblox.com and the user-owned listings on catalog.roblox.com."""

from __future__ import annotations

from datetime import datetime

from .base import RobloxModel
from .catalog import Bundle, BundleCreator  # noqa: F401  (one Bundle model for both APIs)


class CollectibleAsset(RobloxModel):
    """A limited / collectible item a user owns (``assets/collectibles`` rows)."""

    user_asset_id: int
    serial_number: int | None = None
    asset_id: int | None = None
    name: str | None = None
    recent_average_price: int | None = None
    original_price: int | None = None
    asset_stock: int | None = None
    builders_club_membership_type: str | None = None
    is_on_hold: bool | None = None


class InventoryOwner(RobloxModel):
    """The owner of an inventory item or collectible copy (``owner``)."""

    user_id: int | None = None
    username: str | None = None
    display_name: str | None = None


class InventoryItem(RobloxModel):
    """One owned item of an asset type (``v2/users/{id}/inventory/{type}`` rows)."""

    user_asset_id: int
    asset_id: int | None = None
    asset_name: str | None = None
    collectible_item_id: str | None = None
    serial_number: int | None = None
    owner: InventoryOwner | None = None
    created: datetime | None = None
    updated: datetime | None = None


class AssetOwner(RobloxModel):
    """One copy of a collectible asset and who holds it (``v2/assets/{id}/owners`` rows)."""

    id: int
    collectible_item_instance_id: str | None = None
    serial_number: int | None = None
    owner: InventoryOwner | None = None
    created: datetime | None = None
    updated: datetime | None = None



