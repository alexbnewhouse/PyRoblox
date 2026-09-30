"""Tests for :mod:`pyroblox.friends`. No network: every test uses the
FakeSession from conftest and asserts the exact request that would be sent."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from pyroblox.client import PagedList
from pyroblox.errors import AuthRequiredError
from pyroblox.models.friends import Friend, FriendCounts
from tests.conftest import FakeResponse, make_client, page

BASE = "https://friends.roblox.com"

# Real shape from the probe: unauthenticated friends entries have blank names.
FRIENDS_261 = [
    {"id": 4371992339, "name": "", "displayName": ""},
    {"id": 41163986, "name": "", "displayName": ""},
    {"id": 1345006124, "name": "", "displayName": ""},
]
# Shape Roblox sends to authenticated callers (documented friends.roblox.com
# UserResponse): a superset of the unauthenticated entry.
FRIEND_FULL = {
    "isOnline": False,
    "isDeleted": False,
    "friendFrequentScore": 0,
    "friendFrequentRank": 201,
    "hasVerifiedBadge": True,
    "description": None,
    "created": "0001-01-01T05:51:00Z",
    "isBanned": False,
    "externalAppDisplayName": None,
    "id": 1,
    "name": "Roblox",
    "displayName": "Roblox",
}
AUTH_MISSING = {"errors": [{"code": 9002, "subcode": 0,
                            "message": "Authentication token is missing"}]}


def ids(models):
    return [m.id for m in models]


def roundtrip(models, raws):
    """to_record() also emits declared-but-absent fields as None; compare only
    the keys Roblox actually sent."""
    recs = [m.to_record() for m in models]
    assert len(recs) == len(raws)
    return [{k: v for k, v in rec.items() if k in raw} for rec, raw in zip(recs, raws)]


# -- get_friends --------------------------------------------------------------

def test_get_friends_returns_friend_models():
    client, session, _ = make_client(
        routes={f"GET {BASE}/v1/users/261/friends": {"data": FRIENDS_261}})
    out = client.friends.get_friends(261)
    assert isinstance(out, list) and all(isinstance(f, Friend) for f in out)
    assert ids(out) == [4371992339, 41163986, 1345006124]
    assert out[0].name == "" and out[0].display_name == ""
    assert roundtrip(out, FRIENDS_261) == FRIENDS_261
    call = session.calls[0]
    assert call.method == "GET"
    assert call.url == f"{BASE}/v1/users/261/friends"
    assert not call.params


def test_get_friends_empty():
    client, _, _ = make_client(routes={f"GET {BASE}/v1/users/1/friends": {"data": []}})
    assert client.friends.get_friends(1) == []


def test_get_friend_ids_extracts_ids():
    client, session, _ = make_client(
        routes={f"GET {BASE}/v1/users/261/friends": {"data": FRIENDS_261}})
    assert client.friends.get_friend_ids(261) == [4371992339, 41163986, 1345006124]
    assert session.urls == [f"{BASE}/v1/users/261/friends"]


def test_get_friend_count():
    client, session, _ = make_client(
        routes={f"GET {BASE}/v1/users/261/friends/count": {"count": 98}})
    assert client.friends.get_friend_count(261) == 98
    assert session.calls[0].url == f"{BASE}/v1/users/261/friends/count"
    assert not session.calls[0].params


def test_get_count_is_alias_of_get_friend_count():
    client, session, _ = make_client(
        routes={f"GET {BASE}/v1/users/261/friends/count": {"count": 98}})
    assert client.friends.get_count(261) == 98
    assert session.urls == [f"{BASE}/v1/users/261/friends/count"]
    assert client.friends.get_count.__func__ is client.friends.get_friend_count.__func__


# -- get_followers ------------------------------------------------------------

def test_get_followers_paginates_with_limit_100_asc():
    client, session, _ = make_client([
        FakeResponse(200, page([{"id": 10}, {"id": 11}], "c1")),
        FakeResponse(200, page([{"id": 12}], None)),
    ], cookie="SECRET")
    out = client.friends.get_followers(261)
    assert isinstance(out, PagedList)
    assert all(isinstance(f, Friend) for f in out)
    assert ids(out) == [10, 11, 12] and out.truncated is False
    assert session.calls[0].url == f"{BASE}/v1/users/261/followers"
    assert session.calls[0].params == {"limit": 100, "sortOrder": "Asc"}
    assert session.calls[0].cookies == {".ROBLOSECURITY": "SECRET"}
    assert session.calls[1].params == {"limit": 100, "sortOrder": "Asc", "cursor": "c1"}


def test_get_followers_honours_max_items():
    client, session, _ = make_client(
        [FakeResponse(200, page([{"id": 1}, {"id": 2}, {"id": 3}], "c1"))], cookie="SECRET")
    out = client.friends.get_followers(261, max_items=2)
    assert ids(out) == [1, 2] and out.truncated is True
    assert len(session.calls) == 1


def test_get_followers_without_cookie_raises_auth_required():
    client, _, _ = make_client([FakeResponse(401, AUTH_MISSING)])
    with pytest.raises(AuthRequiredError) as exc:
        client.friends.get_followers(261)
    assert exc.value.url == f"{BASE}/v1/users/261/followers"


def test_get_follower_count():
    client, session, _ = make_client(
        routes={f"GET {BASE}/v1/users/261/followers/count": {"count": 2124380}})
    assert client.friends.get_follower_count(261) == 2124380
    assert session.calls[0].url == f"{BASE}/v1/users/261/followers/count"


# -- get_followings -----------------------------------------------------------

def test_get_followings_paginates_with_limit_100_asc():
    client, session, _ = make_client([
        FakeResponse(200, page([{"id": 20}], "c1")),
        FakeResponse(200, page([FRIEND_FULL], None)),
    ], cookie="SECRET")
    out = client.friends.get_followings(261)
    assert isinstance(out, PagedList)
    assert all(isinstance(f, Friend) for f in out)
    assert ids(out) == [20, 1] and out.truncated is False
    assert out[1].name == "Roblox" and out[1].friend_frequent_rank == 201
    assert session.calls[0].url == f"{BASE}/v1/users/261/followings"
    assert session.calls[0].params == {"limit": 100, "sortOrder": "Asc"}
    assert session.calls[1].params == {"limit": 100, "sortOrder": "Asc", "cursor": "c1"}


def test_get_followings_honours_max_items():
    client, session, _ = make_client(
        [FakeResponse(200, page([{"id": 1}, {"id": 2}], "c1"))], cookie="SECRET")
    out = client.friends.get_followings(261, max_items=1)
    assert ids(out) == [1] and out.truncated is True
    assert len(session.calls) == 1


def test_get_followings_without_cookie_raises_auth_required():
    client, _, _ = make_client([FakeResponse(401, AUTH_MISSING)])
    with pytest.raises(AuthRequiredError) as exc:
        client.friends.get_followings(261)
    assert exc.value.url == f"{BASE}/v1/users/261/followings"


def test_get_following_count():
    client, session, _ = make_client(
        routes={f"GET {BASE}/v1/users/261/followings/count": {"count": 457735}})
    assert client.friends.get_following_count(261) == 457735
    assert session.calls[0].url == f"{BASE}/v1/users/261/followings/count"


# -- get_counts ---------------------------------------------------------------

def test_get_counts_composes_the_three_count_calls():
    client, session, _ = make_client(routes={
        f"GET {BASE}/v1/users/261/friends/count": {"count": 98},
        f"GET {BASE}/v1/users/261/followers/count": {"count": 2124380},
        f"GET {BASE}/v1/users/261/followings/count": {"count": 457735},
    })
    out = client.friends.get_counts(261)
    assert isinstance(out, FriendCounts)
    assert out.friends == 98 and out.followers == 2124380 and out.followings == 457735
    assert out.to_record() == {"friends": 98, "followers": 2124380, "followings": 457735}
    assert sorted(session.urls) == sorted([
        f"{BASE}/v1/users/261/friends/count",
        f"{BASE}/v1/users/261/followers/count",
        f"{BASE}/v1/users/261/followings/count",
    ])
    assert len(session.calls) == 3


# -- old names are gone -------------------------------------------------------

def test_old_method_names_are_not_kept():
    client, _, _ = make_client(routes={})
    for old in ("friends", "friend_ids", "friend_count", "followers", "follower_count",
                "followings", "following_count", "counts"):
        assert not hasattr(client.friends, old), old


# -- models -------------------------------------------------------------------

def test_friend_model_validates_unauthenticated_probe_payload():
    raw = dict(FRIENDS_261[0], someNewField="x")
    friend = Friend.model_validate(raw)
    assert friend.id == 4371992339
    assert friend.name == "" and friend.display_name == ""
    assert friend.has_verified_badge is False
    assert friend.is_online is None and friend.friend_frequent_score is None
    assert friend.created is None
    assert friend.model_extra == {"someNewField": "x"}
    assert friend.someNewField == "x"
    rec = friend.to_record()
    assert rec["displayName"] == "" and rec["someNewField"] == "x"
    assert rec.get("hasVerifiedBadge", False) is False   # only present when Roblox sent it
    assert "display_name" not in rec and "has_verified_badge" not in rec
    assert {k: v for k, v in rec.items() if k in raw} == raw


def test_friend_model_validates_authenticated_shape():
    friend = Friend.model_validate(FRIEND_FULL)
    assert friend.id == 1 and friend.name == "Roblox" and friend.display_name == "Roblox"
    assert friend.is_online is False and friend.is_deleted is False
    assert friend.friend_frequent_score == 0 and friend.friend_frequent_rank == 201
    assert friend.has_verified_badge is True and friend.is_banned is False
    assert friend.description is None
    assert friend.created == datetime(1, 1, 1, 5, 51, tzinfo=timezone.utc)
    # externalAppDisplayName is not declared on Friend -> kept as an extra
    assert friend.model_extra == {"externalAppDisplayName": None}
    rec = friend.to_record()
    assert rec["friendFrequentRank"] == 201 and rec["isOnline"] is False
    assert rec["externalAppDisplayName"] is None
    assert set(rec) == set(FRIEND_FULL)


def test_friend_counts_model():
    counts = FriendCounts(friends=98, followers=2124380, followings=457735)
    assert counts.friends == 98
    assert counts.to_record() == {"friends": 98, "followers": 2124380, "followings": 457735}
    # populate_by_name: building from a dict works too
    assert FriendCounts.model_validate({"friends": 1, "followers": 2, "followings": 3}).followings == 3


def test_friend_missing_required_field_raises_validation_error():
    with pytest.raises(ValidationError):
        Friend.model_validate({"name": "Roblox", "displayName": "Roblox"})


def test_friend_counts_missing_required_field_raises_validation_error():
    with pytest.raises(ValidationError):
        FriendCounts(friends=1, followers=2)
