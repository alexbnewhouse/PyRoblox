"""Tests for BadgesAPI resource methods."""

from pytest_httpx import HTTPXMock

from pyroblox.client import RobloxClient


def test_get_badge_info(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "id": 100,
        "name": "Welcome Badge",
        "description": "Awarded for joining",
        "enabled": True,
        "statistics": {
            "pastDayAwardedCount": 50,
            "awardedCount": 10000,
            "winRatePercentage": 75.5,
        },
        "created": "2020-01-01T00:00:00Z",
    })
    with RobloxClient() as client:
        badge = client.badges.get_info(100)
        assert badge.id == 100
        assert badge.name == "Welcome Badge"
        assert badge.statistics is not None
        assert badge.statistics.awarded_count == 10000
        assert badge.statistics.win_rate_percentage == 75.5


def test_get_universe_badges(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "data": [
            {"id": 1, "name": "Badge1"},
            {"id": 2, "name": "Badge2"},
        ],
        "nextPageCursor": None,
    })
    with RobloxClient() as client:
        badges = list(client.badges.get_universe_badges(999))
        assert len(badges) == 2
        assert badges[0].name == "Badge1"


def test_get_user_badges(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "data": [
            {"id": 10, "name": "Earned Badge", "enabled": True},
        ],
        "nextPageCursor": None,
    })
    with RobloxClient() as client:
        badges = list(client.badges.get_user_badges(123))
        assert len(badges) == 1
        assert badges[0].id == 10


def test_get_awarded_dates(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "data": [
            {"badgeId": 1, "awardedDate": "2023-06-15T12:00:00Z"},
            {"badgeId": 2, "awardedDate": "2023-07-01T08:30:00Z"},
        ],
    })
    with RobloxClient() as client:
        dates = client.badges.get_awarded_dates(123, [1, 2])
        assert len(dates) == 2
        assert dates[0].badge_id == 1
        assert dates[0].awarded_date is not None
