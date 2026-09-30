"""Models for ``catalog.roblox.com`` and ``economy.roblox.com`` responses."""

from __future__ import annotations

from datetime import datetime

from .base import PascalModel, RobloxModel


class CatalogItem(RobloxModel):
    """One catalog item as returned by ``catalog/v1/catalog/items/details`` and favourites."""

    id: int
    item_type: str | None = None
    asset_type: int | str | None = None
    name: str | None = None
    description: str | None = None
    product_id: int | None = None
    creator_type: str | None = None
    creator_target_id: int | None = None
    creator_name: str | None = None
    price: int | None = None
    lowest_price: int | None = None
    lowest_resale_price: int | None = None
    favorite_count: int | None = None
    item_restrictions: list[str] | None = None
    collectible_item_id: str | None = None
    total_quantity: int | None = None
    is_off_sale: bool | None = None
    units_available_for_consumption: int | None = None
    creator_has_verified_badge: bool = False


class BundleCreator(RobloxModel):
    """Creator of a bundle."""

    id: int
    name: str | None = None
    type: str | None = None
    has_verified_badge: bool = False


class Bundle(RobloxModel):
    """A bundle (package of avatar items)."""

    id: int
    name: str | None = None
    description: str | None = None
    bundle_type: str | None = None
    creator: BundleCreator | None = None
    items: list | None = None
    product: dict | None = None


class EconomyCreator(PascalModel):
    """``Creator`` block of an economy asset-details answer (``Id``, ``Name``, ``CreatorType``...)."""

    id: int
    name: str | None = None
    creator_type: str | None = None
    creator_target_id: int | None = None
    has_verified_badge: bool = False


class EconomyAssetDetails(PascalModel):
    """An asset or place as ``economy.roblox.com/v2/assets/{id}/details`` describes it (PascalCase keys)."""

    asset_id: int
    product_id: int | None = None
    name: str | None = None
    description: str | None = None
    asset_type_id: int | None = None
    creator: EconomyCreator | None = None
    created: datetime | None = None
    updated: datetime | None = None
    price_in_robux: int | None = None
    sales: int | None = None
    is_for_sale: bool | None = None
    is_limited: bool | None = None
    is_limited_unique: bool | None = None
    is_public_domain: bool | None = None
    remaining: int | None = None
    collectible_item_id: str | None = None


class ResaleData(RobloxModel):
    """Resale statistics for a limited item from ``economy.roblox.com/v1/assets/{id}/resale-data``."""

    asset_stock: int | None = None
    sales: int | None = None
    number_remaining: int | None = None
    recent_average_price: int | None = None
    original_price: int | None = None
    price_data_points: list | None = None
    volume_data_points: list | None = None
