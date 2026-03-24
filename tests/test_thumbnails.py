"""Tests for ThumbnailsAPI resource methods."""

from pytest_httpx import HTTPXMock

from pyroblox.client import RobloxClient


def test_get_user_headshots(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "data": [
            {"targetId": 1, "state": "Completed", "imageUrl": "https://example.com/1.png"},
            {"targetId": 2, "state": "Completed", "imageUrl": "https://example.com/2.png"},
        ],
    })
    with RobloxClient() as client:
        thumbs = client.thumbnails.get_user_headshots([1, 2])
        assert len(thumbs) == 2
        assert thumbs[0].target_id == 1
        assert thumbs[0].state == "Completed"
        assert thumbs[0].image_url == "https://example.com/1.png"


def test_get_user_avatars(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "data": [
            {"targetId": 1, "state": "Completed", "imageUrl": "https://example.com/avatar.png"},
        ],
    })
    with RobloxClient() as client:
        thumbs = client.thumbnails.get_user_avatars([1])
        assert len(thumbs) == 1


def test_get_asset_thumbnails(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "data": [
            {"targetId": 100, "state": "Completed", "imageUrl": "https://example.com/asset.png"},
        ],
    })
    with RobloxClient() as client:
        thumbs = client.thumbnails.get_asset_thumbnails([100])
        assert len(thumbs) == 1
        assert thumbs[0].target_id == 100


def test_get_game_icons(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "data": [
            {"targetId": 999, "state": "Completed", "imageUrl": "https://example.com/game.png"},
        ],
    })
    with RobloxClient() as client:
        thumbs = client.thumbnails.get_game_icons([999])
        assert len(thumbs) == 1


def test_get_group_icons(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "data": [
            {"targetId": 50, "state": "Completed", "imageUrl": "https://example.com/group.png"},
        ],
    })
    with RobloxClient() as client:
        thumbs = client.thumbnails.get_group_icons([50])
        assert len(thumbs) == 1


def test_get_badge_icons(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "data": [
            {"targetId": 77, "state": "Completed", "imageUrl": "https://example.com/badge.png"},
        ],
    })
    with RobloxClient() as client:
        thumbs = client.thumbnails.get_badge_icons([77])
        assert len(thumbs) == 1
        assert thumbs[0].target_id == 77
