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
        assert friends[0].name == "friend1"
        assert friends[1].display_name == "Friend 2"


def test_get_friends_empty(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={"data": []})
    with RobloxClient() as client:
        friends = client.friends.get_friends(100)
        assert friends == []


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
        assert followers[0].id == 1
        assert followers[1].id == 2


def test_get_followings(httpx_mock: HTTPXMock) -> None:
    """get_followings must actually hit the followings endpoint."""
    httpx_mock.add_response(json={
        "data": [{"id": 50, "name": "following1", "displayName": "F"}],
        "nextPageCursor": None,
    })
    with RobloxClient() as client:
        followings = list(client.friends.get_followings(100))
        assert len(followings) == 1
        assert followings[0].id == 50


def test_get_followers_max_pages(httpx_mock: HTTPXMock) -> None:
    """max_pages should stop fetching even if more pages exist."""
    httpx_mock.add_response(json={
        "data": [{"id": 1, "name": "f1", "displayName": "F1"}],
        "nextPageCursor": "more",
    })
    # Only 1 response queued — if max_pages is ignored, this will fail
    with RobloxClient() as client:
        followers = list(client.friends.get_followers(100, max_pages=1))
        assert len(followers) == 1
