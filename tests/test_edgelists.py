"""Tests for the edgelist building utilities."""

import httpx
import pytest
from pytest_httpx import HTTPXMock

from pyroblox.client import RobloxClient
from pyroblox.contrib.edgelists import friend_edgelist, group_edgelist
from pyroblox.exceptions import NotFoundError


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


def test_group_edgelist_hop_failure_is_skipped(httpx_mock: HTTPXMock) -> None:
    """If a 2nd-hop group fetch fails, seed edges should still be collected."""
    # Allies of seed
    httpx_mock.add_response(json={
        "relatedGroups": [{"id": 10, "name": "Ally1"}],
    })
    # Enemies of seed
    httpx_mock.add_response(json={"relatedGroups": []})
    # Allies of ally 10 — fails with 404
    httpx_mock.add_response(
        status_code=404, json={"errors": [{"message": "Not found"}]}
    )
    with RobloxClient() as client:
        result = group_edgelist(client, 1, depth=2)
        # Seed edge should still be present
        assert result["allies"] == [(1, 10)]
        assert result["enemies"] == []


def test_friend_edgelist_hop_failure_is_skipped(httpx_mock: HTTPXMock) -> None:
    """If a friend-of-friend fetch fails, seed edges survive."""
    # Friends of seed
    httpx_mock.add_response(json={
        "data": [{"id": 10, "name": "f1", "displayName": "F1"}],
    })
    # Friends of friend 10 — fails
    httpx_mock.add_response(
        status_code=429, headers={"Retry-After": "0"}
    )
    with RobloxClient(max_retries=0) as client:
        edges = friend_edgelist(client, 1, depth=2)
        assert edges == [(1, 10)]


def test_group_edgelist_no_allies_no_enemies(httpx_mock: HTTPXMock) -> None:
    """Group with no relationships returns empty edgelists."""
    httpx_mock.add_response(json={"relatedGroups": []})
    httpx_mock.add_response(json={"relatedGroups": []})
    with RobloxClient() as client:
        result = group_edgelist(client, 1, depth=1)
        assert result["allies"] == []
        assert result["enemies"] == []
