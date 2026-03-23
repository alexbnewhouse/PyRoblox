"""Tests for Pydantic models — validation and extra-field handling."""

from pyroblox.models.groups import Group, GroupMember, GroupOwner
from pyroblox.models.users import User
from pyroblox.models.friends import Friend
from pyroblox.models.games import Game


def test_group_from_api_response() -> None:
    raw = {
        "id": 5351020,
        "name": "Test Group",
        "description": "A test group",
        "owner": {"userId": 123, "username": "owner", "displayName": "Owner", "hasVerifiedBadge": False},
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


def test_group_member() -> None:
    raw = {
        "user": {"userId": 42, "username": "player1", "displayName": "Player 1", "hasVerifiedBadge": False},
        "role": {"id": 1, "name": "Member", "rank": 1},
    }
    member = GroupMember.model_validate(raw)
    assert member.user.user_id == 42
    assert member.role is not None
    assert member.role.name == "Member"


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


def test_friend_model() -> None:
    raw = {"id": 200, "name": "frienduser", "displayName": "Friend", "isOnline": True}
    friend = Friend.model_validate(raw)
    assert friend.id == 200


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
