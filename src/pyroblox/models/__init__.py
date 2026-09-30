"""Typed models for Roblox API responses (Pydantic v2).

Every API method on :class:`pyroblox.RobloxClient` returns one of these (or a
list / :class:`~pyroblox.client.PagedList` of them). See ``base.py`` for the
shared behaviour: camelCase aliases, extra fields kept, ``to_record()``.
"""

from .account import PromotionChannels, RobloxBadge
from .avatar import Avatar, AvatarAsset, AvatarAssetType, AvatarScales, BodyColors, Outfit
from .badges import AwardingUniverse, Badge, BadgeAwardDate, BadgeStatistics
from .base import PascalModel, RobloxModel, RobloxRecord, to_record, to_records
from .catalog import (
    Bundle,
    BundleCreator,
    CatalogItem,
    EconomyAssetDetails,
    EconomyCreator,
    ResaleData,
)
from .friends import Friend, FriendCounts
from .games import (
    CreatedPlace,
    Game,
    GameCreator,
    GameMedia,
    GamePass,
    GameServer,
    GameVotes,
    Place,
    RootPlace,
)
from .groups import (
    Group,
    GroupMember,
    GroupNameHistoryEntry,
    GroupOwner,
    GroupOwnerRef,
    GroupRole,
    GroupSearchResult,
    GroupShout,
    GroupSummary,
    GroupUser,
    SocialLink,
    UserGroupMembership,
)
from .inventory import AssetOwner, CollectibleAsset, InventoryItem, InventoryOwner
from .presence import LastOnline, UserPresence
from .thumbnails import SavedThumbnail, Thumbnail
from .users import User, UsernameHistoryEntry, UsernameMatch

__all__ = [
    "RobloxModel", "PascalModel", "RobloxRecord", "to_record", "to_records",
    "User", "UsernameMatch", "UsernameHistoryEntry",
    "Friend", "FriendCounts",
    "Group", "GroupSummary", "GroupUser", "GroupOwner", "GroupOwnerRef", "GroupShout", "GroupRole",
    "GroupMember", "SocialLink", "GroupNameHistoryEntry", "UserGroupMembership", "GroupSearchResult",
    "Game", "GameCreator", "RootPlace", "GameVotes", "GameServer", "GamePass", "Place", "GameMedia",
    "CreatedPlace",
    "Badge", "BadgeStatistics", "AwardingUniverse", "BadgeAwardDate",
    "Avatar", "AvatarAsset", "AvatarAssetType", "BodyColors", "AvatarScales", "Outfit",
    "CollectibleAsset", "InventoryItem", "InventoryOwner", "AssetOwner",
    "CatalogItem", "Bundle", "BundleCreator", "EconomyAssetDetails", "EconomyCreator", "ResaleData",
    "RobloxBadge", "PromotionChannels",
    "UserPresence", "LastOnline",
    "Thumbnail", "SavedThumbnail",
]
