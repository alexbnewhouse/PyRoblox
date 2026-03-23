"""Tests for GroupsAPI resource methods."""

import pytest
from pytest_httpx import HTTPXMock

from pyroblox.client import RobloxClient


def test_get_info(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "id": 5351020,
        "name": "Test Group",
        "description": "desc",
        "owner": {"userId": 1, "username": "owner", "displayName": "Owner", "hasVerifiedBadge": False},
        "memberCount": 100,
        "hasVerifiedBadge": False,
    })
    with RobloxClient() as client:
        group = client.groups.get_info(5351020)
        assert group.id == 5351020
        assert group.name == "Test Group"


def test_get_allies(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "relatedGroups": [
            {"id": 10, "name": "Ally1"},
            {"id": 20, "name": "Ally2"},
        ],
    })
    with RobloxClient() as client:
        allies = client.groups.get_allies(1)
        assert len(allies) == 2
        assert allies[0].id == 10


def test_get_members_pagination(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "data": [
            {"user": {"userId": 1, "username": "u1", "displayName": "U1", "hasVerifiedBadge": False}, "role": {"id": 1, "name": "Member", "rank": 1}},
        ],
        "nextPageCursor": "page2",
        "previousPageCursor": None,
    })
    httpx_mock.add_response(json={
        "data": [
            {"user": {"userId": 2, "username": "u2", "displayName": "U2", "hasVerifiedBadge": False}, "role": {"id": 1, "name": "Member", "rank": 1}},
        ],
        "nextPageCursor": None,
        "previousPageCursor": "page1",
    })
    with RobloxClient() as client:
        members = list(client.groups.get_members(1))
        assert len(members) == 2
        assert members[0].user.user_id == 1
        assert members[1].user.user_id == 2


def test_get_roles(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "roles": [
            {"id": 1, "name": "Guest", "rank": 0, "memberCount": 50},
            {"id": 2, "name": "Member", "rank": 1, "memberCount": 100},
        ],
    })
    with RobloxClient() as client:
        roles = client.groups.get_roles(1)
        assert len(roles) == 2
        assert roles[1].name == "Member"


def test_get_social_links(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "data": [
            {"id": 1, "type": "Discord", "url": "https://discord.gg/test", "title": "Our Discord"},
        ],
    })
    with RobloxClient() as client:
        links = client.groups.get_social_links(1)
        assert len(links) == 1
        assert links[0].type == "Discord"
