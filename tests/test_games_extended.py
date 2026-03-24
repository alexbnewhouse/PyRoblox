"""Tests for extended GamesAPI methods (votes, favorites count, servers)."""

from pytest_httpx import HTTPXMock

from pyroblox.client import RobloxClient


def test_get_votes(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "data": [
            {"id": 100, "upVotes": 5000, "downVotes": 200},
            {"id": 200, "upVotes": 1000, "downVotes": 50},
        ],
    })
    with RobloxClient() as client:
        votes = client.games.get_votes([100, 200])
        assert len(votes) == 2
        assert votes[0].up_votes == 5000
        assert votes[0].down_votes == 200
        assert votes[1].id == 200


def test_get_favorites_count(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={"favoritesCount": 42000})
    with RobloxClient() as client:
        count = client.games.get_favorites_count(100)
        assert count == 42000


def test_get_servers(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "data": [
            {"id": "abc-123", "maxPlayers": 50, "playing": 30, "fps": 59.9, "ping": 80},
            {"id": "def-456", "maxPlayers": 50, "playing": 10, "fps": 60.0, "ping": 45},
        ],
        "nextPageCursor": None,
    })
    with RobloxClient() as client:
        servers = list(client.games.get_servers(12345))
        assert len(servers) == 2
        assert servers[0].playing == 30
        assert servers[0].fps == 59.9
        assert servers[1].id == "def-456"
