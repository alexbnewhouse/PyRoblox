"""Tests for CatalogAPI resource methods."""

from pytest_httpx import HTTPXMock

from pyroblox.client import RobloxClient


def test_catalog_search(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "data": [
            {"id": 1, "name": "Cool Hat", "price": 100, "itemType": "Asset"},
            {"id": 2, "name": "Nice Hat", "price": 200, "itemType": "Asset"},
        ],
        "nextPageCursor": None,
    })
    with RobloxClient() as client:
        items = list(client.catalog.search(keyword="hat", max_pages=1))
        assert len(items) == 2
        assert items[0].name == "Cool Hat"
        assert items[0].price == 100


def test_get_item_details(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "data": [
            {"id": 1, "name": "Asset1", "itemType": "Asset", "price": 50},
        ],
    })
    with RobloxClient() as client:
        details = client.catalog.get_item_details([{"itemType": "Asset", "id": 1}])
        assert len(details) == 1
        assert details[0].name == "Asset1"


def test_get_bundle(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "id": 500,
        "name": "Starter Pack",
        "description": "A starter bundle",
        "bundleType": "BodyParts",
        "items": [{"id": 1, "name": "Hat", "type": "Asset"}],
    })
    with RobloxClient() as client:
        bundle = client.catalog.get_bundle(500)
        assert bundle.id == 500
        assert bundle.name == "Starter Pack"
        assert bundle.items is not None
        assert len(bundle.items) == 1


def test_get_bundles_batch(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json=[
        {"id": 1, "name": "Bundle1"},
        {"id": 2, "name": "Bundle2"},
    ])
    with RobloxClient() as client:
        bundles = client.catalog.get_bundles([1, 2])
        assert len(bundles) == 2


def test_get_asset_favorite_count(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json=12345)
    with RobloxClient() as client:
        count = client.catalog.get_asset_favorite_count(100)
        assert count == 12345


def test_get_bundle_favorite_count(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json=678)
    with RobloxClient() as client:
        count = client.catalog.get_bundle_favorite_count(100)
        assert count == 678


def test_get_bundle_recommendations(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "data": [
            {"id": 10, "name": "Recommended Bundle"},
        ],
    })
    with RobloxClient() as client:
        recs = client.catalog.get_bundle_recommendations(500)
        assert len(recs) == 1
        assert recs[0].name == "Recommended Bundle"
