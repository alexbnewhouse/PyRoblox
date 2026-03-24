"""Tests for GamesAPI resource methods."""

from pytest_httpx import HTTPXMock

from pyroblox.client import RobloxClient


def test_get_group_games(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "data": [
            {"id": 1, "name": "Game1"},
            {"id": 2, "name": "Game2"},
        ],
        "nextPageCursor": None,
    })
    with RobloxClient() as client:
        games = list(client.games.get_group_games(100))
        assert len(games) == 2
        assert games[0].name == "Game1"


def test_get_user_games(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "data": [
            {"id": 10, "name": "MyGame", "placeVisits": 100},
        ],
        "nextPageCursor": None,
    })
    with RobloxClient() as client:
        games = list(client.games.get_user_games(1))
        assert len(games) == 1
        assert games[0].name == "MyGame"
        assert games[0].place_visits == 100


def test_get_user_favorites(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "data": [
            {"id": 10, "name": "FavGame", "placeVisits": 5000},
        ],
        "nextPageCursor": None,
    })
    with RobloxClient() as client:
        favs = list(client.games.get_user_favorites(1))
        assert len(favs) == 1
        assert favs[0].place_visits == 5000


def test_get_info_batch(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "data": [
            {"id": 100, "name": "Universe1", "playing": 50},
            {"id": 200, "name": "Universe2", "playing": 100},
        ],
    })
    with RobloxClient() as client:
        games = client.games.get_info([100, 200])
        assert len(games) == 2
        assert games[1].playing == 100


def test_get_group_games_max_pages(httpx_mock: HTTPXMock) -> None:
    """max_pages must actually limit page fetching."""
    httpx_mock.add_response(json={
        "data": [{"id": 1, "name": "Game1"}],
        "nextPageCursor": "more",
    })
    with RobloxClient() as client:
        games = list(client.games.get_group_games(100, max_pages=1))
        assert len(games) == 1


def test_get_info_empty(httpx_mock: HTTPXMock) -> None:
    """Empty universe list should return empty list, not crash."""
    httpx_mock.add_response(json={"data": []})
    with RobloxClient() as client:
        games = client.games.get_info([999999])
        assert games == []
