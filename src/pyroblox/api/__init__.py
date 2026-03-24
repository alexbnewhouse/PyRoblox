"""API resource classes for each Roblox API domain."""

from pyroblox.api.avatar import AvatarAPI
from pyroblox.api.badges import BadgesAPI
from pyroblox.api.catalog import CatalogAPI
from pyroblox.api.friends import FriendsAPI
from pyroblox.api.games import GamesAPI
from pyroblox.api.groups import GroupsAPI
from pyroblox.api.inventory import InventoryAPI
from pyroblox.api.thumbnails import ThumbnailsAPI
from pyroblox.api.users import UsersAPI

__all__ = [
    "AvatarAPI",
    "BadgesAPI",
    "CatalogAPI",
    "FriendsAPI",
    "GamesAPI",
    "GroupsAPI",
    "InventoryAPI",
    "ThumbnailsAPI",
    "UsersAPI",
]
