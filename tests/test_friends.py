"""Tests for FriendsAPI resource methods."""

from pytest_httpx import HTTPXMock

from pyroblox.client import RobloxClient


def test_get_friends(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "data": [
            {"id": 1, "name": "friend1", "displayName": "Friend 1"},
            {"id": 2, "name": "friend2", "displayName": "Friend 2"},
        ],
    })
    with RobloxClient() as client:
        friends = client.friends.get_friends(100)
        assert len(friends) == 2
        assert friends[0].id == 1


def test_get_count(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={"count": 42})
    with RobloxClient() as client:
        count = client.friends.get_count(100)
        assert count == 42


def test_get_followers_pagination(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "data": [{"id": 1, "name": "f1", "displayName": "F1"}],
        "nextPageCursor": "page2",
        "previousPageCursor": None,
    })
    httpx_mock.add_response(json={
        "data": [{"id": 2, "name": "f2", "displayName": "F2"}],
        "nextPageCursor": None,
        "previousPageCursor": "page1",
    })
    with RobloxClient() as client:
        followers = list(client.friends.get_followers(100))
        assert len(followers) == 2
