"""Tests for pyroblox.avatar: AvatarAPI, InventoryAPI, AccountAPI,
PresenceAPI and the ASSET_TYPES table. No network."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from pyroblox.avatar import (
    ASSET_TYPES, AccountAPI, AvatarAPI, InventoryAPI, PresenceAPI,
)
from pyroblox.client import PagedList
from pyroblox.errors import PrivateError
from pyroblox.models.account import PromotionChannels, RobloxBadge
from pyroblox.models.avatar import (
    Avatar, AvatarAsset, AvatarAssetType, AvatarScales, BodyColors, Outfit,
)
from pyroblox.models.catalog import CatalogItem
from pyroblox.models.inventory import (
    AssetOwner, Bundle, BundleCreator, CollectibleAsset, InventoryItem, InventoryOwner,
)
from pyroblox.models.presence import LastOnline, UserPresence
from tests.conftest import FakeResponse, make_client, page

AVATAR = "https://avatar.roblox.com"
INVENTORY = "https://inventory.roblox.com"
CATALOG = "https://catalog.roblox.com"
ACCOUNT = "https://accountinformation.roblox.com"
PRESENCE = "https://presence.roblox.com"

LAST_SEEN = "2026-09-27T18:12:05.517Z"
LAST_SEEN_DT = datetime(2026, 9, 27, 18, 12, 5, 517000, tzinfo=timezone.utc)


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


def test_avatar_get_avatar_returns_model():
    client, session, _ = make_client(routes={f"GET {AVATAR}/v1/users/261/avatar": AVATAR_BODY})
    out = client.avatar.get_avatar(261)
    assert isinstance(out, Avatar)
    assert out.player_avatar_type == "R6"
    assert out.body_colors.torso_color_id == 1003
    assert out.scales.body_type == 0.0
    assert [a.id for a in out.assets] == [1006027, 1028859]
    assert out.assets[0].asset_type.name == "TShirt"
    assert session.calls[0].method == "GET" and session.calls[0].params is None


def test_avatar_currently_wearing_unwraps_asset_ids():
    ids = [1006027, 1028859, 76691628978545, 93075310246069, 111989654515290]
    client, session, _ = make_client(routes={
        f"GET {AVATAR}/v1/users/261/currently-wearing": {"assetIds": ids},
    })
    assert client.avatar.get_currently_wearing(261) == ids
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
    out = client.avatar.get_outfits(261)
    assert type(out) is list and all(isinstance(o, Outfit) for o in out)
    assert [o.id for o in out] == list(range(1, 61))
    assert out[0].name == "Outfit 1" and out[0].is_editable is True
    assert out[0].outfit_type == "Avatar"
    assert len(session.calls) == 2
    assert session.calls[0].params == {"page": 1, "itemsPerPage": 50, "isEditable": "true"}
    assert session.calls[1].params == {"page": 2, "itemsPerPage": 50, "isEditable": "true"}


def test_avatar_outfits_single_page_when_total_covered():
    items = [_outfit(1), _outfit(2)]
    client, session, _ = make_client(routes={
        f"GET {AVATAR}/v1/users/261/outfits": _outfits_page(items, 2),
    })
    assert [o.id for o in client.avatar.get_outfits(261)] == [1, 2]
    assert len(session.calls) == 1


def test_avatar_outfits_stops_on_empty_page():
    # ``total`` over-reports; the empty second page must end the loop.
    client, session, _ = make_client(routes={
        f"GET {AVATAR}/v1/users/261/outfits?page=1&itemsPerPage=50&isEditable=true":
            _outfits_page([_outfit(1)], 5),
        f"GET {AVATAR}/v1/users/261/outfits?page=2&itemsPerPage=50&isEditable=true":
            _outfits_page([], 5),
    })
    assert [o.id for o in client.avatar.get_outfits(261)] == [1]
    assert len(session.calls) == 2


def test_avatar_outfits_stops_when_total_missing_and_page_empty():
    client, session, _ = make_client(routes={
        f"GET {AVATAR}/v1/users/261/outfits?page=1&itemsPerPage=50&isEditable=true":
            {"data": [_outfit(1)]},
        f"GET {AVATAR}/v1/users/261/outfits?page=2&itemsPerPage=50&isEditable=true":
            {"data": []},
    })
    assert [o.id for o in client.avatar.get_outfits(261)] == [1]
    assert len(session.calls) == 2


def test_avatar_outfits_honours_max_items():
    client, session, _ = make_client(routes={
        f"GET {AVATAR}/v1/users/261/outfits": _outfits_page([_outfit(i) for i in range(1, 4)], 100),
    })
    out = client.avatar.get_outfits(261, max_items=2)
    assert [o.id for o in out] == [1, 2]
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
    out = client.inventory.get_collectibles(261)
    assert isinstance(out, PagedList) and all(isinstance(r, CollectibleAsset) for r in out)
    assert [r.user_asset_id for r in out] == [115160, 2] and out.truncated is False
    assert out[0].name == "Traffic Cone" and out[0].recent_average_price == 3411
    assert session.calls[0].params == {"limit": 100, "sortOrder": "Asc"}
    assert session.calls[1].params == {"limit": 100, "sortOrder": "Asc", "cursor": "c1"}


def test_inventory_collectibles_max_items():
    client, session, _ = make_client(routes={
        f"GET {INVENTORY}/v1/users/261/assets/collectibles":
            page([COLLECTIBLE, dict(COLLECTIBLE, userAssetId=2)], "c1"),
    })
    out = client.inventory.get_collectibles(261, max_items=1)
    assert [r.user_asset_id for r in out] == [115160] and out.truncated is True
    assert len(session.calls) == 1


def test_inventory_user_inventory_paginates_by_asset_type():
    client, session, _ = make_client(routes={
        f"GET {INVENTORY}/v2/users/261/inventory/8": page([INVENTORY_ITEM], None),
    })
    out = client.inventory.get_user_inventory(261, 8)
    assert isinstance(out, PagedList) and len(out) == 1
    assert isinstance(out[0], InventoryItem)
    assert out[0].user_asset_id == 29545 and out[0].asset_name == "Pirate Captain's Hat"
    assert out[0].owner.user_id == 261 and out[0].owner.username == "Shedletsky"
    assert out[0].created == datetime(2007, 5, 30, 22, 8, 18, 697000, tzinfo=timezone.utc)
    assert session.calls[0].params == {"limit": 100, "sortOrder": "Asc"}


def test_inventory_user_inventory_max_items():
    client, session, _ = make_client(routes={
        f"GET {INVENTORY}/v2/users/261/inventory/8":
            page([INVENTORY_ITEM, dict(INVENTORY_ITEM, userAssetId=2)], "c1"),
    })
    out = client.inventory.get_user_inventory(261, ASSET_TYPES["hat"], max_items=1)
    assert [r.user_asset_id for r in out] == [29545] and out.truncated is True


def test_inventory_get_items_is_alias_of_get_user_inventory():
    assert InventoryAPI.get_items is InventoryAPI.get_user_inventory
    client, session, _ = make_client(routes={
        f"GET {INVENTORY}/v2/users/261/inventory/8": page([INVENTORY_ITEM], None),
    })
    out = client.inventory.get_items(261, 8)
    assert [r.user_asset_id for r in out] == [29545]
    assert session.calls[0].url == f"{INVENTORY}/v2/users/261/inventory/8"


def test_inventory_user_inventory_private_inventory_raises_private_error():
    client, _, _ = make_client([FakeResponse(403)])
    with pytest.raises(PrivateError):
        client.inventory.get_user_inventory(261, 8)


def test_inventory_asset_owners_paginates():
    client, session, _ = make_client(routes={
        f"GET {INVENTORY}/v2/assets/1028606/owners":
            [page([OWNER_ROW], "c1"), page([dict(OWNER_ROW, id=28606)], None)],
    })
    out = client.inventory.get_asset_owners(1028606)
    assert isinstance(out, PagedList) and all(isinstance(r, AssetOwner) for r in out)
    assert [r.id for r in out] == [28605, 28606]
    assert out[0].owner is None and out[0].serial_number == 0
    assert out[0].collectible_item_instance_id == "fe0f7b73-91be-4050-a1b7-233f884eec33"
    assert session.calls[0].params == {"limit": 100, "sortOrder": "Asc"}
    assert session.calls[1].params == {"limit": 100, "sortOrder": "Asc", "cursor": "c1"}


def test_inventory_asset_owners_max_items():
    client, session, _ = make_client(routes={
        f"GET {INVENTORY}/v2/assets/1028606/owners":
            page([OWNER_ROW, dict(OWNER_ROW, id=28606)], "c1"),
    })
    out = client.inventory.get_asset_owners(1028606, max_items=1)
    assert [r.id for r in out] == [28605] and out.truncated is True


def test_inventory_favorite_assets_uses_catalog_host_without_sort_order():
    client, session, _ = make_client(routes={
        f"GET {CATALOG}/v1/favorites/users/261/favorites/8/assets": page([FAVORITE], None),
    })
    out = client.inventory.get_favorite_assets(261, 8)
    assert isinstance(out, PagedList) and len(out) == 1
    assert isinstance(out[0], CatalogItem)
    assert out[0].id == 1474657 and out[0].name == "The Dusekkar"
    assert out[0].asset_type == 8 and out[0].favorite_count == 33193
    assert out[0].is_off_sale is True and out[0].creator_target_id == 1
    assert session.calls[0].params == {"limit": 100}


def test_inventory_favorite_assets_max_items():
    client, session, _ = make_client(routes={
        f"GET {CATALOG}/v1/favorites/users/261/favorites/8/assets":
            page([FAVORITE, dict(FAVORITE, id=2)], "c1"),
    })
    out = client.inventory.get_favorite_assets(261, 8, max_items=1)
    assert [i.id for i in out] == [1474657] and out.truncated is True


def test_inventory_bundles_paginates_on_catalog_host():
    client, session, _ = make_client(routes={
        f"GET {CATALOG}/v1/users/261/bundles":
            [page([BUNDLE], "c1"), page([dict(BUNDLE, id=1153)], None)],
    })
    out = client.inventory.get_bundles(261)
    assert isinstance(out, PagedList) and all(isinstance(b, Bundle) for b in out)
    assert [b.id for b in out] == [1160, 1153]
    assert out[0].name == "Heeeeeey..." and out[0].bundle_type == "DynamicHead"
    assert isinstance(out[0].creator, BundleCreator)
    assert out[0].creator.has_verified_badge is True
    assert session.calls[0].params == {"limit": 100, "sortOrder": "Asc"}
    assert session.calls[1].params == {"limit": 100, "sortOrder": "Asc", "cursor": "c1"}


def test_inventory_bundles_max_items():
    client, session, _ = make_client(routes={
        f"GET {CATALOG}/v1/users/261/bundles": page([BUNDLE, dict(BUNDLE, id=1153)], "c1"),
    })
    out = client.inventory.get_bundles(261, max_items=1)
    assert [b.id for b in out] == [1160] and out.truncated is True


# -- AccountAPI ---------------------------------------------------------------

ROBLOX_BADGES = [
    {"id": 2, "name": "Friendship", "description": "This badge was given to members ...",
     "imageUrl": "https://images.rbxcdn.com/5eb20917cf530583e2641c0e1f7ba95e.png"},
    {"id": 3, "name": "Combat Initiation", "description": "This badge was granted ...",
     "imageUrl": "https://images.rbxcdn.com/8d77254fc1e6d904fd3ded29dfca28cb.png"},
]


def test_account_roblox_badges_returns_list_of_models():
    # a list-valued route means "responses in turn" to FakeSession, so wrap it
    client, session, _ = make_client(routes={
        f"GET {ACCOUNT}/v1/users/261/roblox-badges": FakeResponse(200, ROBLOX_BADGES),
    })
    out = client.account.get_roblox_badges(261)
    assert type(out) is list and all(isinstance(b, RobloxBadge) for b in out)
    assert [b.id for b in out] == [2, 3]
    assert out[0].name == "Friendship"
    assert out[1].image_url == "https://images.rbxcdn.com/8d77254fc1e6d904fd3ded29dfca28cb.png"
    assert session.calls[0].method == "GET" and session.calls[0].params is None


def test_account_promotion_channels_returns_model():
    body = {"facebook": None, "twitter": None, "youtube": None, "twitch": None}
    client, session, _ = make_client(routes={
        f"GET {ACCOUNT}/v1/users/261/promotion-channels": body,
    })
    out = client.account.get_promotion_channels(261)
    assert isinstance(out, PromotionChannels)
    assert out.facebook is None and out.twitter is None and out.youtube is None
    assert out.twitch is None and out.guilded is None
    assert session.calls[0].params is None


def test_account_promotion_channels_exposes_values_when_present():
    body = {"facebook": None, "twitter": "@shedletsky",
            "youtube": "https://www.youtube.com/@shedletsky", "twitch": None, "guilded": "shed"}
    client, _, _ = make_client(routes={
        f"GET {ACCOUNT}/v1/users/261/promotion-channels": body,
    }, cookie="cookie")
    out = client.account.get_promotion_channels(261)
    assert out.twitter == "@shedletsky" and out.guilded == "shed"
    assert out.youtube == "https://www.youtube.com/@shedletsky"


# -- PresenceAPI --------------------------------------------------------------

def _presence(uid):
    return {"userPresenceType": 0, "lastLocation": "Website", "placeId": None,
            "rootPlaceId": None, "gameId": None, "universeId": None, "userId": uid}


def test_presence_get_presence_posts_user_ids_and_unwraps():
    body = {"userPresences": [_presence(1), _presence(261)]}
    client, session, _ = make_client(routes={f"POST {PRESENCE}/v1/presence/users": body})
    out = client.presence.get_presence([1, 261])
    assert type(out) is list and all(isinstance(p, UserPresence) for p in out)
    assert [p.user_id for p in out] == [1, 261]
    assert out[0].user_presence_type == 0 and out[0].last_location == "Website"
    assert out[0].place_id is None and out[0].universe_id is None
    call = session.calls[0]
    assert call.method == "POST" and call.json == {"userIds": [1, 261]}
    assert call.params is None


def test_presence_get_presence_chunks_150_ids_into_two_posts():
    ids = list(range(1, 151))
    client, session, _ = make_client([
        FakeResponse(200, {"userPresences": [_presence(i) for i in ids[:100]]}),
        FakeResponse(200, {"userPresences": [_presence(i) for i in ids[100:]]}),
    ])
    out = client.presence.get_presence(ids)
    assert len(session.calls) == 2
    assert session.calls[0].url == f"{PRESENCE}/v1/presence/users"
    assert session.calls[0].json == {"userIds": ids[:100]}
    assert session.calls[1].json == {"userIds": ids[100:]}
    assert [p.user_id for p in out] == ids


def test_presence_get_presence_with_no_ids_makes_no_request():
    client, session, _ = make_client(routes={})
    assert client.presence.get_presence([]) == []
    assert session.calls == []


def test_presence_last_online_posts_and_unwraps():
    rows = [{"userId": 1, "lastOnline": "2026-09-01T00:00:00.000Z"},
            {"userId": 261, "lastOnline": LAST_SEEN}]
    client, session, _ = make_client(routes={
        f"POST {PRESENCE}/v1/presence/last-online": {"lastOnlineTimestamps": rows},
    })
    out = client.presence.get_last_online([1, 261])
    assert type(out) is list and all(isinstance(r, LastOnline) for r in out)
    assert [r.user_id for r in out] == [1, 261]
    assert out[0].last_online == datetime(2026, 9, 1, tzinfo=timezone.utc)
    assert out[1].last_online == LAST_SEEN_DT
    call = session.calls[0]
    assert call.method == "POST" and call.json == {"userIds": [1, 261]}


def test_presence_last_online_chunks_150_ids_into_two_posts():
    ids = list(range(1, 151))
    client, session, _ = make_client([
        FakeResponse(200, {"lastOnlineTimestamps": [{"userId": i, "lastOnline": LAST_SEEN} for i in ids[:100]]}),
        FakeResponse(200, {"lastOnlineTimestamps": [{"userId": i, "lastOnline": LAST_SEEN} for i in ids[100:]]}),
    ])
    out = client.presence.get_last_online(ids)
    assert len(session.calls) == 2
    assert session.calls[0].url == f"{PRESENCE}/v1/presence/last-online"
    assert session.calls[0].json == {"userIds": ids[:100]}
    assert session.calls[1].json == {"userIds": ids[100:]}
    assert [r.user_id for r in out] == ids


# -- models -------------------------------------------------------------------

# (Model, realistic camelCase payload, snake_case attribute, expected value,
#  a camelCase key whose value survives to_record() unchanged)
MODEL_CASES = [
    pytest.param(AvatarAssetType, {"id": 2, "name": "TShirt"},
                 "name", "TShirt", "id", id="AvatarAssetType"),
    pytest.param(AvatarAsset, AVATAR_BODY["assets"][1],
                 "current_version_id", 883359752, "currentVersionId", id="AvatarAsset"),
    pytest.param(BodyColors, AVATAR_BODY["bodyColors"],
                 "torso_color_id", 1003, "rightLegColorId", id="BodyColors"),
    pytest.param(AvatarScales, AVATAR_BODY["scales"],
                 "body_type", 0.0, "bodyType", id="AvatarScales"),
    pytest.param(Avatar, AVATAR_BODY,
                 "player_avatar_type", "R6", "playerAvatarType", id="Avatar"),
    pytest.param(Outfit, _outfit(7),
                 "is_editable", True, "outfitType", id="Outfit"),
    pytest.param(CollectibleAsset, COLLECTIBLE,
                 "recent_average_price", 3411, "recentAveragePrice", id="CollectibleAsset"),
    pytest.param(InventoryOwner, INVENTORY_ITEM["owner"],
                 "user_id", 261, "username", id="InventoryOwner"),
    pytest.param(InventoryItem, INVENTORY_ITEM,
                 "asset_name", "Pirate Captain's Hat", "assetName", id="InventoryItem"),
    pytest.param(AssetOwner, OWNER_ROW,
                 "collectible_item_instance_id", OWNER_ROW["collectibleItemInstanceId"],
                 "serialNumber", id="AssetOwner"),
    pytest.param(BundleCreator, BUNDLE["creator"],
                 "has_verified_badge", True, "hasVerifiedBadge", id="BundleCreator"),
    pytest.param(Bundle, BUNDLE,
                 "bundle_type", "DynamicHead", "bundleType", id="Bundle"),
    pytest.param(RobloxBadge, ROBLOX_BADGES[0],
                 "image_url", ROBLOX_BADGES[0]["imageUrl"], "imageUrl", id="RobloxBadge"),
    pytest.param(PromotionChannels,
                 {"facebook": None, "twitter": "@x", "youtube": None, "twitch": None},
                 "twitter", "@x", "twitter", id="PromotionChannels"),
    pytest.param(UserPresence, _presence(261),
                 "user_presence_type", 0, "userPresenceType", id="UserPresence"),
    pytest.param(LastOnline, {"userId": 261, "lastOnline": LAST_SEEN},
                 "user_id", 261, "userId", id="LastOnline"),
]


@pytest.mark.parametrize("model, payload, attr, expected, camel_key", MODEL_CASES)
def test_model_validates_realistic_payload(model, payload, attr, expected, camel_key):
    obj = model.model_validate(dict(payload, zzzNewField="kept"))
    assert getattr(obj, attr) == expected
    assert obj.model_extra["zzzNewField"] == "kept"
    assert obj.zzzNewField == "kept"
    rec = obj.to_record()
    assert set(payload) <= set(rec)
    assert rec[camel_key] == payload[camel_key]
    assert rec["zzzNewField"] == "kept"


def test_avatar_model_nests_colors_scales_and_assets():
    avatar = Avatar.model_validate(AVATAR_BODY)
    assert isinstance(avatar.body_colors, BodyColors)
    assert avatar.body_colors.left_leg_color_id == 23
    assert isinstance(avatar.scales, AvatarScales) and avatar.scales.height == 1.0
    assert [a.id for a in avatar.assets] == [1006027, 1028859]
    assert all(isinstance(a, AvatarAsset) for a in avatar.assets)
    assert isinstance(avatar.assets[0].asset_type, AvatarAssetType)
    assert avatar.assets[0].asset_type.name == "TShirt"
    assert avatar.default_shirt_applied is None and avatar.emotes is None
    assert Avatar.model_validate({}).assets == []
    rec = avatar.to_record()
    assert rec["bodyColors"] == AVATAR_BODY["bodyColors"]
    assert rec["scales"] == AVATAR_BODY["scales"]
    assert rec["assets"][0]["assetType"] == {"id": 2, "name": "TShirt"}


def test_inventory_item_parses_owner_and_timestamps():
    item = InventoryItem.model_validate(INVENTORY_ITEM)
    assert isinstance(item.owner, InventoryOwner) and item.owner.user_id == 261
    assert item.owner.display_name is None
    assert item.owner.model_extra == {"buildersClubMembershipType": "None"}
    assert item.created == datetime(2007, 5, 30, 22, 8, 18, 697000, tzinfo=timezone.utc)
    assert item.collectible_item_id is None and item.serial_number is None
    rec = item.to_record()
    assert rec["created"].startswith("2007-05-30T22:08:18")
    assert rec["owner"]["userId"] == 261


def test_asset_owner_with_null_owner():
    row = AssetOwner.model_validate(OWNER_ROW)
    assert row.owner is None and row.serial_number == 0
    assert row.created == datetime(2007, 5, 30, 7, 25, 25, 527000, tzinfo=timezone.utc)
    assert row.to_record()["owner"] is None


def test_bundle_nests_creator():
    bundle = Bundle.model_validate(BUNDLE)
    assert isinstance(bundle.creator, BundleCreator)
    assert bundle.creator.id == 1 and bundle.creator.type == "User"
    assert bundle.description is None and bundle.items is None
    assert bundle.to_record()["creator"] == BUNDLE["creator"]
    assert BundleCreator.model_validate({"id": 1}).has_verified_badge is False


def test_promotion_channels_defaults_guilded_when_roblox_omits_it():
    channels = PromotionChannels.model_validate(
        {"facebook": None, "twitter": None, "youtube": None, "twitch": None})
    assert channels.guilded is None
    # to_record() only emits keys Roblox actually sent, so the unset default stays out
    assert set(channels.to_record()) == {"facebook", "twitter", "youtube", "twitch"}
    assert channels.model_dump(by_alias=True)["guilded"] is None


def test_user_presence_in_game_shape():
    body = {"userPresenceType": 2, "lastLocation": "Blox Fruits", "placeId": 2753915549,
            "rootPlaceId": 2753915549, "gameId": "6f7a0f5e-1c3b-4a2e-9a0e-0b9a5b6c7d8e",
            "universeId": 994732206, "userId": 261, "lastOnline": LAST_SEEN}
    presence = UserPresence.model_validate(body)
    assert presence.user_presence_type == 2 and presence.place_id == 2753915549
    assert presence.game_id == "6f7a0f5e-1c3b-4a2e-9a0e-0b9a5b6c7d8e"
    assert presence.universe_id == 994732206 and presence.last_online == LAST_SEEN_DT
    assert presence.to_record()["lastOnline"].startswith("2026-09-27T18:12:05")


def test_last_online_parses_timestamp():
    row = LastOnline.model_validate({"userId": 261, "lastOnline": LAST_SEEN})
    assert row.user_id == 261 and row.last_online == LAST_SEEN_DT
    assert row.to_record()["lastOnline"].startswith("2026-09-27T18:12:05")
    assert LastOnline.model_validate({"userId": 1}).last_online is None


@pytest.mark.parametrize("model, payload", [
    pytest.param(AvatarAssetType, {"name": "Hat"}, id="AvatarAssetType-no-id"),
    pytest.param(AvatarAsset, {"name": "x"}, id="AvatarAsset-no-id"),
    pytest.param(Avatar, {"assets": [{"name": "no id"}]}, id="Avatar-nested-asset-no-id"),
    pytest.param(Outfit, {"name": "x"}, id="Outfit-no-id"),
    pytest.param(Outfit, {"id": "not-a-number"}, id="Outfit-id-not-int"),
    pytest.param(CollectibleAsset, {"assetId": 1}, id="CollectibleAsset-no-userAssetId"),
    pytest.param(InventoryItem, {"assetId": 1}, id="InventoryItem-no-userAssetId"),
    pytest.param(AssetOwner, {"serialNumber": 1}, id="AssetOwner-no-id"),
    pytest.param(BundleCreator, {"name": "Roblox"}, id="BundleCreator-no-id"),
    pytest.param(Bundle, {"name": "x"}, id="Bundle-no-id"),
    pytest.param(RobloxBadge, {"id": 2}, id="RobloxBadge-no-name"),
    pytest.param(UserPresence, {"userPresenceType": 0}, id="UserPresence-no-userId"),
    pytest.param(LastOnline, {"lastOnline": LAST_SEEN}, id="LastOnline-no-userId"),
])
def test_missing_or_invalid_required_field_raises_validation_error(model, payload):
    with pytest.raises(ValidationError):
        model.model_validate(payload)
