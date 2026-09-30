"""Catalog items, places and bundles as products: economy details, catalog
details, bundle membership and limited-item resale data from
``economy.roblox.com`` and ``catalog.roblox.com``. Nothing here needs a cookie;
the catalog details POST needs a CSRF token, which the client obtains itself.

Answers are typed: :class:`~pyroblox.models.catalog.CatalogItem`,
:class:`~pyroblox.models.catalog.Bundle`,
:class:`~pyroblox.models.catalog.EconomyAssetDetails` and
:class:`~pyroblox.models.catalog.ResaleData`.
"""

from __future__ import annotations

from typing import Iterable, List, Optional

from .client import PagedList, RobloxClient, chunked
from .models.catalog import Bundle, CatalogItem, EconomyAssetDetails, ResaleData


class CatalogAPI:
    """Asset, catalog item and bundle lookups."""

    BASE = "https://economy.roblox.com"
    CATALOG = "https://catalog.roblox.com"

    def __init__(self, client: RobloxClient):
        self.client = client

    def get_item_details(self, items: Iterable[dict]) -> list[CatalogItem]:
        """Return the :class:`CatalogItem` list for ``{"itemType": "Asset"|"Bundle", "id": n}``
        items, POSTed in batches of 100. Roblox answers the first call with 403 +
        an x-csrf-token header; the client handles that automatically."""
        url = f"{self.CATALOG}/v1/catalog/items/details"
        out: List[dict] = []
        for chunk in chunked(items, 100):
            body = self.client.post(url, {"items": list(chunk)})
            out.extend(body.get("data") or [])
        return CatalogItem.from_list(out)

    def get_asset_item_details(self, asset_ids: Iterable[int]) -> list[CatalogItem]:
        """Return the :class:`CatalogItem` list for asset ids (itemType Asset)."""
        return self.get_item_details({"itemType": "Asset", "id": i} for i in asset_ids)

    def get_asset_bundles(self, asset_id: int,
                          max_items: Optional[int] = None) -> PagedList[Bundle]:
        """Return the :class:`Bundle` records (id, name, bundle_type, creator) that
        include this asset, as a :class:`PagedList`."""
        url = f"{self.CATALOG}/v1/assets/{asset_id}/bundles"
        return self.client.fetch_all(url, limit=100, max_items=max_items,
                                     sort_order="Asc", model=Bundle)

    def get_bundle(self, bundle_id: int) -> Bundle:
        """Return the :class:`Bundle` for one bundle id: id, name, bundle_type,
        items, creator, product."""
        return Bundle.model_validate(
            self.client.get(f"{self.CATALOG}/v1/bundles/{bundle_id}/details"))

    def get_economy_details(self, asset_id: int) -> EconomyAssetDetails:
        """Return the :class:`EconomyAssetDetails` for an asset or place. Roblox
        answers in PascalCase (AssetId, Name, AssetTypeId, Creator, Created,
        Updated, PriceInRobux, Sales, IsLimited...); read them as ``asset_id``,
        ``price_in_robux`` and so on."""
        return EconomyAssetDetails.model_validate(
            self.client.get(f"{self.BASE}/v2/assets/{asset_id}/details"))

    def get_resale_data(self, asset_id: int) -> ResaleData:
        """Return the :class:`ResaleData` for a limited item (recent_average_price,
        price_data_points...); non-limited items raise BadRequestError."""
        return ResaleData.model_validate(
            self.client.get(f"{self.BASE}/v1/assets/{asset_id}/resale-data"))
