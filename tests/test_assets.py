"""Tests for robloxwrapper.assets (economy.roblox.com + catalog.roblox.com).
No network."""

import pytest

from robloxwrapper.assets import AssetsAPI
from robloxwrapper.client import PagedList
from robloxwrapper.errors import BadRequestError, NotFoundError, PrivateError
from tests.conftest import FakeResponse, make_client, page

ECONOMY = "https://economy.roblox.com"
CATALOG = "https://catalog.roblox.com"

# Real shape from GET /v2/assets/1028606/details (probe, 2026-09), trimmed.
DETAILS = {
    "TargetId": 1028606, "ProductType": "Collectible Item", "AssetId": 1028606,
    "ProductId": 2744785375, "Name": "Red Baseball Cap",
    "Description": "This hat isn't worn out, it's well loved!",
    "AssetTypeId": 8,
    "Creator": {"Id": 1, "Name": "Roblox", "CreatorType": "User", "CreatorTargetId": 1,
                "HasVerifiedBadge": True},
    "IconImageAssetId": 0, "Created": "2007-05-30T07:25:25.51Z",
    "Updated": "2016-11-16T20:10:01.413Z", "PriceInRobux": 7, "PriceInTickets": None,
    "Sales": 0, "IsNew": False, "IsForSale": False, "IsPublicDomain": False,
    "IsLimited": True, "IsLimitedUnique": False, "Remaining": 0,
    "MinimumMembershipLevel": 0, "ContentRatingTypeId": 0,
    "CollectibleItemId": "f9111724-5901-45f6-9b30-4ce57bd919db",
}
CATALOG_ITEM = {
    "bundledItems": [], "itemCreatedUtc": "2007-05-30T07:25:25.51Z",
    "id": 1028606, "itemType": "Asset", "assetType": 8, "name": "Red Baseball Cap",
    "productId": 7834684483542479, "itemRestrictions": ["Limited"],
    "creatorHasVerifiedBadge": True, "creatorType": "User", "creatorTargetId": 1,
    "creatorName": "Roblox", "price": 7, "lowestPrice": 1300, "lowestResalePrice": 1300,
    "favoriteCount": 50052, "totalQuantity": 118959, "hasResellers": True, "isOffSale": True,
}
BUNDLE = {"id": 1160, "name": "Heeeeeey...", "bundleType": "DynamicHead",
          "creator": {"id": 1, "name": "Roblox", "type": "User", "hasVerifiedBadge": True}}


def test_client_exposes_assets_api():
    client, _, _ = make_client(routes={})
    assert isinstance(client.assets, AssetsAPI)
    assert client.assets.client is client
    assert AssetsAPI.BASE == ECONOMY


# -- details ------------------------------------------------------------------

def test_details_returns_economy_object():
    client, session, _ = make_client(routes={f"GET {ECONOMY}/v2/assets/1028606/details": DETAILS})
    assert client.assets.details(1028606) == DETAILS
    assert session.calls[0].method == "GET" and session.calls[0].params is None


def test_details_missing_asset_raises_not_found():
    client, _, _ = make_client([FakeResponse(404)])
    with pytest.raises(NotFoundError):
        client.assets.details(1)


# -- catalog_details ----------------------------------------------------------

def test_catalog_details_posts_items_and_unwraps_data():
    client, session, _ = make_client(routes={
        f"POST {CATALOG}/v1/catalog/items/details": {"data": [CATALOG_ITEM]},
    })
    items = [{"itemType": "Asset", "id": 1028606}]
    out = client.assets.catalog_details(items)
    assert out == [CATALOG_ITEM] and type(out) is list
    call = session.calls[0]
    assert call.method == "POST" and call.json == {"items": items} and call.params is None


def test_catalog_details_chunks_150_items_into_two_posts():
    items = [{"itemType": "Asset", "id": i} for i in range(1, 151)]
    client, session, _ = make_client([
        FakeResponse(200, {"data": [dict(CATALOG_ITEM, id=i["id"]) for i in items[:100]]}),
        FakeResponse(200, {"data": [dict(CATALOG_ITEM, id=i["id"]) for i in items[100:]]}),
    ])
    out = client.assets.catalog_details(items)
    assert len(session.calls) == 2
    assert session.calls[0].url == f"{CATALOG}/v1/catalog/items/details"
    assert session.calls[0].json == {"items": items[:100]}
    assert session.calls[1].json == {"items": items[100:]}
    assert [r["id"] for r in out] == list(range(1, 151))


def test_catalog_details_with_no_items_makes_no_request():
    client, session, _ = make_client(routes={})
    assert client.assets.catalog_details([]) == []
    assert session.calls == []


def test_catalog_details_learns_csrf_token_from_first_403_unauthenticated():
    client, session, _ = make_client([
        FakeResponse(403, {"errors": [{"code": 0, "message": "XSRF token invalid"}]},
                     headers={"x-csrf-token": "TOK"}),
        FakeResponse(200, {"data": [CATALOG_ITEM]}),
    ])
    assert client.assets.catalog_details([{"itemType": "Asset", "id": 1028606}]) == [CATALOG_ITEM]
    assert len(session.calls) == 2
    assert session.calls[1].headers["X-CSRF-TOKEN"] == "TOK"


def test_catalog_asset_details_wraps_ids_as_asset_items():
    client, session, _ = make_client(routes={
        f"POST {CATALOG}/v1/catalog/items/details":
            {"data": [CATALOG_ITEM, dict(CATALOG_ITEM, id=1474657)]},
    })
    out = client.assets.catalog_asset_details([1028606, 1474657])
    assert [r["id"] for r in out] == [1028606, 1474657]
    assert session.calls[0].json == {"items": [{"itemType": "Asset", "id": 1028606},
                                               {"itemType": "Asset", "id": 1474657}]}


def test_catalog_asset_details_chunks_150_ids_into_two_posts():
    ids = list(range(1, 151))
    client, session, _ = make_client([
        FakeResponse(200, {"data": [{"id": i} for i in ids[:100]]}),
        FakeResponse(200, {"data": [{"id": i} for i in ids[100:]]}),
    ])
    out = client.assets.catalog_asset_details(ids)
    assert len(session.calls) == 2
    assert session.calls[1].json == {"items": [{"itemType": "Asset", "id": i} for i in ids[100:]]}
    assert [r["id"] for r in out] == ids


# -- bundles ------------------------------------------------------------------

def test_bundles_paginates_on_catalog_host():
    client, session, _ = make_client(routes={
        f"GET {CATALOG}/v1/assets/1028606/bundles":
            [page([BUNDLE], "c1"), page([dict(BUNDLE, id=1153)], None)],
    })
    out = client.assets.bundles(1028606)
    assert isinstance(out, PagedList)
    assert [b["id"] for b in out] == [1160, 1153] and out.truncated is False
    assert session.calls[0].params == {"limit": 100, "sortOrder": "Asc"}
    assert session.calls[1].params == {"limit": 100, "sortOrder": "Asc", "cursor": "c1"}


def test_bundles_max_items():
    client, session, _ = make_client(routes={
        f"GET {CATALOG}/v1/assets/1028606/bundles": page([BUNDLE, dict(BUNDLE, id=1153)], "c1"),
    })
    out = client.assets.bundles(1028606, max_items=1)
    assert out == [BUNDLE] and out.truncated is True
    assert len(session.calls) == 1


# -- resale -------------------------------------------------------------------

def test_resale_returns_object():
    body = {"assetStock": 118959, "sales": 118959, "numberRemaining": 0,
            "recentAveragePrice": 1421, "originalPrice": 7,
            "priceDataPoints": [{"value": 1400, "date": "2026-09-27T00:00:00Z"}],
            "volumeDataPoints": [{"value": 3, "date": "2026-09-27T00:00:00Z"}]}
    client, session, _ = make_client(routes={f"GET {ECONOMY}/v1/assets/1028606/resale-data": body})
    assert client.assets.resale(1028606) == body
    assert session.calls[0].method == "GET" and session.calls[0].params is None


def test_resale_non_limited_item_lets_bad_request_propagate():
    body = {"errors": [{"code": 0, "message": "The asset is not a limited item."}]}
    client, _, _ = make_client([FakeResponse(400, body)])
    with pytest.raises(BadRequestError) as exc:
        client.assets.resale(1006027)
    assert exc.value.roblox_message == "The asset is not a limited item."


# -- bundle_details -----------------------------------------------------------

def test_bundle_details_returns_object():
    body = {"id": 1160, "name": "Heeeeeey...", "description": "", "bundleType": "DynamicHead",
            "items": [{"id": 10, "name": "Head", "type": "Asset"}],
            "creator": {"id": 1, "name": "Roblox", "type": "User", "hasVerifiedBadge": True},
            "product": {"id": 1, "type": "productType", "isPublicDomain": False,
                        "isForSale": False, "priceInRobux": None, "isFree": False,
                        "noPriceText": None}}
    client, session, _ = make_client(routes={f"GET {CATALOG}/v1/bundles/1160/details": body})
    assert client.assets.bundle_details(1160) == body
    assert session.calls[0].method == "GET" and session.calls[0].params is None


def test_bundle_details_private_lets_private_error_propagate():
    client, _, _ = make_client([FakeResponse(403)])
    with pytest.raises(PrivateError):
        client.assets.bundle_details(1160)
