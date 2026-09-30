"""Tests for :mod:`robloxwrapper.friends`. No network: every test uses the
FakeSession from conftest and asserts the exact request that would be sent."""

import pytest

from robloxwrapper.client import PagedList
from robloxwrapper.errors import AuthRequiredError
from tests.conftest import FakeResponse, make_client, page

BASE = "https://friends.roblox.com"

# Real shape from the probe: unauthenticated friends entries have blank names.
FRIENDS_261 = [
    {"id": 4371992339, "name": "", "displayName": ""},
    {"id": 41163986, "name": "", "displayName": ""},
    {"id": 1345006124, "name": "", "displayName": ""},
]
AUTH_MISSING = {"errors": [{"code": 9002, "subcode": 0,
                            "message": "Authentication token is missing"}]}


# -- friends ------------------------------------------------------------------

def test_friends_returns_data_list():
    client, session, _ = make_client(
        routes={f"GET {BASE}/v1/users/261/friends": {"data": FRIENDS_261}})
    assert client.friends.friends(261) == FRIENDS_261
    call = session.calls[0]
    assert call.method == "GET"
    assert call.url == f"{BASE}/v1/users/261/friends"
    assert not call.params


def test_friends_empty():
    client, _, _ = make_client(routes={f"GET {BASE}/v1/users/1/friends": {"data": []}})
    assert client.friends.friends(1) == []


def test_friend_ids_extracts_ids():
    client, session, _ = make_client(
        routes={f"GET {BASE}/v1/users/261/friends": {"data": FRIENDS_261}})
    assert client.friends.friend_ids(261) == [4371992339, 41163986, 1345006124]
    assert session.urls == [f"{BASE}/v1/users/261/friends"]


def test_friend_count():
    client, session, _ = make_client(
        routes={f"GET {BASE}/v1/users/261/friends/count": {"count": 98}})
    assert client.friends.friend_count(261) == 98
    assert session.calls[0].url == f"{BASE}/v1/users/261/friends/count"
    assert not session.calls[0].params


# -- followers ----------------------------------------------------------------

def test_followers_paginates_with_limit_100_asc():
    client, session, _ = make_client([
        FakeResponse(200, page([{"id": 10}, {"id": 11}], "c1")),
        FakeResponse(200, page([{"id": 12}], None)),
    ], cookie="SECRET")
    out = client.friends.followers(261)
    assert isinstance(out, PagedList)
    assert out == [{"id": 10}, {"id": 11}, {"id": 12}] and out.truncated is False
    assert session.calls[0].url == f"{BASE}/v1/users/261/followers"
    assert session.calls[0].params == {"limit": 100, "sortOrder": "Asc"}
    assert session.calls[0].cookies == {".ROBLOSECURITY": "SECRET"}
    assert session.calls[1].params == {"limit": 100, "sortOrder": "Asc", "cursor": "c1"}


def test_followers_honours_max_items():
    client, session, _ = make_client(
        [FakeResponse(200, page([{"id": 1}, {"id": 2}, {"id": 3}], "c1"))], cookie="SECRET")
    out = client.friends.followers(261, max_items=2)
    assert out == [{"id": 1}, {"id": 2}] and out.truncated is True
    assert len(session.calls) == 1


def test_followers_without_cookie_raises_auth_required():
    client, _, _ = make_client([FakeResponse(401, AUTH_MISSING)])
    with pytest.raises(AuthRequiredError) as exc:
        client.friends.followers(261)
    assert exc.value.url == f"{BASE}/v1/users/261/followers"


def test_follower_count():
    client, session, _ = make_client(
        routes={f"GET {BASE}/v1/users/261/followers/count": {"count": 2124380}})
    assert client.friends.follower_count(261) == 2124380
    assert session.calls[0].url == f"{BASE}/v1/users/261/followers/count"


# -- followings ---------------------------------------------------------------

def test_followings_paginates_with_limit_100_asc():
    client, session, _ = make_client([
        FakeResponse(200, page([{"id": 20}], "c1")),
        FakeResponse(200, page([{"id": 21}], None)),
    ], cookie="SECRET")
    out = client.friends.followings(261)
    assert isinstance(out, PagedList)
    assert out == [{"id": 20}, {"id": 21}] and out.truncated is False
    assert session.calls[0].url == f"{BASE}/v1/users/261/followings"
    assert session.calls[0].params == {"limit": 100, "sortOrder": "Asc"}
    assert session.calls[1].params == {"limit": 100, "sortOrder": "Asc", "cursor": "c1"}


def test_followings_honours_max_items():
    client, session, _ = make_client(
        [FakeResponse(200, page([{"id": 1}, {"id": 2}], "c1"))], cookie="SECRET")
    out = client.friends.followings(261, max_items=1)
    assert out == [{"id": 1}] and out.truncated is True
    assert len(session.calls) == 1


def test_followings_without_cookie_raises_auth_required():
    client, _, _ = make_client([FakeResponse(401, AUTH_MISSING)])
    with pytest.raises(AuthRequiredError) as exc:
        client.friends.followings(261)
    assert exc.value.url == f"{BASE}/v1/users/261/followings"


def test_following_count():
    client, session, _ = make_client(
        routes={f"GET {BASE}/v1/users/261/followings/count": {"count": 457735}})
    assert client.friends.following_count(261) == 457735
    assert session.calls[0].url == f"{BASE}/v1/users/261/followings/count"


# -- counts -------------------------------------------------------------------

def test_counts_composes_the_three_count_calls():
    client, session, _ = make_client(routes={
        f"GET {BASE}/v1/users/261/friends/count": {"count": 98},
        f"GET {BASE}/v1/users/261/followers/count": {"count": 2124380},
        f"GET {BASE}/v1/users/261/followings/count": {"count": 457735},
    })
    assert client.friends.counts(261) == {
        "friends": 98, "followers": 2124380, "followings": 457735}
    assert sorted(session.urls) == sorted([
        f"{BASE}/v1/users/261/friends/count",
        f"{BASE}/v1/users/261/followers/count",
        f"{BASE}/v1/users/261/followings/count",
    ])
    assert len(session.calls) == 3
