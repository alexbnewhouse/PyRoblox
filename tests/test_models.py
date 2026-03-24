"""Tests for Pydantic models — validation, edge cases, and extra-field handling."""

import pytest
from pydantic import ValidationError

from pyroblox.models.avatar import Avatar, AvatarAsset, AvatarAssetType
from pyroblox.models.badges import Badge, BadgeAwardDate, BadgeStatistics
from pyroblox.models.catalog import Bundle, BundleCreator, CatalogItem
from pyroblox.models.friends import Friend
from pyroblox.models.games import Game, GameServer, GameVotes
from pyroblox.models.groups import Group, GroupMember, GroupOwner
from pyroblox.models.inventory import AssetOwner, AssetOwnerUser, CollectibleAsset
from pyroblox.models.thumbnails import Thumbnail
from pyroblox.models.users import User


# --- Groups ---


def test_group_from_api_response() -> None:
    raw = {
        "id": 5351020,
        "name": "Test Group",
        "description": "A test group",
        "owner": {
            "userId": 123,
            "username": "owner",
            "displayName": "Owner",
            "hasVerifiedBadge": False,
        },
        "shout": None,
        "memberCount": 500,
        "isBuildersClubOnly": False,
        "publicEntryAllowed": True,
        "hasVerifiedBadge": False,
    }
    group = Group.model_validate(raw)
    assert group.id == 5351020
    assert group.name == "Test Group"
    assert group.owner is not None
    assert group.owner.user_id == 123
    assert group.member_count == 500


def test_group_extra_fields_allowed() -> None:
    """New fields from Roblox API should not break validation."""
    raw = {
        "id": 1,
        "name": "G",
        "someNewField": True,
        "anotherField": {"nested": "data"},
    }
    group = Group.model_validate(raw)
    assert group.id == 1
    assert group.model_extra is not None
    assert group.model_extra["someNewField"] is True


def test_group_missing_optional_fields() -> None:
    """Minimal response with only required fields should work."""
    raw = {"id": 1, "name": "MinimalGroup"}
    group = Group.model_validate(raw)
    assert group.owner is None
    assert group.member_count is None
    assert group.description is None


def test_group_missing_required_field() -> None:
    """Missing required 'name' field should raise ValidationError."""
    with pytest.raises(ValidationError):
        Group.model_validate({"id": 1})


def test_group_member() -> None:
    raw = {
        "user": {
            "userId": 42,
            "username": "player1",
            "displayName": "Player 1",
            "hasVerifiedBadge": False,
        },
        "role": {"id": 1, "name": "Member", "rank": 1},
    }
    member = GroupMember.model_validate(raw)
    assert member.user.user_id == 42
    assert member.role is not None
    assert member.role.name == "Member"


def test_group_member_no_role() -> None:
    """Member without role should have role=None."""
    raw = {"user": {"userId": 1, "username": "x", "displayName": "X"}}
    member = GroupMember.model_validate(raw)
    assert member.role is None


# --- Users ---


def test_user_model() -> None:
    raw = {
        "id": 100,
        "name": "testuser",
        "displayName": "Test User",
        "description": "Hello",
        "created": "2020-01-01T00:00:00Z",
        "isBanned": False,
        "hasVerifiedBadge": True,
    }
    user = User.model_validate(raw)
    assert user.id == 100
    assert user.has_verified_badge is True
    assert user.created is not None


def test_user_minimal() -> None:
    raw = {"id": 1, "name": "x"}
    user = User.model_validate(raw)
    assert user.display_name is None
    assert user.is_banned is None
    assert user.created is None


# --- Friends ---


def test_friend_model() -> None:
    raw = {"id": 200, "name": "frienduser", "displayName": "Friend", "isOnline": True}
    friend = Friend.model_validate(raw)
    assert friend.id == 200
    assert friend.is_online is True


# --- Games ---


def test_game_model() -> None:
    raw = {
        "id": 300,
        "name": "Cool Game",
        "description": "A game",
        "creator": {"id": 1, "name": "dev", "type": "User"},
        "placeVisits": 1000000,
    }
    game = Game.model_validate(raw)
    assert game.id == 300
    assert game.creator is not None
    assert game.creator.id == 1
    assert game.place_visits == 1000000


def test_game_votes_model() -> None:
    raw = {"id": 100, "upVotes": 5000, "downVotes": 200}
    votes = GameVotes.model_validate(raw)
    assert votes.up_votes == 5000
    assert votes.down_votes == 200


def test_game_server_model() -> None:
    raw = {"id": "abc", "maxPlayers": 50, "playing": 30, "fps": 59.9, "ping": 80}
    server = GameServer.model_validate(raw)
    assert server.playing == 30
    assert server.fps == 59.9


# --- Badges ---


def test_badge_model() -> None:
    raw = {
        "id": 1,
        "name": "Welcome",
        "statistics": {
            "pastDayAwardedCount": 10,
            "awardedCount": 5000,
            "winRatePercentage": 50.0,
        },
    }
    badge = Badge.model_validate(raw)
    assert badge.name == "Welcome"
    assert badge.statistics is not None
    assert badge.statistics.awarded_count == 5000


def test_badge_without_statistics() -> None:
    raw = {"id": 1, "name": "NoStats"}
    badge = Badge.model_validate(raw)
    assert badge.statistics is None


def test_badge_award_date() -> None:
    raw = {"badgeId": 42, "awardedDate": "2023-01-01T00:00:00Z"}
    award = BadgeAwardDate.model_validate(raw)
    assert award.badge_id == 42
    assert award.awarded_date is not None


# --- Inventory ---


def test_collectible_asset_model() -> None:
    raw = {
        "userAssetId": 1,
        "assetId": 100,
        "name": "Rare Item",
        "recentAveragePrice": 5000,
        "buildersClubMemberOnly": True,
    }
    item = CollectibleAsset.model_validate(raw)
    assert item.asset_id == 100
    assert item.recent_average_price == 5000
    assert item.builders_club_member_only is True


def test_asset_owner_with_nested_user() -> None:
    raw = {
        "id": 1,
        "serialNumber": 42,
        "owner": {"id": 100, "type": "User", "name": "Player"},
    }
    owner = AssetOwner.model_validate(raw)
    assert owner.owner is not None
    assert owner.owner.id == 100
    assert owner.owner.name == "Player"


def test_asset_owner_null_owner() -> None:
    """Some assets have hidden owners (null)."""
    raw = {"id": 1, "serialNumber": 1, "owner": None}
    owner = AssetOwner.model_validate(raw)
    assert owner.owner is None


# --- Catalog ---


def test_catalog_item_model() -> None:
    raw = {
        "id": 1,
        "name": "Hat",
        "itemType": "Asset",
        "price": 100,
        "creatorName": "Roblox",
        "favoriteCount": 500,
    }
    item = CatalogItem.model_validate(raw)
    assert item.price == 100
    assert item.creator_name == "Roblox"
    assert item.favorite_count == 500


def test_bundle_with_nested_models() -> None:
    raw = {
        "id": 1,
        "name": "Bundle",
        "items": [{"id": 10, "name": "Item", "type": "Asset"}],
        "creator": {"id": 1, "name": "Roblox", "type": "User"},
        "product": {"id": 1, "isForSale": True, "priceInRobux": 200},
    }
    bundle = Bundle.model_validate(raw)
    assert bundle.items is not None
    assert len(bundle.items) == 1
    assert bundle.creator is not None
    assert bundle.creator.name == "Roblox"
    assert bundle.product is not None
    assert bundle.product.price_in_robux == 200


# --- Avatar ---


def test_avatar_model() -> None:
    raw = {
        "playerAvatarType": "R15",
        "bodyColors": {"headColorId": 1, "torsoColorId": 2},
        "scales": {"height": 1.0, "width": 1.0},
        "assets": [
            {"id": 100, "name": "Hat", "assetType": {"id": 8, "name": "Hat"}},
        ],
    }
    avatar = Avatar.model_validate(raw)
    assert avatar.player_avatar_type == "R15"
    assert avatar.assets is not None
    assert avatar.assets[0].asset_type is not None
    assert avatar.assets[0].asset_type.id == 8


def test_avatar_empty_assets() -> None:
    raw = {"playerAvatarType": "R6", "assets": []}
    avatar = Avatar.model_validate(raw)
    assert avatar.assets == []


# --- Thumbnails ---


def test_thumbnail_model() -> None:
    raw = {
        "targetId": 1,
        "state": "Completed",
        "imageUrl": "https://example.com/img.png",
    }
    thumb = Thumbnail.model_validate(raw)
    assert thumb.target_id == 1
    assert thumb.image_url == "https://example.com/img.png"


def test_thumbnail_pending_state() -> None:
    """Pending thumbnails have no imageUrl."""
    raw = {"targetId": 1, "state": "Pending", "imageUrl": None}
    thumb = Thumbnail.model_validate(raw)
    assert thumb.state == "Pending"
    assert thumb.image_url is None
