"""Interface to catalog.roblox.com endpoints."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from pyroblox import _endpoints as ep
from pyroblox.models.catalog import Bundle, CatalogItem
from pyroblox.pagination import CursorPage, paginate

if TYPE_CHECKING:
    from pyroblox.client import RobloxClient


class CatalogAPI:
    """Methods for the Roblox Catalog API."""

    def __init__(self, client: RobloxClient) -> None:
        self._client = client

    def search(
        self,
        *,
        keyword: str | None = None,
        asset_type_ids: list[int] | None = None,
        category: str | None = None,
        sort_type: int | None = None,
        creator_name: str | None = None,
        min_price: int | None = None,
        max_price: int | None = None,
        limit: int = 30,
        max_pages: int | None = None,
    ) -> Iterator[CatalogItem]:
        """Search the Roblox catalog with filters.

        Args:
            keyword: Search term.
            asset_type_ids: Filter by asset type (e.g. [8] for hats).
            category: Category filter string.
            sort_type: Sort type (0=Relevance, 1=Favorited,
                2=Sales, 3=Updated, 4=PriceAsc, 5=PriceDesc).
            creator_name: Filter by creator.
            min_price: Minimum price in Robux.
            max_price: Maximum price in Robux.
            limit: Results per page (10, 28, or 30).
            max_pages: Safety limit on total pages fetched.
        """
        def fetch_page(cursor: str | None) -> CursorPage[CatalogItem]:
            params: dict[str, Any] = {"limit": limit}
            if keyword is not None:
                params["Keyword"] = keyword
            if asset_type_ids is not None:
                for i, atid in enumerate(asset_type_ids):
                    params[f"AssetTypeIds[{i}]"] = atid
            if category is not None:
                params["CategoryFilter"] = category
            if sort_type is not None:
                params["SortType"] = sort_type
            if creator_name is not None:
                params["CreatorName"] = creator_name
            if min_price is not None:
                params["MinPrice"] = min_price
            if max_price is not None:
                params["MaxPrice"] = max_price
            if cursor:
                params["cursor"] = cursor
            resp = self._client.get("catalog", ep.CATALOG_SEARCH, params=params)
            raw = resp.json()
            return CursorPage(
                data=[CatalogItem.model_validate(i) for i in raw.get("data", [])],
                next_page_cursor=raw.get("nextPageCursor"),
                previous_page_cursor=raw.get("previousPageCursor"),
            )

        return paginate(fetch_page, max_pages=max_pages)

    def get_item_details(self, items: list[dict[str, Any]]) -> list[CatalogItem]:
        """Batch hydrate catalog item details.

        Args:
            items: List of dicts with ``itemType`` ("Asset" or "Bundle") and ``id``.

        Example::

            details = client.catalog.get_item_details([
                {"itemType": "Asset", "id": 1234},
                {"itemType": "Bundle", "id": 567},
            ])
        """
        resp = self._client.post(
            "catalog", ep.CATALOG_ITEM_DETAILS, json={"items": items}
        )
        data = resp.json()
        return [CatalogItem.model_validate(d) for d in data.get("data", [])]

    def get_bundle(self, bundle_id: int) -> Bundle:
        """Get details for a single bundle."""
        path = ep.BUNDLE_DETAILS.format(bundle_id=bundle_id)
        resp = self._client.get("catalog", path)
        return Bundle.model_validate(resp.json())

    def get_bundles(self, bundle_ids: list[int]) -> list[Bundle]:
        """Get details for multiple bundles."""
        resp = self._client.get(
            "catalog", ep.BUNDLE_DETAILS_BATCH,
            params={"bundleIds": ",".join(str(bid) for bid in bundle_ids)},
        )
        data = resp.json()
        return [Bundle.model_validate(b) for b in data]

    def get_asset_favorite_count(self, asset_id: int) -> int:
        """Get the number of favorites for an asset."""
        path = ep.ASSET_FAVORITE_COUNT.format(asset_id=asset_id)
        resp = self._client.get("catalog", path)
        return int(resp.json())

    def get_bundle_favorite_count(self, bundle_id: int) -> int:
        """Get the number of favorites for a bundle."""
        path = ep.BUNDLE_FAVORITE_COUNT.format(bundle_id=bundle_id)
        resp = self._client.get("catalog", path)
        return int(resp.json())

    def get_bundle_recommendations(self, bundle_id: int) -> list[Bundle]:
        """Get recommended bundles for a given bundle."""
        path = ep.BUNDLE_RECOMMENDATIONS.format(bundle_id=bundle_id)
        resp = self._client.get("catalog", path)
        data = resp.json()
        return [Bundle.model_validate(b) for b in data.get("data", [])]
