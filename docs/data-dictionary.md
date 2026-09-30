# Data dictionary

What each output file and column means. Column names come from Roblox's own
JSON field names, so they use Roblox's spelling (`memberCount`, `isBanned`).
Example values were collected live on 2026-09-28.

## How columns are made

Roblox returns nested JSON. PyRoblox flattens each record into one CSV row:

| Roblox JSON | CSV column | Rule |
|---|---|---|
| `{"owner": {"userId": 21557}}` | `owner_userId` = `21557` | Nested objects are joined with `_`. |
| `{"tags": ["a", "b"]}` | `tags` = `a;b` | Lists of simple values are joined with `;`. |
| `{"roles": [{"id": 1}, {"id": 2}]}` | `roles` = `[{"id": 1}, {"id": 2}]` | Lists of objects are kept as JSON text so nothing is lost. |
| `{"shout": null}` | `shout` = empty | Missing and null values are empty cells. |

Two consequences:

- Column sets can grow. If Roblox adds a field, a new column appears. Code that
  reads these files should select columns by name, not by position.
- Ids are integers and can be up to 16 digits. Spreadsheet programs may show
  them in scientific notation or round them; import id columns as text.

Timestamps are ISO 8601 in UTC. Values pass through typed models before export, so fractional seconds are written with six digits (`2006-06-22T01:33:56.450000Z`) even when Roblox sent fewer; the instant is unchanged. Only fields Roblox actually sent become columns.

## Manifest

Every snapshot and network writes `<entity>_<id>_manifest.json`.

| Key | Meaning |
|---|---|
| `entity` | `user`, `group`, `game`, `friend_network`, or `group_network`. |
| `id` | The user, group, or universe id. |
| `captured_at` | When collection started, UTC. |
| `counts` | Table name to number of rows written. |
| `files` | The file names written beside the manifest. |
| `omitted` | Table name to reason it was not collected: `cookie-required` (Roblox answered 401), `private` (403), `not-found` (404), `invalid` (400, usually a banned user or locked group), `no-root-place` (game has no root place), `error` (anything else; see `errors`). |
| `truncated` | Table name to `true` when a `--max` cap stopped pagination while Roblox still had more rows. |
| `errors` | List of `{table, error, message}` for tables that failed with a Roblox message worth keeping. |
| `depth` | Friend networks only: the `--depth` used. |
| `failed` | Networks only: id to reason for users or groups whose lists could not be fetched (locked group, banned user). |
| `hidden_friends_skipped` | Friend networks only: how many `id: -1` placeholder friends (deleted accounts) were left out of the graph. |
| `root_place_id`, `place_id` | Games only: the universe's root place and, when a place was given, the place id that was resolved. |

## User tables (`roblox user snapshot`, `roblox user <command>`)

### `user_<id>_profile`

One row. Source: `users.roblox.com/v1/users/{id}`.

| Column | Meaning | Example |
|---|---|---|
| `id` | User id. Stable; never changes. | `261` |
| `name` | Current username. Can change. | `Shedletsky` |
| `displayName` | Display name shown in games. | `Shedletsky` |
| `description` | Profile "About" text. | `"He came like the wind..."` |
| `created` | Account creation time. | `2006-06-22T01:33:56.45Z` |
| `isBanned` | Whether Roblox has banned the account. | `False` |
| `hasVerifiedBadge` | Blue verified badge. | `True` |
| `externalAppDisplayName` | Display name from a linked external app, if any. | empty |

### `user_<id>_counts`

One row from the three count endpoints.

| Column | Meaning | Example |
|---|---|---|
| `friends` | Number of friends (max 1000 on Roblox). | `98` |
| `followers` | Number of followers. | `2124380` |
| `followings` | Number of accounts the user follows. | `457735` |

### `user_<id>_friends`

One row per friend. Source: `friends.roblox.com/v1/users/{id}/friends`, with
names filled in from `POST users.roblox.com/v1/users`.

| Column | Meaning | Example |
|---|---|---|
| `id` | Friend's user id. `-1` means a deleted or hidden account. | `4371992339` |
| `name` | Friend's username. Empty for `-1` entries. | `JoeysFault` |
| `displayName` | Friend's display name. | `Joey` |
| `hasVerifiedBadge` | Verified badge. | `False` |

### `user_<id>_followers`, `user_<id>_followings` (cookie)

One row per account with `id`, `name`, `displayName`, `hasVerifiedBadge`, `created`, `description`, `isBanned` as Roblox returns them.

### `user_<id>_groups`

One row per group membership. Source: `groups.roblox.com/v1/users/{id}/groups/roles`.

| Column | Meaning | Example |
|---|---|---|
| `group_id` | Group id. | `3059674` |
| `group_name` | Group name. `[ Content Deleted ]` for removed groups. | `Badimo` |
| `group_description` | Group description. | |
| `group_owner_userId`, `group_owner_username`, `group_owner_displayName`, `group_owner_hasVerifiedBadge` | The group's owner. Empty when the group has no owner. | `2837719`, `asimo3089` |
| `group_shout` | Current group shout, as JSON text if present. | empty |
| `group_memberCount` | Members in the group. | `3489298` |
| `group_isBuildersClubOnly`, `group_publicEntryAllowed`, `group_hasVerifiedBadge`, `group_hasSocialModules` | Group flags. | |
| `role_id`, `role_name`, `role_rank`, `role_color` | The user's role in this group. `role_rank` is 0 to 255; 255 is the owner. | `21008349`, `Member`, `1` |
| `isPrimaryGroup` | `True` for the user's chosen primary group. | empty |

### `user_<id>_games`

One row per experience the user published. Source: `games.roblox.com/v2/users/{id}/games`.

| Column | Meaning | Example |
|---|---|---|
| `id` | Universe id. | `2434560046` |
| `name` | Experience name. | `Crossroads but with a million people` |
| `description` | Description. `[ Content Deleted ]` if moderated. | |
| `creator_id`, `creator_type` | Owner id and `User` or `Group`. | `261`, `User` |
| `rootPlace_id`, `rootPlace_type` | The start place. This is the id in the game's URL. | `6504969480`, `Place` |
| `created`, `updated` | Timestamps. | |
| `placeVisits` | Total visits. | `24754` |

### `user_<id>_favorite_games`

Same columns as `user_<id>_games` (plus `creator_name` and `price`), one row per experience the user favourited, newest first.

### `user_<id>_badges` (cookie)

One row per game badge earned: `id`, `name`, `description`, `displayName`, `enabled`, `iconImageId`, `created`, `updated`, `statistics_*`, `awardingUniverse_id`, `awardingUniverse_name`, `awardingUniverse_rootPlaceId`.

### `user_<id>_username_history`

One row per previous username: `name`. Empty for users who never changed their name.

### `user_<id>_avatar`

One row. Source: `avatar.roblox.com/v1/users/{id}/avatar` without the assets list.

| Column | Meaning | Example |
|---|---|---|
| `playerAvatarType` | `R6` or `R15`. | `R6` |
| `bodyColors_headColorId` and five more `bodyColors_*` | BrickColor ids of each body part. | `24` |
| `scales_height`, `scales_width`, `scales_head`, `scales_depth`, `scales_proportion`, `scales_bodyType` | Avatar scaling. | `1.0` |
| `defaultShirtApplied`, `defaultPantsApplied` | Whether default clothing is shown. | `False` |
| `emotes` | Equipped emotes, as JSON text. | |

### `user_<id>_avatar_assets`

One row per worn item.

| Column | Meaning | Example |
|---|---|---|
| `id` | Asset id. | `1006027` |
| `name` | Item name. | `Got Root?` |
| `assetType_id`, `assetType_name` | Item type. | `2`, `TShirt` |
| `currentVersionId` | Asset version. | `6028` |

### `user_<id>_collectibles`

One row per limited/collectible item owned. Source: `inventory.roblox.com/v1/users/{id}/assets/collectibles`.

| Column | Meaning | Example |
|---|---|---|
| `userAssetId` | This copy's id. | `115160` |
| `assetId`, `name` | The item. | `1082932`, `Traffic Cone` |
| `serialNumber` | Serial for limited-unique items. | empty |
| `recentAveragePrice` | Recent resale price in Robux. | `3387` |
| `originalPrice` | Original sale price. | `80` |
| `assetStock` | Copies in existence. | `163907` |
| `buildersClubMembershipType`, `isOnHold` | Legacy flags. | |

### `user_<id>_roblox_badges`

One row per platform badge (not game badges): `id`, `name`, `description`, `imageUrl`. Examples: `Friendship`, `Homestead`, `Veteran`, `Administrator`.

### `user_<id>_promotion_channels`

One row: `facebook`, `twitter`, `youtube`, `twitch`. All empty without a cookie.

### `user_<id>_presence`

One row. Source: `presence.roblox.com/v1/presence/users`.

| Column | Meaning | Example |
|---|---|---|
| `userPresenceType` | `0` offline, `1` online (website), `2` in a game, `3` in Studio. | `0` |
| `lastLocation` | `Website` or the experience name. | `Website` |
| `placeId`, `rootPlaceId`, `universeId`, `gameId` | Where they are, when in a game. `gameId` is the server instance. | empty |
| `userId` | The user. | `261` |

## Friend network (`roblox user network`)

### `friend_network_<id>_edges`

| Column | Meaning |
|---|---|
| `source`, `target` | User ids. Undirected; each pair appears once with `source < target`. |

### `friend_network_<id>_nodes`

| Column | Meaning | Example |
|---|---|---|
| `id` | User id. | `261` |
| `name`, `displayName`, `hasVerifiedBadge` | From the batch user lookup. | `Shedletsky` |
| `depth` | Hops from the seed user (0 = the seed). | `0` |
| `expanded` | `True` if this user's own friend list was fetched. | `True` |

## Group tables (`roblox group snapshot`, `roblox group <command>`)

### `group_<id>_profile`

One row. Source: `groups.roblox.com/v1/groups/{id}`.

| Column | Meaning | Example |
|---|---|---|
| `id`, `name`, `description` | The group. | `7`, `Roblox` |
| `owner_userId`, `owner_username`, `owner_displayName`, `owner_hasVerifiedBadge` | Owner. Empty if ownerless. | `21557`, `Games` |
| `shout` | Current shout as JSON text (`body`, `poster`, `created`, `updated`). | empty |
| `memberCount` | Members. | `13508013` |
| `isBuildersClubOnly` | Legacy Premium-only flag. | `False` |
| `publicEntryAllowed` | Anyone can join without approval. | `True` |
| `isLocked` | Group is locked by Roblox. Only present when true. | empty |
| `hasVerifiedBadge`, `hasSocialModules` | Flags. | `True` |
| `communityTier_*` | Roblox's community tier fields (`currentTier`, `lastEvaluatedTime`, `requirements` as JSON text). | `3` |

### `group_<id>_roles`

One row per role: `id`, `name`, `rank` (0 to 255), `memberCount`, `color`, `isBase`.

### `group_<id>_members`

One row per member. Source: `groups.roblox.com/v1/groups/{id}/users`.

| Column | Meaning | Example |
|---|---|---|
| `user_userId`, `user_username`, `user_displayName`, `user_hasVerifiedBadge` | The member. Names are present here (unlike friend lists). | `2615839`, `joer234` |
| `role_id`, `role_name`, `role_rank`, `role_color` | Their role. | `200`, `Member`, `1` |

### `group_<id>_allies`, `group_<id>_enemies`

One row per related group with the same columns as `group_<id>_profile`.

### `group_<id>_games`

Same columns as `user_<id>_games`, one row per experience the group publishes.

### `group_<id>_name_history`

One row per previous name: `name`, `created`.

### `group_<id>_social_links` (cookie)

One row per link: `id`, `type` (`Discord`, `Twitter`, `YouTube`, `Twitch`, `Facebook`, `Guilded`, `RobloxGroup`), `url`, `title`.

## Group network (`roblox group network`)

| File | One row per | Columns |
|---|---|---|
| `group_network_<id>_groups` | group seen (seed, allies, enemies, and their allies and enemies) | same as `group_<id>_profile` |
| `group_network_<id>_allies` | ally relationship | `source`, `target` (group ids, directed as Roblox reports them) |
| `group_network_<id>_enemies` | enemy relationship | `source`, `target` |
| `group_network_<id>_membership` | group-member pair | `groupId`, then the `group_<id>_members` columns (`user_userId`, `role_name`, ...) |
| `group_network_<id>_members` | unique user across all groups | `id`, `name`, `displayName`, `hasVerifiedBadge` |
| `group_network_<id>_member_profiles` (`--profiles`) | unique user | same as `user_<id>_profile` |
| `group_network_<id>_favorite_games` (`--favorites`) | user-favourite pair | `userId`, `universeId` |
| `group_network_<id>_games` (`--favorites`) | unique favourited experience | same as `user_<id>_favorite_games` |

## Game tables (`roblox game snapshot`, `roblox game <command>`)

### `game_<universe>_profile`

One row. Source: `games.roblox.com/v1/games?universeIds=`.

| Column | Meaning | Example |
|---|---|---|
| `id` | Universe id. | `13058` |
| `rootPlaceId` | Start place; the id in the game URL. | `1818` |
| `name`, `description` | The experience. | `Crossroads` |
| `creator_id`, `creator_name`, `creator_type`, `creator_hasVerifiedBadge`, `creator_isRNVAccount` | Owner (`User` or `Group`). | `1`, `Roblox`, `User` |
| `playing` | Players online at collection time. | `413` |
| `visits` | Total visits. | `39229329` |
| `maxPlayers` | Server size. | `15` |
| `created`, `updated` | Timestamps. | `2007-05-01T01:07:04.78Z` |
| `genre`, `genre_l1`, `genre_l2` | Genre labels. | `Fighting`, `Action`, `Battlegrounds & Fighting` |
| `favoritedCount` | Favourites. | `316859` |
| `isContentRestricted` | Age-restricted content flag. | `False` |
| `price`, `allowedGearGenres`, `allowedGearCategories`, `isGenreEnforced`, `copyingAllowed`, `studioAccessToApisAllowed`, `createVipServersAllowed`, `universeAvatarType`, `isAllGenre`, `isFavoritedByUser`, `canonicalUrlPath`, `sourceName`, `sourceDescription` | Other settings as Roblox reports them. | |

### `game_<universe>_votes`

One row: `id`, `upVotes`, `downVotes`, `favoritesCount`.

### `game_<universe>_places`

One row per place in the universe: `id`, `universeId`, `name`, `description`.

### `game_<universe>_servers`

One row per public server at collection time. Source: `games.roblox.com/v1/games/{placeId}/servers/Public`.

| Column | Meaning | Example |
|---|---|---|
| `id` | Server instance id. | `a3c69989-...` |
| `maxPlayers`, `playing` | Capacity and current players. | `15`, `2` |
| `playerTokens` | Opaque tokens for avatar thumbnails. Empty without a cookie. | |
| `players` | Player list. Empty without a cookie. | |
| `fps`, `ping` | Server performance. | `59.97`, `53` |

### `game_<universe>_badges`

One row per badge the experience awards.

| Column | Meaning | Example |
|---|---|---|
| `id`, `name`, `description`, `displayName`, `displayDescription` | The badge. | `4036544995812202` |
| `enabled` | Can still be awarded. | `True` |
| `iconImageId`, `displayIconImageId` | Icon asset. | |
| `created`, `updated` | Timestamps. | |
| `statistics_awardedCount` | Total awards ever. | `9163315` |
| `statistics_pastDayAwardedCount` | Awards in the last 24 hours. | `51565` |
| `statistics_winRatePercentage` | Share of players who earn it. | `0.786` |
| `awardingUniverse_id`, `awardingUniverse_name`, `awardingUniverse_rootPlaceId` | The awarding experience. | `13058` |

### `game_<universe>_media`

One row per image or video: `assetTypeId`, `assetType`, `imageId`, `videoHash`, `videoTitle`, `approved`, `altText`.

### `game_<universe>_game_passes`

One row per pass: `id`, `productId`, `name`, `displayName`, `displayDescription`, `isForSale`, `displayIconImageAssetId`, `created`, `updated`.

## Search and batch outputs

| File | Columns |
|---|---|
| `search_users_<keyword>` | `id`, `name`, `displayName`, `hasVerifiedBadge`, `previousUsernames` (`;`-joined) |
| `search_groups_<keyword>` | `id`, `name`, `description`, `memberCount`, `previousName`, `publicEntryAllowed`, `created`, `updated`, `hasVerifiedBadge` |
| `batch_users_<file>` | `id`, `name`, `displayName`, `hasVerifiedBadge`; with `--full`, the `user_<id>_profile` columns plus `error` for refused ids |
| `batch_groups_<file>` | `id`, `name`, `description`, `owner_id`, `owner_type`, `created`, `hasVerifiedBadge` |

## Legacy v1 files (`build_dataframes`)

The Python function `build_dataframes(group_id, cookie)` still writes the seven
v1 files, now with correct contents. Note the v1 column names differ from the
rest of PyRoblox.

| File | Columns | v1 problem, now fixed |
|---|---|---|
| `allies_<id>_edgelist.csv` | `From`, `To` (group ids) | |
| `enemies_<id>_edgelist.csv` | `From`, `To` | |
| `group_info_<id>.csv` | group profile columns for every group in the network | |
| `membership_<id>_edgelist.csv` | `Group`, `User` | Every group had the seed group's members. |
| `user_info_membership_<id>.csv` | user profile columns for every member | Covered only the seed group's members. |
| `asset_el<id>.csv` | `User`, `FavoritedGame` (universe id) | Contained no data. |
| `asset_info_<id>.csv` | favourite game columns | Only the first 50 favourites per user. |

The v1 files no longer carry the unnamed pandas index column.
