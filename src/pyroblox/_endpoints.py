"""Centralized endpoint path definitions.

When Roblox updates API versions or paths, update them here.
"""

# Groups (groups.roblox.com)
GROUP_INFO = "/v1/groups/{group_id}"
GROUP_ALLIES = "/v1/groups/{group_id}/relationships/Allies"
GROUP_ENEMIES = "/v1/groups/{group_id}/relationships/Enemies"
GROUP_MEMBERS = "/v1/groups/{group_id}/users"
GROUP_SOCIAL_LINKS = "/v1/groups/{group_id}/social-links"
GROUP_ROLES = "/v1/groups/{group_id}/roles"

# Users (users.roblox.com)
USER_INFO = "/v1/users/{user_id}"
USER_SEARCH = "/v1/users/search"
USERS_BATCH = "/v1/users"

# Friends (friends.roblox.com)
USER_FRIENDS = "/v1/users/{user_id}/friends"
USER_FRIEND_COUNT = "/v1/users/{user_id}/friends/count"
USER_FOLLOWERS = "/v1/users/{user_id}/followers"
USER_FOLLOWINGS = "/v1/users/{user_id}/followings"

# Games (games.roblox.com)
GROUP_GAMES = "/v2/groups/{group_id}/games"
USER_GAMES = "/v2/users/{user_id}/games"
USER_FAVORITE_GAMES = "/v2/users/{user_id}/favorite/games"
GAME_INFO = "/v1/games"

# Badges (badges.roblox.com)
BADGE_INFO = "/v1/badges/{badge_id}"
UNIVERSE_BADGES = "/v1/universes/{universe_id}/badges"
USER_BADGES = "/v1/users/{user_id}/badges"
USER_BADGE_AWARDED_DATES = "/v1/users/{user_id}/badges/awarded-dates"

# Inventory (inventory.roblox.com)
USER_COLLECTIBLES = "/v1/users/{user_id}/assets/collectibles"
USER_CAN_VIEW_INVENTORY = "/v1/users/{user_id}/can-view-inventory"
USER_INVENTORY = "/v2/users/{user_id}/inventory/{asset_type_id}"
ASSET_OWNERS = "/v2/assets/{asset_id}/owners"

# Catalog (catalog.roblox.com)
CATALOG_SEARCH = "/v2/search/items/details"
CATALOG_ITEM_DETAILS = "/v1/catalog/items/details"
BUNDLE_DETAILS = "/v1/bundles/{bundle_id}/details"
BUNDLE_DETAILS_BATCH = "/v1/bundles/details"
ASSET_FAVORITE_COUNT = "/v1/favorites/assets/{asset_id}/count"
BUNDLE_FAVORITE_COUNT = "/v1/favorites/bundles/{bundle_id}/count"
BUNDLE_RECOMMENDATIONS = "/v1/bundles/{bundle_id}/recommendations"

# Avatar (avatar.roblox.com)
USER_AVATAR = "/v1/users/{user_id}/avatar"
USER_CURRENTLY_WEARING = "/v1/users/{user_id}/currently-wearing"
USER_OUTFITS = "/v2/avatar/users/{user_id}/outfits"

# Games — additional endpoints
GAME_VOTES = "/v1/games/votes"
GAME_FAVORITES_COUNT = "/v1/games/{universe_id}/favorites/count"
GAME_SERVERS = "/v1/games/{place_id}/servers/{server_type}"
GAME_MEDIA = "/v2/games/{universe_id}/media"

# Thumbnails (thumbnails.roblox.com)
USER_AVATAR_THUMBNAILS = "/v1/users/avatar"
USER_HEADSHOT_THUMBNAILS = "/v1/users/avatar-headshot"
ASSET_THUMBNAILS = "/v1/assets"
GAME_ICON_THUMBNAILS = "/v1/games/icons"
GROUP_ICON_THUMBNAILS = "/v1/groups/icons"
BADGE_ICON_THUMBNAILS = "/v1/badges/icons"
THUMBNAIL_BATCH = "/v1/batch"

# Presence (presence.roblox.com)
USER_PRESENCE = "/v1/presence/users"
