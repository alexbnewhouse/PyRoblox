"""Tests for AvatarAPI resource methods."""

from pytest_httpx import HTTPXMock

from pyroblox.client import RobloxClient


def test_get_avatar(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "playerAvatarType": "R15",
        "bodyColors": {
            "headColorId": 1,
            "torsoColorId": 2,
            "rightArmColorId": 3,
            "leftArmColorId": 4,
            "rightLegColorId": 5,
            "leftLegColorId": 6,
        },
        "scales": {
            "height": 1.0,
            "width": 1.0,
            "head": 1.0,
            "depth": 1.0,
        },
        "assets": [
            {"id": 100, "name": "Cool Hat", "assetType": {"id": 8, "name": "Hat"}},
            {"id": 200, "name": "Shirt", "assetType": {"id": 11, "name": "Shirt"}},
        ],
        "defaultShirtApplied": False,
        "defaultPantsApplied": False,
    })
    with RobloxClient() as client:
        avatar = client.avatar.get_avatar(1)
        assert avatar.player_avatar_type == "R15"
        assert avatar.body_colors is not None
        assert avatar.body_colors.head_color_id == 1
        assert avatar.assets is not None
        assert len(avatar.assets) == 2
        assert avatar.assets[0].name == "Cool Hat"


def test_get_currently_wearing(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={"assetIds": [100, 200, 300]})
    with RobloxClient() as client:
        wearing = client.avatar.get_currently_wearing(1)
        assert wearing == [100, 200, 300]


def test_get_currently_wearing_empty(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={"assetIds": []})
    with RobloxClient() as client:
        wearing = client.avatar.get_currently_wearing(1)
        assert wearing == []


def test_get_outfits(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "data": [
            {"id": 1, "name": "Outfit 1", "isEditable": True},
            {"id": 2, "name": "Outfit 2", "isEditable": False},
        ],
        "nextPageToken": None,
    })
    with RobloxClient() as client:
        outfits = list(client.avatar.get_outfits(1))
        assert len(outfits) == 2
        assert outfits[0].name == "Outfit 1"
        assert outfits[1].is_editable is False


def test_get_outfits_pagination_with_next_page_token(
    httpx_mock: HTTPXMock,
) -> None:
    """Verify multi-page outfits using nextPageToken field."""
    httpx_mock.add_response(json={
        "data": [{"id": 1, "name": "Outfit 1"}],
        "nextPageToken": "token_abc",
    })
    httpx_mock.add_response(json={
        "data": [{"id": 2, "name": "Outfit 2"}],
        "nextPageToken": None,
    })
    with RobloxClient() as client:
        outfits = list(client.avatar.get_outfits(1))
        assert len(outfits) == 2
        assert outfits[0].id == 1
        assert outfits[1].id == 2


def test_get_outfits_max_pages(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={
        "data": [{"id": 1, "name": "O1"}],
        "nextPageToken": "more",
    })
    with RobloxClient() as client:
        outfits = list(client.avatar.get_outfits(1, max_pages=1))
        assert len(outfits) == 1
