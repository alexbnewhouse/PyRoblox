"""Tests for robloxwrapper.badges (badges.roblox.com). No network."""

import pytest

from robloxwrapper.badges import BadgesAPI
from robloxwrapper.client import PagedList
from robloxwrapper.errors import AuthRequiredError, NotFoundError
from tests.conftest import FakeResponse, make_client, page

BASE = "https://badges.roblox.com"

# Real shape from GET /v1/badges/2125253106 (probe, 2026-09).
BADGE = {
    "id": 2125253106,
    "name": "Second Sea",
    "description": "You have reached the Second Sea! Ready to awaken the true potential of your fruits?",
    "displayName": "Second Sea",
    "displayDescription": "You have reached the Second Sea! Ready to awaken the true potential of your fruits?",
    "enabled": True,
    "iconImageId": 9043500281,
    "displayIconImageId": 9043500281,
    "created": "2022-03-08T08:32:52.703+00:00",
    "updated": "2022-03-08T08:32:52.703+00:00",
    "statistics": {"pastDayAwardedCount": 31593, "awardedCount": 97135072,
                   "winRatePercentage": 0.008},
    "awardingUniverse": {"id": 994732206, "name": "Blox Fruits", "rootPlaceId": 2753915549},
}
BADGE2 = dict(BADGE, id=2125253113, name="Third Sea")


def test_client_exposes_badges_api():
    client, _, _ = make_client(routes={})
    assert isinstance(client.badges, BadgesAPI)
    assert client.badges.client is client
    assert BadgesAPI.BASE == BASE


# -- user_badges --------------------------------------------------------------

def test_user_badges_paginates_with_limit_100_and_asc():
    client, session, _ = make_client(routes={
        f"GET {BASE}/v1/users/261/badges": [page([BADGE], "c1"), page([BADGE2], None)],
    })
    out = client.badges.user_badges(261)
    assert isinstance(out, PagedList)
    assert out == [BADGE, BADGE2] and out.truncated is False
    assert session.calls[0].method == "GET"
    assert session.calls[0].params == {"limit": 100, "sortOrder": "Asc"}
    assert session.calls[1].params == {"limit": 100, "sortOrder": "Asc", "cursor": "c1"}


def test_user_badges_honours_max_items():
    client, session, _ = make_client(routes={
        f"GET {BASE}/v1/users/261/badges": page([BADGE, BADGE2, dict(BADGE, id=3)], "c1"),
    })
    out = client.badges.user_badges(261, max_items=2)
    assert [b["id"] for b in out] == [2125253106, 2125253113] and out.truncated is True
    assert len(session.calls) == 1


def test_user_badges_unauthenticated_raises_auth_required():
    body = {"errors": [{"code": 9002, "subcode": 0, "message": "Authentication token is missing"}]}
    client, _, _ = make_client([FakeResponse(401, body)])
    with pytest.raises(AuthRequiredError):
        client.badges.user_badges(261)


# -- awarded_dates ------------------------------------------------------------

def test_awarded_dates_joins_ids_and_unwraps_data():
    rows = [{"badgeId": 2125253106, "awardedDate": "2023-04-01T12:00:00.000+00:00"},
            {"badgeId": 2125253113, "awardedDate": "2023-05-01T12:00:00.000+00:00"}]
    client, session, _ = make_client(routes={
        f"GET {BASE}/v1/users/261/badges/awarded-dates": {"data": rows},
    })
    out = client.badges.awarded_dates(261, [2125253106, 2125253113])
    assert out == rows and type(out) is list
    assert session.calls[0].method == "GET"
    assert session.calls[0].params == {"badgeIds": "2125253106,2125253113"}


def test_awarded_dates_chunks_150_ids_into_two_calls():
    ids = list(range(1, 151))
    client, session, _ = make_client([
        FakeResponse(200, {"data": [{"badgeId": i, "awardedDate": "d"} for i in ids[:100]]}),
        FakeResponse(200, {"data": [{"badgeId": i, "awardedDate": "d"} for i in ids[100:]]}),
    ])
    out = client.badges.awarded_dates(261, ids)
    assert len(session.calls) == 2
    assert session.calls[0].url == f"{BASE}/v1/users/261/badges/awarded-dates"
    assert session.calls[0].params == {"badgeIds": ",".join(map(str, ids[:100]))}
    assert session.calls[1].params == {"badgeIds": ",".join(map(str, ids[100:]))}
    assert [r["badgeId"] for r in out] == ids


def test_awarded_dates_with_no_ids_makes_no_request():
    client, session, _ = make_client(routes={})
    assert client.badges.awarded_dates(261, []) == []
    assert session.calls == []


# -- universe_badges ----------------------------------------------------------

def test_universe_badges_paginates_with_limit_100_and_asc():
    client, session, _ = make_client(routes={
        f"GET {BASE}/v1/universes/994732206/badges": [page([BADGE], "c1"), page([BADGE2], None)],
    })
    out = client.badges.universe_badges(994732206)
    assert isinstance(out, PagedList)
    assert out == [BADGE, BADGE2] and out.truncated is False
    assert session.calls[0].params == {"limit": 100, "sortOrder": "Asc"}
    assert session.calls[1].params == {"limit": 100, "sortOrder": "Asc", "cursor": "c1"}


def test_universe_badges_honours_max_items():
    client, session, _ = make_client(routes={
        f"GET {BASE}/v1/universes/994732206/badges": page([BADGE, BADGE2], "c1"),
    })
    out = client.badges.universe_badges(994732206, max_items=1)
    assert out == [BADGE] and out.truncated is True
    assert len(session.calls) == 1


# -- get ----------------------------------------------------------------------

def test_get_returns_badge_object():
    client, session, _ = make_client(routes={f"GET {BASE}/v1/badges/2125253106": BADGE})
    assert client.badges.get(2125253106) == BADGE
    assert session.calls[0].method == "GET"
    assert session.calls[0].params is None


def test_get_missing_badge_raises_not_found():
    client, _, _ = make_client([FakeResponse(404)])
    with pytest.raises(NotFoundError) as exc:
        client.badges.get(1)
    assert exc.value.url == f"{BASE}/v1/badges/1"
