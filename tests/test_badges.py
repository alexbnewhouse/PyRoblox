"""Tests for pyroblox.badges (badges.roblox.com). No network."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from pyroblox.badges import BadgesAPI
from pyroblox.client import PagedList
from pyroblox.errors import AuthRequiredError, NotFoundError
from pyroblox.models.badges import AwardingUniverse, Badge, BadgeAwardDate, BadgeStatistics
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
AWARDED = "2023-04-01T12:00:00.000+00:00"
AWARDED_DT = datetime(2023, 4, 1, 12, tzinfo=timezone.utc)


def test_client_exposes_badges_api():
    client, _, _ = make_client(routes={})
    assert isinstance(client.badges, BadgesAPI)
    assert client.badges.client is client
    assert BadgesAPI.BASE == BASE


# -- get_user_badges ----------------------------------------------------------

def test_user_badges_paginates_with_limit_100_and_asc():
    client, session, _ = make_client(routes={
        f"GET {BASE}/v1/users/261/badges": [page([BADGE], "c1"), page([BADGE2], None)],
    })
    out = client.badges.get_user_badges(261)
    assert isinstance(out, PagedList)
    assert all(isinstance(b, Badge) for b in out)
    assert [b.id for b in out] == [2125253106, 2125253113] and out.truncated is False
    assert out[1].name == "Third Sea"
    assert session.calls[0].method == "GET"
    assert session.calls[0].params == {"limit": 100, "sortOrder": "Asc"}
    assert session.calls[1].params == {"limit": 100, "sortOrder": "Asc", "cursor": "c1"}


def test_user_badges_honours_max_items():
    client, session, _ = make_client(routes={
        f"GET {BASE}/v1/users/261/badges": page([BADGE, BADGE2, dict(BADGE, id=3)], "c1"),
    })
    out = client.badges.get_user_badges(261, max_items=2)
    assert [b.id for b in out] == [2125253106, 2125253113] and out.truncated is True
    assert len(session.calls) == 1


def test_user_badges_unauthenticated_raises_auth_required():
    body = {"errors": [{"code": 9002, "subcode": 0, "message": "Authentication token is missing"}]}
    client, _, _ = make_client([FakeResponse(401, body)])
    with pytest.raises(AuthRequiredError):
        client.badges.get_user_badges(261)


# -- get_awarded_dates --------------------------------------------------------

def test_awarded_dates_joins_ids_and_unwraps_data():
    rows = [{"badgeId": 2125253106, "awardedDate": AWARDED},
            {"badgeId": 2125253113, "awardedDate": "2023-05-01T12:00:00.000+00:00"}]
    client, session, _ = make_client(routes={
        f"GET {BASE}/v1/users/261/badges/awarded-dates": {"data": rows},
    })
    out = client.badges.get_awarded_dates(261, [2125253106, 2125253113])
    assert type(out) is list and all(isinstance(r, BadgeAwardDate) for r in out)
    assert [r.badge_id for r in out] == [2125253106, 2125253113]
    assert out[0].awarded_date == AWARDED_DT
    assert out[1].awarded_date == datetime(2023, 5, 1, 12, tzinfo=timezone.utc)
    assert session.calls[0].method == "GET"
    assert session.calls[0].params == {"badgeIds": "2125253106,2125253113"}


def test_awarded_dates_chunks_150_ids_into_two_calls():
    ids = list(range(1, 151))
    client, session, _ = make_client([
        FakeResponse(200, {"data": [{"badgeId": i, "awardedDate": AWARDED} for i in ids[:100]]}),
        FakeResponse(200, {"data": [{"badgeId": i, "awardedDate": AWARDED} for i in ids[100:]]}),
    ])
    out = client.badges.get_awarded_dates(261, ids)
    assert len(session.calls) == 2
    assert session.calls[0].url == f"{BASE}/v1/users/261/badges/awarded-dates"
    assert session.calls[0].params == {"badgeIds": ",".join(map(str, ids[:100]))}
    assert session.calls[1].params == {"badgeIds": ",".join(map(str, ids[100:]))}
    assert [r.badge_id for r in out] == ids


def test_awarded_dates_with_no_ids_makes_no_request():
    client, session, _ = make_client(routes={})
    assert client.badges.get_awarded_dates(261, []) == []
    assert session.calls == []


# -- get_universe_badges ------------------------------------------------------

def test_universe_badges_paginates_with_limit_100_and_asc():
    client, session, _ = make_client(routes={
        f"GET {BASE}/v1/universes/994732206/badges": [page([BADGE], "c1"), page([BADGE2], None)],
    })
    out = client.badges.get_universe_badges(994732206)
    assert isinstance(out, PagedList)
    assert all(isinstance(b, Badge) for b in out)
    assert [b.id for b in out] == [2125253106, 2125253113] and out.truncated is False
    assert out[0].statistics.awarded_count == 97135072
    assert session.calls[0].params == {"limit": 100, "sortOrder": "Asc"}
    assert session.calls[1].params == {"limit": 100, "sortOrder": "Asc", "cursor": "c1"}


def test_universe_badges_honours_max_items():
    client, session, _ = make_client(routes={
        f"GET {BASE}/v1/universes/994732206/badges": page([BADGE, BADGE2], "c1"),
    })
    out = client.badges.get_universe_badges(994732206, max_items=1)
    assert [b.id for b in out] == [2125253106] and out.truncated is True
    assert len(session.calls) == 1


# -- get_info -----------------------------------------------------------------

def test_get_info_returns_badge_model():
    client, session, _ = make_client(routes={f"GET {BASE}/v1/badges/2125253106": BADGE})
    out = client.badges.get_info(2125253106)
    assert isinstance(out, Badge)
    assert out.id == 2125253106 and out.name == "Second Sea"
    assert out.enabled is True and out.icon_image_id == 9043500281
    assert out.statistics.past_day_awarded_count == 31593
    assert out.awarding_universe.root_place_id == 2753915549
    assert session.calls[0].method == "GET"
    assert session.calls[0].params is None


def test_get_info_missing_badge_raises_not_found():
    client, _, _ = make_client([FakeResponse(404)])
    with pytest.raises(NotFoundError) as exc:
        client.badges.get_info(1)
    assert exc.value.url == f"{BASE}/v1/badges/1"


# -- models -------------------------------------------------------------------

def test_badge_model_validates_probe_payload():
    badge = Badge.model_validate(dict(BADGE, communityTier="Gold"))
    assert badge.display_name == "Second Sea"
    assert badge.display_description == BADGE["displayDescription"]
    assert badge.display_icon_image_id == 9043500281
    assert badge.created == datetime(2022, 3, 8, 8, 32, 52, 703000, tzinfo=timezone.utc)
    assert badge.updated == badge.created
    assert isinstance(badge.statistics, BadgeStatistics)
    assert badge.statistics.win_rate_percentage == 0.008
    assert isinstance(badge.awarding_universe, AwardingUniverse)
    assert badge.awarding_universe.name == "Blox Fruits"
    assert badge.model_extra == {"communityTier": "Gold"}
    assert badge.communityTier == "Gold"
    rec = badge.to_record()
    assert set(BADGE) <= set(rec)
    assert rec["displayIconImageId"] == 9043500281
    assert rec["statistics"] == BADGE["statistics"]
    assert rec["awardingUniverse"] == BADGE["awardingUniverse"]
    assert rec["communityTier"] == "Gold"
    assert rec["created"].startswith("2022-03-08T08:32:52")


def test_badge_statistics_model():
    stats = BadgeStatistics.model_validate({"pastDayAwardedCount": 5, "awardedCount": 9,
                                            "winRatePercentage": 0.5, "streak": 1})
    assert stats.past_day_awarded_count == 5 and stats.awarded_count == 9
    assert stats.win_rate_percentage == 0.5
    assert stats.model_extra == {"streak": 1}
    assert stats.to_record() == {"pastDayAwardedCount": 5, "awardedCount": 9,
                                 "winRatePercentage": 0.5, "streak": 1}
    empty = BadgeStatistics()
    assert (empty.past_day_awarded_count, empty.awarded_count, empty.win_rate_percentage) == (0, 0, 0.0)


def test_awarding_universe_model():
    universe = AwardingUniverse.model_validate({"id": 994732206, "name": "Blox Fruits",
                                                "rootPlaceId": 2753915549, "genre": "Adventure"})
    assert universe.id == 994732206 and universe.root_place_id == 2753915549
    assert universe.model_extra == {"genre": "Adventure"}
    assert universe.to_record() == {"id": 994732206, "name": "Blox Fruits",
                                    "rootPlaceId": 2753915549, "genre": "Adventure"}


def test_badge_award_date_model():
    row = BadgeAwardDate.model_validate({"badgeId": 2125253106, "awardedDate": AWARDED,
                                         "source": "probe"})
    assert row.badge_id == 2125253106
    assert row.awarded_date == AWARDED_DT
    assert row.model_extra == {"source": "probe"}
    rec = row.to_record()
    assert set(rec) == {"badgeId", "awardedDate", "source"}
    assert rec["awardedDate"].startswith("2023-04-01T12:00:00")


@pytest.mark.parametrize("model, payload", [
    pytest.param(Badge, {"name": "no id"}, id="Badge-no-id"),
    pytest.param(Badge, {"id": 1}, id="Badge-no-name"),
    pytest.param(Badge, {"id": "not-a-number", "name": "x"}, id="Badge-id-not-int"),
    pytest.param(Badge, dict(BADGE, awardingUniverse={"name": "no id"}), id="Badge-nested-universe-no-id"),
    pytest.param(AwardingUniverse, {"name": "no id"}, id="AwardingUniverse-no-id"),
    pytest.param(BadgeAwardDate, {"awardedDate": AWARDED}, id="BadgeAwardDate-no-badgeId"),
])
def test_missing_or_invalid_required_field_raises_validation_error(model, payload):
    with pytest.raises(ValidationError):
        model.model_validate(payload)
