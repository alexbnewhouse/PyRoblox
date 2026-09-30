"""Tests for pyroblox.catalog (economy.roblox.com + catalog.roblox.com).
No network."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from pyroblox.catalog import CatalogAPI
from pyroblox.client import PagedList
from pyroblox.errors import BadRequestError, NotFoundError, PrivateError
from pyroblox.models.catalog import (Bundle, BundleCreator, CatalogItem, EconomyAssetDetails,
                                     EconomyCreator, ResaleData)
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
    "SaleLocation": {"SaleLocationType": 1, "UniverseIds": []},
    "CollectibleItemId": "f9111724-5901-45f6-9b30-4ce57bd919db",
}
# Real shape from POST /v1/catalog/items/details (probe, 2026-09).
CATALOG_ITEM = {
    "bundledItems": [],
    "taxonomy": [{"taxonomyId": "thukPQUFe5EHxRrtsgq43u", "taxonomyName": "Head Accessories"}],
    "itemCreatedUtc": "2007-05-30T07:25:25.51Z",
    "id": 1028606, "itemType": "Asset", "assetType": 8, "name": "Red Baseball Cap",
    "description": "This hat isn't worn out, it's well loved!",
    "productId": 7834684483542479, "itemStatus": [], "itemRestrictions": ["Limited"],
    "creatorHasVerifiedBadge": True, "creatorType": "User", "creatorTargetId": 1,
    "creatorName": "Roblox", "price": 7, "lowestPrice": 1300, "lowestResalePrice": 1300,
    "unitsAvailableForConsumption": 0, "favoriteCount": 50052, "offSaleDeadline": None,
    "collectibleItemId": "f9111724-5901-45f6-9b30-4ce57bd919db", "totalQuantity": 118959,
    "saleLocationType": "ShopOnly", "hasResellers": True, "isOffSale": True,
}
BUNDLE = {"id": 1160, "name": "Heeeeeey...", "bundleType": "DynamicHead",
          "creator": {"id": 1, "name": "Roblox", "type": "User", "hasVerifiedBadge": True}}
BUNDLE_DETAILS = {
    "id": 1160, "name": "Heeeeeey...", "description": "", "bundleType": "DynamicHead",
    "items": [{"id": 10, "name": "Head", "type": "Asset"}],
    "creator": {"id": 1, "name": "Roblox", "type": "User", "hasVerifiedBadge": True},
    "product": {"id": 1, "type": "productType", "isPublicDomain": False,
                "isForSale": False, "priceInRobux": None, "isFree": False,
                "noPriceText": None},
}
RESALE = {"assetStock": 118959, "sales": 118959, "numberRemaining": 0,
          "recentAveragePrice": 1421, "originalPrice": 7,
          "priceDataPoints": [{"value": 1400, "date": "2026-09-27T00:00:00Z"}],
          "volumeDataPoints": [{"value": 3, "date": "2026-09-27T00:00:00Z"}]}


def test_client_exposes_catalog_api():
    client, _, _ = make_client(routes={})
    assert isinstance(client.catalog, CatalogAPI)
    assert client.catalog.client is client
    assert client.assets is client.catalog          # pre-release alias
    assert CatalogAPI.BASE == ECONOMY
    assert CatalogAPI.CATALOG == CATALOG


def test_old_method_names_are_gone():
    import pyroblox.catalog as mod
    assert not hasattr(mod, "AssetsAPI")
    for name in ("details", "catalog_details", "catalog_asset_details", "bundles",
                 "resale", "bundle_details"):
        assert not hasattr(CatalogAPI, name)


# -- models -------------------------------------------------------------------

def test_catalog_item_model_validates_probe_payload():
    item = CatalogItem.model_validate(CATALOG_ITEM)
    assert item.id == 1028606 and item.item_type == "Asset" and item.asset_type == 8
    assert item.name == "Red Baseball Cap"
    assert item.product_id == 7834684483542479
    assert item.creator_type == "User" and item.creator_target_id == 1
    assert item.creator_name == "Roblox"
    assert item.price == 7 and item.lowest_price == 1300 and item.lowest_resale_price == 1300
    assert item.favorite_count == 50052 and item.total_quantity == 118959
    assert item.item_restrictions == ["Limited"]
    assert item.collectible_item_id == "f9111724-5901-45f6-9b30-4ce57bd919db"
    assert item.is_off_sale is True and item.units_available_for_consumption == 0
    # undeclared keys survive as extras, reachable either way
    assert item.model_extra["hasResellers"] is True
    assert item.hasResellers is True
    assert item.model_extra["taxonomy"][0]["taxonomyName"] == "Head Accessories"
    assert item.creator_has_verified_badge is True     # declared field (Roblox's creatorHasVerifiedBadge)
    rec = item.to_record()
    assert rec["creatorTargetId"] == 1 and rec["itemRestrictions"] == ["Limited"]
    assert rec["hasResellers"] is True and rec["saleLocationType"] == "ShopOnly"
    assert "creator_target_id" not in rec and "item_type" not in rec
    for key in CATALOG_ITEM:
        assert rec[key] == CATALOG_ITEM[key]


def test_catalog_item_requires_id():
    with pytest.raises(ValidationError):
        CatalogItem.model_validate({"name": "Red Baseball Cap", "itemType": "Asset"})


def test_bundle_model_validates_probe_payloads():
    short = Bundle.model_validate(BUNDLE)
    assert short.id == 1160 and short.bundle_type == "DynamicHead"
    assert isinstance(short.creator, BundleCreator)
    assert short.creator.id == 1 and short.creator.has_verified_badge is True
    assert short.items is None and short.product is None
    full = Bundle.model_validate(dict(BUNDLE_DETAILS, collectibleItemDetail=None))
    assert full.items == [{"id": 10, "name": "Head", "type": "Asset"}]
    assert full.product["isForSale"] is False
    assert full.model_extra == {"collectibleItemDetail": None}
    rec = full.to_record()
    assert rec["bundleType"] == "DynamicHead" and rec["creator"]["hasVerifiedBadge"] is True
    assert "bundle_type" not in rec
    assert Bundle.model_validate(BUNDLE_DETAILS).to_record() == BUNDLE_DETAILS


def test_bundle_requires_id():
    with pytest.raises(ValidationError):
        Bundle.model_validate({"name": "Heeeeeey...", "bundleType": "DynamicHead"})


def test_economy_asset_details_model_reads_pascal_case_payload():
    details = EconomyAssetDetails.model_validate(DETAILS)
    assert details.asset_id == 1028606 and details.product_id == 2744785375
    assert details.name == "Red Baseball Cap"
    assert details.description == "This hat isn't worn out, it's well loved!"
    assert details.asset_type_id == 8
    assert isinstance(details.creator, EconomyCreator)
    assert details.creator.id == 1 and details.creator.name == "Roblox"
    assert details.creator.creator_type == "User" and details.creator.creator_target_id == 1
    assert details.creator.has_verified_badge is True
    assert details.created == datetime(2007, 5, 30, 7, 25, 25, 510000, tzinfo=timezone.utc)
    assert details.updated == datetime(2016, 11, 16, 20, 10, 1, 413000, tzinfo=timezone.utc)
    assert details.price_in_robux == 7 and details.sales == 0
    assert details.is_for_sale is False and details.is_public_domain is False
    assert details.is_limited is True and details.is_limited_unique is False
    assert details.remaining == 0
    assert details.collectible_item_id == "f9111724-5901-45f6-9b30-4ce57bd919db"
    # undeclared PascalCase keys survive as extras under Roblox's spelling
    assert details.model_extra["ProductType"] == "Collectible Item"
    assert details.ProductType == "Collectible Item"
    assert details.model_extra["SaleLocation"] == {"SaleLocationType": 1, "UniverseIds": []}
    rec = details.to_record()
    assert rec["AssetId"] == 1028606 and rec["PriceInRobux"] == 7
    assert rec["Creator"]["CreatorType"] == "User" and rec["Creator"]["HasVerifiedBadge"] is True
    assert rec["Created"] == "2007-05-30T07:25:25.510000Z"
    assert rec["ProductType"] == "Collectible Item" and rec["TargetId"] == 1028606
    assert "asset_id" not in rec and "assetId" not in rec and "price_in_robux" not in rec


def test_economy_asset_details_accepts_snake_case_construction():
    details = EconomyAssetDetails(asset_id=5, name="x", creator=EconomyCreator(id=1))
    assert details.asset_id == 5 and details.creator.id == 1
    assert details.to_record()["AssetId"] == 5 and details.to_record()["Creator"]["Id"] == 1


def test_economy_asset_details_requires_asset_id():
    with pytest.raises(ValidationError):
        EconomyAssetDetails.model_validate({"Name": "Red Baseball Cap", "ProductId": 1})


def test_resale_data_model_validates_probe_payload():
    resale = ResaleData.model_validate(dict(RESALE, marketCap=1))
    assert resale.asset_stock == 118959 and resale.sales == 118959
    assert resale.number_remaining == 0
    assert resale.recent_average_price == 1421 and resale.original_price == 7
    assert resale.price_data_points == [{"value": 1400, "date": "2026-09-27T00:00:00Z"}]
    assert resale.volume_data_points == [{"value": 3, "date": "2026-09-27T00:00:00Z"}]
    assert resale.model_extra == {"marketCap": 1}
    rec = resale.to_record()
    assert rec["recentAveragePrice"] == 1421 and rec["marketCap"] == 1
    assert "recent_average_price" not in rec
    assert ResaleData.model_validate(RESALE).to_record() == RESALE


def test_resale_data_rejects_non_numeric_price():
    with pytest.raises(ValidationError):
        ResaleData.model_validate({"recentAveragePrice": "lots"})


# -- get_economy_details --------------------------------------------------------

def test_get_economy_details_returns_economy_model():
    client, session, _ = make_client(routes={f"GET {ECONOMY}/v2/assets/1028606/details": DETAILS})
    out = client.catalog.get_economy_details(1028606)
    assert isinstance(out, EconomyAssetDetails)
    assert out.asset_id == 1028606 and out.name == "Red Baseball Cap"
    assert out.creator.creator_type == "User" and out.is_limited is True
    assert out.price_in_robux == 7
    assert session.calls[0].method == "GET" and session.calls[0].params is None
    assert session.calls[0].url == f"{ECONOMY}/v2/assets/1028606/details"


def test_get_economy_details_missing_asset_raises_not_found():
    client, _, _ = make_client([FakeResponse(404)])
    with pytest.raises(NotFoundError):
        client.catalog.get_economy_details(1)


# -- get_item_details -----------------------------------------------------------

def test_get_item_details_posts_items_and_unwraps_data():
    client, session, _ = make_client(routes={
        f"POST {CATALOG}/v1/catalog/items/details": {"data": [CATALOG_ITEM]},
    })
    items = [{"itemType": "Asset", "id": 1028606}]
    out = client.catalog.get_item_details(items)
    assert type(out) is list and len(out) == 1
    assert isinstance(out[0], CatalogItem)
    assert out[0].id == 1028606 and out[0].name == "Red Baseball Cap"
    assert out[0].item_restrictions == ["Limited"] and out[0].creator_target_id == 1
    call = session.calls[0]
    assert call.method == "POST" and call.json == {"items": items} and call.params is None
    assert call.url == f"{CATALOG}/v1/catalog/items/details"


def test_get_item_details_chunks_150_items_into_two_posts():
    items = [{"itemType": "Asset", "id": i} for i in range(1, 151)]
    client, session, _ = make_client([
        FakeResponse(200, {"data": [dict(CATALOG_ITEM, id=i["id"]) for i in items[:100]]}),
        FakeResponse(200, {"data": [dict(CATALOG_ITEM, id=i["id"]) for i in items[100:]]}),
    ])
    out = client.catalog.get_item_details(items)
    assert len(session.calls) == 2
    assert session.calls[0].url == f"{CATALOG}/v1/catalog/items/details"
    assert session.calls[0].json == {"items": items[:100]}
    assert session.calls[1].json == {"items": items[100:]}
    assert [r.id for r in out] == list(range(1, 151))


def test_get_item_details_with_no_items_makes_no_request():
    client, session, _ = make_client(routes={})
    assert client.catalog.get_item_details([]) == []
    assert session.calls == []


def test_get_item_details_learns_csrf_token_from_first_403_unauthenticated():
    client, session, _ = make_client([
        FakeResponse(403, {"errors": [{"code": 0, "message": "XSRF token invalid"}]},
                     headers={"x-csrf-token": "TOK"}),
        FakeResponse(200, {"data": [CATALOG_ITEM]}),
    ])
    out = client.catalog.get_item_details([{"itemType": "Asset", "id": 1028606}])
    assert [i.id for i in out] == [1028606]
    assert len(session.calls) == 2
    assert session.calls[1].headers["X-CSRF-TOKEN"] == "TOK"


def test_get_asset_item_details_wraps_ids_as_asset_items():
    client, session, _ = make_client(routes={
        f"POST {CATALOG}/v1/catalog/items/details":
            {"data": [CATALOG_ITEM, dict(CATALOG_ITEM, id=1474657)]},
    })
    out = client.catalog.get_asset_item_details([1028606, 1474657])
    assert [r.id for r in out] == [1028606, 1474657]
    assert all(isinstance(r, CatalogItem) for r in out)
    assert session.calls[0].json == {"items": [{"itemType": "Asset", "id": 1028606},
                                               {"itemType": "Asset", "id": 1474657}]}


def test_get_asset_item_details_chunks_150_ids_into_two_posts():
    ids = list(range(1, 151))
    client, session, _ = make_client([
        FakeResponse(200, {"data": [{"id": i} for i in ids[:100]]}),
        FakeResponse(200, {"data": [{"id": i} for i in ids[100:]]}),
    ])
    out = client.catalog.get_asset_item_details(ids)
    assert len(session.calls) == 2
    assert session.calls[1].json == {"items": [{"itemType": "Asset", "id": i} for i in ids[100:]]}
    assert [r.id for r in out] == ids


# -- get_asset_bundles ----------------------------------------------------------

def test_get_asset_bundles_paginates_on_catalog_host():
    client, session, _ = make_client(routes={
        f"GET {CATALOG}/v1/assets/1028606/bundles":
            [page([BUNDLE], "c1"), page([dict(BUNDLE, id=1153)], None)],
    })
    out = client.catalog.get_asset_bundles(1028606)
    assert isinstance(out, PagedList)
    assert all(isinstance(b, Bundle) for b in out)
    assert [b.id for b in out] == [1160, 1153] and out.truncated is False
    assert out[0].name == "Heeeeeey..." and out[0].bundle_type == "DynamicHead"
    assert out[0].creator.name == "Roblox" and out[0].creator.has_verified_badge is True
    assert session.calls[0].url == f"{CATALOG}/v1/assets/1028606/bundles"
    assert session.calls[0].params == {"limit": 100, "sortOrder": "Asc"}
    assert session.calls[1].params == {"limit": 100, "sortOrder": "Asc", "cursor": "c1"}


def test_get_asset_bundles_max_items():
    client, session, _ = make_client(routes={
        f"GET {CATALOG}/v1/assets/1028606/bundles": page([BUNDLE, dict(BUNDLE, id=1153)], "c1"),
    })
    out = client.catalog.get_asset_bundles(1028606, max_items=1)
    assert [b.id for b in out] == [1160] and out.truncated is True
    assert len(session.calls) == 1


# -- get_resale_data ------------------------------------------------------------

def test_get_resale_data_returns_model():
    client, session, _ = make_client(routes={f"GET {ECONOMY}/v1/assets/1028606/resale-data": RESALE})
    out = client.catalog.get_resale_data(1028606)
    assert isinstance(out, ResaleData)
    assert out.recent_average_price == 1421 and out.asset_stock == 118959
    assert out.price_data_points == RESALE["priceDataPoints"]
    assert out.to_record() == RESALE
    assert session.calls[0].method == "GET" and session.calls[0].params is None
    assert session.calls[0].url == f"{ECONOMY}/v1/assets/1028606/resale-data"


def test_get_resale_data_non_limited_item_lets_bad_request_propagate():
    body = {"errors": [{"code": 0, "message": "The asset is not a limited item."}]}
    client, _, _ = make_client([FakeResponse(400, body)])
    with pytest.raises(BadRequestError) as exc:
        client.catalog.get_resale_data(1006027)
    assert exc.value.roblox_message == "The asset is not a limited item."


# -- get_bundle -----------------------------------------------------------------

def test_get_bundle_returns_model():
    client, session, _ = make_client(routes={f"GET {CATALOG}/v1/bundles/1160/details": BUNDLE_DETAILS})
    out = client.catalog.get_bundle(1160)
    assert isinstance(out, Bundle)
    assert out.id == 1160 and out.name == "Heeeeeey..." and out.bundle_type == "DynamicHead"
    assert out.items == [{"id": 10, "name": "Head", "type": "Asset"}]
    assert out.creator.id == 1 and out.creator.type == "User"
    assert out.product["isFree"] is False
    assert out.to_record() == BUNDLE_DETAILS
    assert session.calls[0].method == "GET" and session.calls[0].params is None
    assert session.calls[0].url == f"{CATALOG}/v1/bundles/1160/details"


def test_get_bundle_private_lets_private_error_propagate():
    client, _, _ = make_client([FakeResponse(403)])
    with pytest.raises(PrivateError):
        client.catalog.get_bundle(1160)
