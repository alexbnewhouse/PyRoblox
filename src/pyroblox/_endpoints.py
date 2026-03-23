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

# Thumbnails (thumbnails.roblox.com)
USER_AVATAR_THUMBNAILS = "/v1/users/avatar"

# Presence (presence.roblox.com)
USER_PRESENCE = "/v1/presence/users"
