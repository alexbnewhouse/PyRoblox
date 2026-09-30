"""Catalog items, places and bundles as products: economy details, catalog
details, bundle membership and limited-item resale data from
``economy.roblox.com`` and ``catalog.roblox.com``. Nothing here needs a cookie;
the catalog details POST needs a CSRF token, which the client obtains itself.
"""

from __future__ import annotations

from typing import Iterable, List, Optional

from .client import PagedList, RobloxClient, chunked


class AssetsAPI:
    """Asset, catalog item and bundle lookups."""

    BASE = "https://economy.roblox.com"
    CATALOG = "https://catalog.roblox.com"

    def __init__(self, client: RobloxClient):
        self.client = client

    def details(self, asset_id: int) -> dict:
        """Economy details for an asset or place (PascalCase keys: AssetId, Name,
        AssetTypeId, Creator, Created, Updated, PriceInRobux, Sales, IsLimited...)."""
        return self.client.get(f"{self.BASE}/v2/assets/{asset_id}/details")

    def catalog_details(self, items: Iterable[dict]) -> list:
        """Catalog details for ``{"itemType": "Asset"|"Bundle", "id": n}`` items.
        Roblox answers the first call with 403 + an x-csrf-token header; the
        client handles that automatically."""
        url = f"{self.CATALOG}/v1/catalog/items/details"
        out: List[dict] = []
        for chunk in chunked(items, 100):
            body = self.client.post(url, {"items": list(chunk)})
            out.extend(body.get("data") or [])
        return out

    def catalog_asset_details(self, asset_ids: Iterable[int]) -> list:
        """Catalog details for asset ids (itemType Asset)."""
        return self.catalog_details({"itemType": "Asset", "id": i} for i in asset_ids)

    def bundles(self, asset_id: int, max_items: Optional[int] = None) -> PagedList:
        """Bundles that include this asset (id, name, bundleType, creator)."""
        url = f"{self.CATALOG}/v1/assets/{asset_id}/bundles"
        return self.client.fetch_all(url, limit=100, max_items=max_items, sort_order="Asc")

    def resale(self, asset_id: int) -> dict:
        """Resale statistics for a limited item (recentAveragePrice, priceDataPoints...);
        non-limited items raise BadRequestError."""
        return self.client.get(f"{self.BASE}/v1/assets/{asset_id}/resale-data")

    def bundle_details(self, bundle_id: int) -> dict:
        """One bundle: id, name, bundleType, items[], creator, product."""
        return self.client.get(f"{self.CATALOG}/v1/bundles/{bundle_id}/details")
