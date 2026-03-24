"""Models for the Catalog API."""

from __future__ import annotations

from pyroblox.models.base import RobloxModel


class CatalogItem(RobloxModel):
    id: int
    item_type: str | None = None
    asset_type: int | None = None
    bundle_type: int | None = None
    name: str | None = None
    description: str | None = None
    product_id: int | None = None
    price: int | None = None
    lowest_price: int | None = None
    price_status: str | None = None
    creator_name: str | None = None
    creator_type: str | None = None
    creator_target_id: int | None = None
    creator_has_verified_badge: bool = False
    favorite_count: int | None = None
    off_sale_deadline: str | None = None
    units_available_for_consumption: int | None = None


class BundleItem(RobloxModel):
    id: int
    name: str | None = None
    type: str | None = None


class BundleCreator(RobloxModel):
    id: int
    name: str | None = None
    type: str | None = None
    has_verified_badge: bool = False


class BundleProduct(RobloxModel):
    id: int | None = None
    is_for_sale: bool = False
    price_in_robux: int | None = None


class Bundle(RobloxModel):
    id: int
    name: str | None = None
    description: str | None = None
    bundle_type: str | None = None
    items: list[BundleItem] | None = None
    creator: BundleCreator | None = None
    product: BundleProduct | None = None
