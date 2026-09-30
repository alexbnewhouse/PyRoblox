"""Tests for robloxwrapper.avatar: AvatarAPI, InventoryAPI, AccountAPI,
PresenceAPI and the ASSET_TYPES table. No network."""

import pytest

from robloxwrapper.avatar import (
    ASSET_TYPES, AccountAPI, AvatarAPI, InventoryAPI, PresenceAPI,
)
from robloxwrapper.client import PagedList
from robloxwrapper.errors import PrivateError
from tests.conftest import FakeResponse, make_client, page

AVATAR = "https://avatar.roblox.com"
INVENTORY = "https://inventory.roblox.com"
CATALOG = "https://catalog.roblox.com"
ACCOUNT = "https://accountinformation.roblox.com"
PRESENCE = "https://presence.roblox.com"


def test_client_exposes_the_four_apis():
    client, _, _ = make_client(routes={})
    assert isinstance(client.avatar, AvatarAPI) and client.avatar.client is client
    assert isinstance(client.inventory, InventoryAPI) and client.inventory.client is client
    assert isinstance(client.account, AccountAPI) and client.account.client is client
    assert isinstance(client.presence, PresenceAPI) and client.presence.client is client
    assert AvatarAPI.BASE == AVATAR
    assert InventoryAPI.BASE == INVENTORY
    assert AccountAPI.BASE == ACCOUNT
    assert PresenceAPI.BASE == PRESENCE


def test_asset_types_table():
    assert ASSET_TYPES == {
        "hat": 8, "tshirt": 2, "shirt": 11, "pants": 12, "face": 18, "gear": 19,
        "head": 17, "hair": 41, "face_accessory": 42, "neck_accessory": 43,
        "shoulder_accessory": 44, "front_accessory": 45, "back_accessory": 46,
        "waist_accessory": 47, "emote": 61, "place": 9, "model": 10, "decal": 13,
        "audio": 3, "animation": 24, "video": 62,
    }


# -- AvatarAPI ----------------------------------------------------------------

AVATAR_BODY = {
    "scales": {"height": 1.0, "width": 1.0, "head": 1.0, "depth": 1.0,
               "proportion": 0.0, "bodyType": 0.0},
    "playerAvatarType": "R6",
    "bodyColors": {"headColorId": 24, "torsoColorId": 1003, "rightArmColorId": 24,
                   "leftArmColorId": 24, "rightLegColorId": 23, "leftLegColorId": 23},
    "assets": [
        {"id": 1006027, "name": "Got Root?", "assetType": {"id": 2, "name": "TShirt"},
         "currentVersionId": 6028},
        {"id": 1028859, "name": "Pirate Captain's Hat", "assetType": {"id": 8, "name": "Hat"},
         "currentVersionId": 883359752},
    ],
}


def test_avatar_get_returns_object():
    client, session, _ = make_client(routes={f"GET {AVATAR}/v1/users/261/avatar": AVATAR_BODY})
    assert client.avatar.get(261) == AVATAR_BODY
    assert session.calls[0].method == "GET" and session.calls[0].params is None


def test_avatar_currently_wearing_unwraps_asset_ids():
    ids = [1006027, 1028859, 76691628978545, 93075310246069, 111989654515290]
    client, session, _ = make_client(routes={
        f"GET {AVATAR}/v1/users/261/currently-wearing": {"assetIds": ids},
    })
    assert client.avatar.currently_wearing(261) == ids
    assert session.calls[0].params is None


def _outfit(i):
    return {"id": i, "name": f"Outfit {i}", "isEditable": True, "outfitType": "Avatar"}


def _outfits_page(items, total):
    return {"filteredCount": total, "data": items, "total": total}


def test_avatar_outfits_walks_pages_until_total_reached():
    first = [_outfit(i) for i in range(1, 51)]
    second = [_outfit(i) for i in range(51, 61)]
    client, session, _ = make_client(routes={
        f"GET {AVATAR}/v1/users/261/outfits?page=1&itemsPerPage=50&isEditable=true":
            _outfits_page(first, 60),
        f"GET {AVATAR}/v1/users/261/outfits?page=2&itemsPerPage=50&isEditable=true":
            _outfits_page(second, 60),
    })
    out = client.avatar.outfits(261)
    assert out == first + second and type(out) is list
    assert len(session.calls) == 2
    assert session.calls[0].params == {"page": 1, "itemsPerPage": 50, "isEditable": "true"}
    assert session.calls[1].params == {"page": 2, "itemsPerPage": 50, "isEditable": "true"}


def test_avatar_outfits_single_page_when_total_covered():
    items = [_outfit(1), _outfit(2)]
    client, session, _ = make_client(routes={
        f"GET {AVATAR}/v1/users/261/outfits": _outfits_page(items, 2),
    })
    assert client.avatar.outfits(261) == items
    assert len(session.calls) == 1


def test_avatar_outfits_stops_on_empty_page():
    # ``total`` over-reports; the empty second page must end the loop.
    client, session, _ = make_client(routes={
        f"GET {AVATAR}/v1/users/261/outfits?page=1&itemsPerPage=50&isEditable=true":
            _outfits_page([_outfit(1)], 5),
        f"GET {AVATAR}/v1/users/261/outfits?page=2&itemsPerPage=50&isEditable=true":
            _outfits_page([], 5),
    })
    assert client.avatar.outfits(261) == [_outfit(1)]
    assert len(session.calls) == 2


def test_avatar_outfits_stops_when_total_missing_and_page_empty():
    client, session, _ = make_client(routes={
        f"GET {AVATAR}/v1/users/261/outfits?page=1&itemsPerPage=50&isEditable=true":
            {"data": [_outfit(1)]},
        f"GET {AVATAR}/v1/users/261/outfits?page=2&itemsPerPage=50&isEditable=true":
            {"data": []},
    })
    assert client.avatar.outfits(261) == [_outfit(1)]
    assert len(session.calls) == 2


def test_avatar_outfits_honours_max_items():
    client, session, _ = make_client(routes={
        f"GET {AVATAR}/v1/users/261/outfits": _outfits_page([_outfit(i) for i in range(1, 4)], 100),
    })
    out = client.avatar.outfits(261, max_items=2)
    assert out == [_outfit(1), _outfit(2)]
    assert len(session.calls) == 1


# -- InventoryAPI -------------------------------------------------------------

COLLECTIBLE = {
    "userAssetId": 115160, "serialNumber": None, "assetId": 1082932, "name": "Traffic Cone",
    "recentAveragePrice": 3411, "originalPrice": 80, "assetStock": 163907,
    "buildersClubMembershipType": "None", "isOnHold": False,
}
INVENTORY_ITEM = {
    "userAssetId": 29545, "assetId": 1028859, "assetName": "Pirate Captain's Hat",
    "collectibleItemId": None, "collectibleItemInstanceId": None, "serialNumber": None,
    "owner": {"userId": 261, "username": "Shedletsky", "buildersClubMembershipType": "None"},
    "created": "2007-05-30T22:08:18.697Z", "updated": "2007-05-30T22:08:18.697Z",
}
OWNER_ROW = {
    "id": 28605, "collectibleItemInstanceId": "fe0f7b73-91be-4050-a1b7-233f884eec33",
    "serialNumber": 0, "owner": None,
    "created": "2007-05-30T07:25:25.527Z", "updated": "2007-05-30T07:25:25.527Z",
}
BUNDLE = {"id": 1160, "name": "Heeeeeey...", "bundleType": "DynamicHead",
          "creator": {"id": 1, "name": "Roblox", "type": "User", "hasVerifiedBadge": True}}
FAVORITE = {"id": 1474657, "itemType": "Asset", "assetType": 8, "name": "The Dusekkar",
            "creatorType": "User", "creatorTargetId": 1, "creatorName": "Roblox",
            "price": 0, "favoriteCount": 33193, "isOffSale": True}


def test_inventory_can_view_unwraps_flag():
    client, session, _ = make_client(routes={
        f"GET {INVENTORY}/v1/users/261/can-view-inventory": {"canView": True},
    })
    assert client.inventory.can_view(261) is True
    assert session.calls[0].params is None


def test_inventory_collectibles_paginates():
    client, session, _ = make_client(routes={
        f"GET {INVENTORY}/v1/users/261/assets/collectibles":
            [page([COLLECTIBLE], "c1"), page([dict(COLLECTIBLE, userAssetId=2)], None)],
    })
    out = client.inventory.collectibles(261)
    assert isinstance(out, PagedList)
    assert [r["userAssetId"] for r in out] == [115160, 2] and out.truncated is False
    assert session.calls[0].params == {"limit": 100, "sortOrder": "Asc"}
    assert session.calls[1].params == {"limit": 100, "sortOrder": "Asc", "cursor": "c1"}


def test_inventory_collectibles_max_items():
    client, session, _ = make_client(routes={
        f"GET {INVENTORY}/v1/users/261/assets/collectibles":
            page([COLLECTIBLE, dict(COLLECTIBLE, userAssetId=2)], "c1"),
    })
    out = client.inventory.collectibles(261, max_items=1)
    assert out == [COLLECTIBLE] and out.truncated is True
    assert len(session.calls) == 1


def test_inventory_items_paginates_by_asset_type():
    client, session, _ = make_client(routes={
        f"GET {INVENTORY}/v2/users/261/inventory/8": page([INVENTORY_ITEM], None),
    })
    out = client.inventory.items(261, 8)
    assert isinstance(out, PagedList) and out == [INVENTORY_ITEM]
    assert session.calls[0].params == {"limit": 100, "sortOrder": "Asc"}


def test_inventory_items_max_items():
    client, session, _ = make_client(routes={
        f"GET {INVENTORY}/v2/users/261/inventory/8":
            page([INVENTORY_ITEM, dict(INVENTORY_ITEM, userAssetId=2)], "c1"),
    })
    out = client.inventory.items(261, ASSET_TYPES["hat"], max_items=1)
    assert out == [INVENTORY_ITEM] and out.truncated is True


def test_inventory_items_private_inventory_raises_private_error():
    client, _, _ = make_client([FakeResponse(403)])
    with pytest.raises(PrivateError):
        client.inventory.items(261, 8)


def test_inventory_asset_owners_paginates():
    client, session, _ = make_client(routes={
        f"GET {INVENTORY}/v2/assets/1028606/owners":
            [page([OWNER_ROW], "c1"), page([dict(OWNER_ROW, id=28606)], None)],
    })
    out = client.inventory.asset_owners(1028606)
    assert isinstance(out, PagedList)
    assert [r["id"] for r in out] == [28605, 28606]
    assert session.calls[0].params == {"limit": 100, "sortOrder": "Asc"}
    assert session.calls[1].params == {"limit": 100, "sortOrder": "Asc", "cursor": "c1"}


def test_inventory_asset_owners_max_items():
    client, session, _ = make_client(routes={
        f"GET {INVENTORY}/v2/assets/1028606/owners":
            page([OWNER_ROW, dict(OWNER_ROW, id=28606)], "c1"),
    })
    out = client.inventory.asset_owners(1028606, max_items=1)
    assert out == [OWNER_ROW] and out.truncated is True


def test_inventory_favorite_assets_uses_catalog_host_without_sort_order():
    client, session, _ = make_client(routes={
        f"GET {CATALOG}/v1/favorites/users/261/favorites/8/assets": page([FAVORITE], None),
    })
    out = client.inventory.favorite_assets(261, 8)
    assert isinstance(out, PagedList) and out == [FAVORITE]
    assert session.calls[0].params == {"limit": 100}


def test_inventory_favorite_assets_max_items():
    client, session, _ = make_client(routes={
        f"GET {CATALOG}/v1/favorites/users/261/favorites/8/assets":
            page([FAVORITE, dict(FAVORITE, id=2)], "c1"),
    })
    out = client.inventory.favorite_assets(261, 8, max_items=1)
    assert out == [FAVORITE] and out.truncated is True


def test_inventory_bundles_paginates_on_catalog_host():
    client, session, _ = make_client(routes={
        f"GET {CATALOG}/v1/users/261/bundles":
            [page([BUNDLE], "c1"), page([dict(BUNDLE, id=1153)], None)],
    })
    out = client.inventory.bundles(261)
    assert isinstance(out, PagedList)
    assert [b["id"] for b in out] == [1160, 1153]
    assert session.calls[0].params == {"limit": 100, "sortOrder": "Asc"}
    assert session.calls[1].params == {"limit": 100, "sortOrder": "Asc", "cursor": "c1"}


def test_inventory_bundles_max_items():
    client, session, _ = make_client(routes={
        f"GET {CATALOG}/v1/users/261/bundles": page([BUNDLE, dict(BUNDLE, id=1153)], "c1"),
    })
    out = client.inventory.bundles(261, max_items=1)
    assert out == [BUNDLE] and out.truncated is True


# -- AccountAPI ---------------------------------------------------------------

ROBLOX_BADGES = [
    {"id": 2, "name": "Friendship", "description": "This badge was given to members ...",
     "imageUrl": "https://images.rbxcdn.com/5eb20917cf530583e2641c0e1f7ba95e.png"},
    {"id": 3, "name": "Combat Initiation", "description": "This badge was granted ...",
     "imageUrl": "https://images.rbxcdn.com/8d77254fc1e6d904fd3ded29dfca28cb.png"},
]


def test_account_roblox_badges_returns_bare_array():
    # a list-valued route means "responses in turn" to FakeSession, so wrap it
    client, session, _ = make_client(routes={
        f"GET {ACCOUNT}/v1/users/261/roblox-badges": FakeResponse(200, ROBLOX_BADGES),
    })
    assert client.account.roblox_badges(261) == ROBLOX_BADGES
    assert session.calls[0].method == "GET" and session.calls[0].params is None


def test_account_promotion_channels_returns_object():
    body = {"facebook": None, "twitter": None, "youtube": None, "twitch": None}
    client, session, _ = make_client(routes={
        f"GET {ACCOUNT}/v1/users/261/promotion-channels": body,
    })
    assert client.account.promotion_channels(261) == body
    assert session.calls[0].params is None


# -- PresenceAPI --------------------------------------------------------------

def _presence(uid):
    return {"userPresenceType": 0, "lastLocation": "Website", "placeId": None,
            "rootPlaceId": None, "gameId": None, "universeId": None, "userId": uid}


def test_presence_get_posts_user_ids_and_unwraps():
    body = {"userPresences": [_presence(1), _presence(261)]}
    client, session, _ = make_client(routes={f"POST {PRESENCE}/v1/presence/users": body})
    out = client.presence.get([1, 261])
    assert out == [_presence(1), _presence(261)] and type(out) is list
    call = session.calls[0]
    assert call.method == "POST" and call.json == {"userIds": [1, 261]}
    assert call.params is None


def test_presence_get_chunks_150_ids_into_two_posts():
    ids = list(range(1, 151))
    client, session, _ = make_client([
        FakeResponse(200, {"userPresences": [_presence(i) for i in ids[:100]]}),
        FakeResponse(200, {"userPresences": [_presence(i) for i in ids[100:]]}),
    ])
    out = client.presence.get(ids)
    assert len(session.calls) == 2
    assert session.calls[0].url == f"{PRESENCE}/v1/presence/users"
    assert session.calls[0].json == {"userIds": ids[:100]}
    assert session.calls[1].json == {"userIds": ids[100:]}
    assert [p["userId"] for p in out] == ids


def test_presence_get_with_no_ids_makes_no_request():
    client, session, _ = make_client(routes={})
    assert client.presence.get([]) == []
    assert session.calls == []


def test_presence_last_online_posts_and_unwraps():
    rows = [{"userId": 1, "lastOnline": "2026-09-01T00:00:00.000Z"},
            {"userId": 261, "lastOnline": "2026-09-27T18:12:05.517Z"}]
    client, session, _ = make_client(routes={
        f"POST {PRESENCE}/v1/presence/last-online": {"lastOnlineTimestamps": rows},
    })
    assert client.presence.last_online([1, 261]) == rows
    call = session.calls[0]
    assert call.method == "POST" and call.json == {"userIds": [1, 261]}


def test_presence_last_online_chunks_150_ids_into_two_posts():
    ids = list(range(1, 151))
    client, session, _ = make_client([
        FakeResponse(200, {"lastOnlineTimestamps": [{"userId": i, "lastOnline": "t"} for i in ids[:100]]}),
        FakeResponse(200, {"lastOnlineTimestamps": [{"userId": i, "lastOnline": "t"} for i in ids[100:]]}),
    ])
    out = client.presence.last_online(ids)
    assert len(session.calls) == 2
    assert session.calls[0].url == f"{PRESENCE}/v1/presence/last-online"
    assert session.calls[0].json == {"userIds": ids[:100]}
    assert session.calls[1].json == {"userIds": ids[100:]}
    assert [r["userId"] for r in out] == ids
