"""API resource classes for each Roblox API domain."""

from pyroblox.api.friends import FriendsAPI
from pyroblox.api.games import GamesAPI
from pyroblox.api.groups import GroupsAPI
from pyroblox.api.users import UsersAPI

__all__ = ["FriendsAPI", "GamesAPI", "GroupsAPI", "UsersAPI"]
