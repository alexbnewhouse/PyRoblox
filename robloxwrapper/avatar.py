"""What a user looks like and owns: the avatar (``avatar.roblox.com``), the
inventory and collectibles (``inventory.roblox.com`` / ``catalog.roblox.com``),
account-level facts such as Roblox badges and promotion channels
(``accountinformation.roblox.com``), and online presence
(``presence.roblox.com``). Everything here works without a cookie, though a
private inventory answers 403 and promotion channels come back null unless you
supply one.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from .client import PagedList, RobloxClient, chunked

#: Roblox asset type ids for :meth:`InventoryAPI.items` / :meth:`InventoryAPI.favorite_assets`.
ASSET_TYPES: Dict[str, int] = {
    "hat": 8, "tshirt": 2, "shirt": 11, "pants": 12, "face": 18, "gear": 19,
    "head": 17, "hair": 41, "face_accessory": 42, "neck_accessory": 43,
    "shoulder_accessory": 44, "front_accessory": 45, "back_accessory": 46,
    "waist_accessory": 47, "emote": 61, "place": 9, "model": 10, "decal": 13,
    "audio": 3, "animation": 24, "video": 62,
}


class AvatarAPI:
    """A user's current avatar, worn assets and saved outfits (avatar.roblox.com)."""

    BASE = "https://avatar.roblox.com"

    def __init__(self, client: RobloxClient):
        self.client = client

    def get(self, user_id: int) -> dict:
        """The avatar object: playerAvatarType, bodyColors, scales, assets[]."""
        return self.client.get(f"{self.BASE}/v1/users/{user_id}/avatar")

    def currently_wearing(self, user_id: int) -> List[int]:
        """Asset ids the user is wearing. Roblox allows about 6 calls per minute unauthenticated."""
        body = self.client.get(f"{self.BASE}/v1/users/{user_id}/currently-wearing")
        return body.get("assetIds") or []

    def outfits(self, user_id: int, max_items: Optional[int] = None) -> list:
        """The user's saved outfits (id, name, isEditable), walking ``page`` until done."""
        url = f"{self.BASE}/v1/users/{user_id}/outfits"
        items: List[dict] = []
        page_no = 1
        while True:
            body = self.client.get(url, {"page": page_no, "itemsPerPage": 50,
                                         "isEditable": "true"})
            data = body.get("data") or []
            if not data:
                break
            items.extend(data)
            if max_items is not None and len(items) >= max_items:
                return items[:max_items]
            total = body.get("total")
            if total is not None and len(items) >= total:
                break
            page_no += 1
        return items


class InventoryAPI:
    """What a user owns: collectibles, items by type, favourites and bundles."""

    BASE = "https://inventory.roblox.com"
    CATALOG = "https://catalog.roblox.com"

    def __init__(self, client: RobloxClient):
        self.client = client

    def can_view(self, user_id: int) -> bool:
        """Whether the user's inventory is visible to you. Roblox allows about 1 call per minute unauthenticated."""
        body = self.client.get(f"{self.BASE}/v1/users/{user_id}/can-view-inventory")
        return bool(body.get("canView"))

    def collectibles(self, user_id: int, max_items: Optional[int] = None) -> PagedList:
        """Limited / collectible items the user owns, with recentAveragePrice."""
        url = f"{self.BASE}/v1/users/{user_id}/assets/collectibles"
        return self.client.fetch_all(url, limit=100, max_items=max_items, sort_order="Asc")

    def items(self, user_id: int, asset_type_id: int,
              max_items: Optional[int] = None) -> PagedList:
        """Owned items of one asset type (see ``ASSET_TYPES``); a private inventory raises PrivateError."""
        url = f"{self.BASE}/v2/users/{user_id}/inventory/{asset_type_id}"
        return self.client.fetch_all(url, limit=100, max_items=max_items, sort_order="Asc")

    def asset_owners(self, asset_id: int, max_items: Optional[int] = None) -> PagedList:
        """Every copy of a collectible asset (id, serialNumber, owner - null unauthenticated, created)."""
        url = f"{self.BASE}/v2/assets/{asset_id}/owners"
        return self.client.fetch_all(url, limit=100, max_items=max_items, sort_order="Asc")

    def favorite_assets(self, user_id: int, asset_type_id: int,
                        max_items: Optional[int] = None) -> PagedList:
        """Catalog items of one asset type the user has favourited. Roblox allows about 10 calls per minute unauthenticated."""
        url = f"{self.CATALOG}/v1/favorites/users/{user_id}/favorites/{asset_type_id}/assets"
        return self.client.fetch_all(url, limit=100, max_items=max_items)

    def bundles(self, user_id: int, max_items: Optional[int] = None) -> PagedList:
        """Bundles the user owns (id, name, bundleType, creator). Roblox allows about 10 calls per minute unauthenticated."""
        url = f"{self.CATALOG}/v1/users/{user_id}/bundles"
        return self.client.fetch_all(url, limit=100, max_items=max_items, sort_order="Asc")


class AccountAPI:
    """Account-level facts from accountinformation.roblox.com."""

    BASE = "https://accountinformation.roblox.com"

    def __init__(self, client: RobloxClient):
        self.client = client

    def roblox_badges(self, user_id: int) -> list:
        """Roblox's own (non-game) badges the user holds: id, name, description, imageUrl."""
        return self.client.get(f"{self.BASE}/v1/users/{user_id}/roblox-badges")

    def promotion_channels(self, user_id: int) -> dict:
        """Linked social channels (facebook, twitter, youtube, twitch, guilded).
        Values are null unless you supply a cookie."""
        return self.client.get(f"{self.BASE}/v1/users/{user_id}/promotion-channels")


class PresenceAPI:
    """Who is online right now and when they were last seen (presence.roblox.com)."""

    BASE = "https://presence.roblox.com"

    def __init__(self, client: RobloxClient):
        self.client = client

    def get(self, user_ids: Iterable[int]) -> list:
        """Presence per user: userPresenceType (0 offline, 1 online, 2 in game,
        3 studio), lastLocation, placeId, rootPlaceId, gameId, universeId, lastOnline."""
        url = f"{self.BASE}/v1/presence/users"
        out: List[dict] = []
        for chunk in chunked(user_ids, 100):
            body = self.client.post(url, {"userIds": list(chunk)})
            out.extend(body.get("userPresences") or [])
        return out

    def last_online(self, user_ids: Iterable[int]) -> list:
        """Last-online timestamps per user (userId, lastOnline)."""
        url = f"{self.BASE}/v1/presence/last-online"
        out: List[dict] = []
        for chunk in chunked(user_ids, 100):
            body = self.client.post(url, {"userIds": list(chunk)})
            out.extend(body.get("lastOnlineTimestamps") or [])
        return out
