"""Tests for the edgelist building utilities."""

from pytest_httpx import HTTPXMock

from pyroblox.client import RobloxClient
from pyroblox.contrib.edgelists import friend_edgelist, group_edgelist


def test_group_edgelist_depth_1(httpx_mock: HTTPXMock) -> None:
    # Allies response
    httpx_mock.add_response(json={
        "relatedGroups": [{"id": 10, "name": "Ally1"}],
    })
    # Enemies response
    httpx_mock.add_response(json={
        "relatedGroups": [{"id": 20, "name": "Enemy1"}],
    })
    with RobloxClient() as client:
        result = group_edgelist(client, 1, depth=1)
        assert result["allies"] == [(1, 10)]
        assert result["enemies"] == [(1, 20)]


def test_group_edgelist_depth_2(httpx_mock: HTTPXMock) -> None:
    # Allies of seed
    httpx_mock.add_response(json={
        "relatedGroups": [{"id": 10, "name": "Ally1"}],
    })
    # Enemies of seed
    httpx_mock.add_response(json={
        "relatedGroups": [{"id": 20, "name": "Enemy1"}],
    })
    # Allies of ally 10
    httpx_mock.add_response(json={
        "relatedGroups": [{"id": 30, "name": "Ally1-Ally"}],
    })
    # Enemies of enemy 20
    httpx_mock.add_response(json={
        "relatedGroups": [{"id": 40, "name": "Enemy1-Enemy"}],
    })
    with RobloxClient() as client:
        result = group_edgelist(client, 1, depth=2)
        assert (1, 10) in result["allies"]
        assert (10, 30) in result["allies"]
        assert (1, 20) in result["enemies"]
        assert (20, 40) in result["enemies"]


def test_friend_edgelist_depth_1(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "data": [
            {"id": 10, "name": "f1", "displayName": "F1"},
            {"id": 20, "name": "f2", "displayName": "F2"},
        ],
    })
    with RobloxClient() as client:
        edges = friend_edgelist(client, 1, depth=1)
        assert edges == [(1, 10), (1, 20)]


def test_friend_edgelist_depth_2(httpx_mock: HTTPXMock) -> None:
    # Friends of seed
    httpx_mock.add_response(json={
        "data": [{"id": 10, "name": "f1", "displayName": "F1"}],
    })
    # Friends of friend 10
    httpx_mock.add_response(json={
        "data": [{"id": 30, "name": "f3", "displayName": "F3"}],
    })
    with RobloxClient() as client:
        edges = friend_edgelist(client, 1, depth=2)
        assert (1, 10) in edges
        assert (10, 30) in edges
