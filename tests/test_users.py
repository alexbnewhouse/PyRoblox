"""Tests for UsersAPI resource methods."""

from pytest_httpx import HTTPXMock

from pyroblox.client import RobloxClient


def test_get_info(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "id": 100,
        "name": "testuser",
        "displayName": "Test User",
        "description": "Hello",
        "created": "2020-01-01T00:00:00Z",
        "isBanned": False,
        "hasVerifiedBadge": False,
    })
    with RobloxClient() as client:
        user = client.users.get_info(100)
        assert user.id == 100
        assert user.name == "testuser"


def test_get_batch(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "data": [
            {"id": 1, "name": "user1", "displayName": "User 1"},
            {"id": 2, "name": "user2", "displayName": "User 2"},
        ],
    })
    with RobloxClient() as client:
        users = client.users.get_batch([1, 2])
        assert len(users) == 2
        assert users[0].id == 1


def test_search(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "data": [
            {"id": 10, "name": "testplayer", "displayName": "Test Player"},
        ],
    })
    with RobloxClient() as client:
        results = client.users.search("test")
        assert len(results) == 1
        assert results[0].name == "testplayer"
