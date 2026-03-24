"""Interface to inventory.roblox.com endpoints."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from pyroblox import _endpoints as ep
from pyroblox.models.inventory import AssetOwner, CollectibleAsset, InventoryItem
from pyroblox.pagination import paginate_endpoint

if TYPE_CHECKING:
    from pyroblox.client import RobloxClient


class InventoryAPI:
    """Methods for the Roblox Inventory API."""

    def __init__(self, client: RobloxClient) -> None:
        self._client = client

    def can_view(self, user_id: int) -> bool:
        """Check whether a user's inventory is publicly visible."""
        path = ep.USER_CAN_VIEW_INVENTORY.format(user_id=user_id)
        resp = self._client.get("inventory", path)
        return resp.json().get("canView", False)  # type: ignore[no-any-return]

    def get_collectibles(
        self, user_id: int, *, limit: int = 100, max_pages: int | None = None
    ) -> Iterator[CollectibleAsset]:
        """Lazily iterate a user's collectible (limited) items."""
        path = ep.USER_COLLECTIBLES.format(user_id=user_id)
        return paginate_endpoint(
            self._client, "inventory", path, CollectibleAsset,
            limit=limit, max_pages=max_pages,
            extra_params={"sortOrder": "Asc"},
        )

    def get_user_inventory(
        self,
        user_id: int,
        asset_type_id: int,
        *,
        limit: int = 100,
        max_pages: int | None = None,
    ) -> Iterator[InventoryItem]:
        """Lazily iterate a user's inventory filtered by asset type.

        Args:
            user_id: The user whose inventory to fetch.
            asset_type_id: Roblox asset type ID (e.g. 8=Hat, 11=Shirt, 12=Pants).
            limit: Items per page.
            max_pages: Safety limit on total pages fetched.
        """
        path = ep.USER_INVENTORY.format(
            user_id=user_id, asset_type_id=asset_type_id
        )
        return paginate_endpoint(
            self._client, "inventory", path, InventoryItem,
            limit=limit, max_pages=max_pages,
            extra_params={"sortOrder": "Asc"},
        )

    def get_asset_owners(
        self, asset_id: int, *, limit: int = 100, max_pages: int | None = None
    ) -> Iterator[AssetOwner]:
        """Lazily iterate owners of a specific asset."""
        path = ep.ASSET_OWNERS.format(asset_id=asset_id)
        return paginate_endpoint(
            self._client, "inventory", path, AssetOwner,
            limit=limit, max_pages=max_pages,
            extra_params={"sortOrder": "Asc"},
        )
