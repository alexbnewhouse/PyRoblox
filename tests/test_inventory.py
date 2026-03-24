"""Tests for InventoryAPI resource methods."""

from pytest_httpx import HTTPXMock

from pyroblox.client import RobloxClient


def test_can_view_inventory(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={"canView": True})
    with RobloxClient() as client:
        assert client.inventory.can_view(123) is True


def test_can_view_inventory_private(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={"canView": False})
    with RobloxClient() as client:
        assert client.inventory.can_view(456) is False


def test_get_collectibles(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "data": [
            {
                "userAssetId": 1000,
                "assetId": 200,
                "name": "Rare Hat",
                "serialNumber": 42,
                "recentAveragePrice": 5000,
            },
        ],
        "nextPageCursor": None,
    })
    with RobloxClient() as client:
        items = list(client.inventory.get_collectibles(123))
        assert len(items) == 1
        assert items[0].asset_id == 200
        assert items[0].name == "Rare Hat"
        assert items[0].serial_number == 42
        assert items[0].recent_average_price == 5000


def test_get_user_inventory(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "data": [
            {"assetId": 300, "name": "Cool Shirt", "assetType": "Shirt"},
            {"assetId": 301, "name": "Nice Shirt", "assetType": "Shirt"},
        ],
        "nextPageCursor": None,
    })
    with RobloxClient() as client:
        items = list(client.inventory.get_user_inventory(123, 11))  # 11 = Shirt
        assert len(items) == 2
        assert items[0].name == "Cool Shirt"


def test_get_asset_owners(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "data": [
            {"id": 1, "serialNumber": 1, "owner": {"id": 100, "type": "User", "name": "Player1"}},
            {"id": 2, "serialNumber": 2, "owner": {"id": 200, "type": "User", "name": "Player2"}},
        ],
        "nextPageCursor": None,
    })
    with RobloxClient() as client:
        owners = list(client.inventory.get_asset_owners(500))
        assert len(owners) == 2
        assert owners[0].owner is not None
        assert owners[0].owner.name == "Player1"
