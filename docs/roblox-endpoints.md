# Roblox endpoints used by PyRoblox

Every figure on this page was verified live on 2026-09-28 from a single unauthenticated IP address, one request per second with a browser `User-Agent`. Rate limits are per IP address and per endpoint, and are copied from the `x-ratelimit-limit` header Roblox returns on each response: `30 / 60 s` means thirty requests in a sixty second window, and `1000 / 1 s` means a thousand per second. Supplying a `.ROBLOSECURITY` cookie unlocks some endpoints and changes some limits; those cases are marked. Roblox changes hosts, fields and limits without notice, so treat this page as a snapshot. Run `roblox check` before a large collection to re-verify connectivity, the current limits and your cookie.

Column key:

- **PyRoblox call**: the v2 method that wraps the endpoint. Blank means v2 deliberately does not wrap it.
- **Cookie needed?**: `No`, `Yes` (401 or 403 without one), or `Yes, else values null` (200 without one, but the interesting fields are blank).
- **Rate limit (unauth)**: from the header. `not captured` means the endpoint was not called, or Roblox sent no header.
- **Pagination**: `none`, `cursor` (`nextPageCursor`; `limit` must be 10, 25, 50 or 100 unless noted), `rows` (`model.startRowIndex` / `nextRowIndex`), or `page` (`page` and `itemsPerPage`).

## users.roblox.com

| Endpoint | PyRoblox call | Cookie needed? | Rate limit (unauth) | Pagination | Notable fields | Notes |
|---|---|---|---|---|---|---|
| `GET /v1/users/{userId}` | `client.users.get_info(id)` | No | 30 / 60 s | none | id, name, displayName, description, created, isBanned, hasVerifiedBadge, externalAppDisplayName | Works for banned accounts (`isBanned: true`). A non-existent id returns 404 "The user id is invalid." Slow for bulk work; use the POST below for names. |
| `POST /v1/users` (body `userIds`, `excludeBannedUsers`) | `client.users.get_batch(ids)` | No | 1000 / 1 s | none; PyRoblox sends 100 ids per call | id, name, displayName, hasVerifiedBadge | The way to turn the id-only friends list into names. No description or created date. |
| `POST /v1/usernames/users` (body `usernames`) | `client.users.get_by_usernames(names)`, `client.users.resolve(name)` | No | 500 / 60 s | none; 100 names per call | requestedUsername, id, name, displayName, hasVerifiedBadge | |
| `GET /v1/users/{userId}/username-history` | `client.users.get_username_history(id)` | No | 1 / 60 s | cursor | name | A second call inside the minute returned 429 with `retry-after: 5`. |
| `GET /v1/users/search?keyword=` | `client.users.search(keyword)` | No | 1 / 60 s | cursor | id, name, displayName, hasVerifiedBadge, previousUsernames[] | `previousUsernames` gives name changes without spending a username-history call. One probe returned 200 with empty `data` while throttled. |
| `GET /v1/users/authenticated` | `client.users.get_authenticated()` | Yes | 100 / 60 s | none | id, name, displayName | 401 code 9002 without a cookie. Used to validate the cookie. |
| `GET /v2/users/{userId}` | | | not captured | | | 404. There is no v2 user lookup. |

## friends.roblox.com

| Endpoint | PyRoblox call | Cookie needed? | Rate limit (unauth) | Pagination | Notable fields | Notes |
|---|---|---|---|---|---|---|
| `GET /v1/users/{userId}/friends` | `client.friends.get_friends(id)`, `client.friends.get_friend_ids(id)` | Yes, else values null (ids are returned; `name` and `displayName` are empty strings) | 20 / 60 s | none; the whole list comes back in one response | id, name, displayName | 98 entries for user 261, matching `friends/count`, so the id list is complete. Deleted or hidden friends appear as `id: -1` with empty names. Resolve names with `client.users.batch_get`. |
| `GET /v1/users/{userId}/friends/count` | `client.friends.get_friend_count(id)` | No | 100 / 60 s | none | count | |
| `GET /v1/users/{userId}/friends/find` | | No | 100 / 60 s | cursor (`PageItems`, `PreviousCursor`; a different envelope) | id | Ids only, same as the list above. Not wrapped. |
| `GET /v1/users/{userId}/followers` | `client.friends.get_followers(id)` | Yes | 10000 / 60 s | cursor | | 401 without a cookie. |
| `GET /v1/users/{userId}/followers/count` | `client.friends.get_follower_count(id)` | No | 100 / 60 s | none | count | |
| `GET /v1/users/{userId}/followings` | `client.friends.get_followings(id)` | Yes | 10000 / 60 s | cursor | | 401 without a cookie. |
| `GET /v1/users/{userId}/followings/count` | `client.friends.get_following_count(id)` | No | 100 / 60 s | none | count | `client.friends.get_counts(id)` returns all three counts in one dict. |

The documented `friends/online`, `friends/inactive` and `friends/search` endpoints are marked authenticated-only in Roblox's reference and were not probed.

## groups.roblox.com

| Endpoint | PyRoblox call | Cookie needed? | Rate limit (unauth) | Pagination | Notable fields | Notes |
|---|---|---|---|---|---|---|
| `GET /v1/groups/{groupId}` | `client.groups.get_info(id)` | No | 7 / 60 s | none | id, name, description, owner{userId, username, displayName}, shout, memberCount, publicEntryAllowed, isLocked, hasVerifiedBadge, communityTier | The tightest useful limit on the platform. v2 uses it only for the seed group. `isLocked` appeared only on the locked group in the probe. |
| `GET /v2/groups?groupIds=1,2,3` | `client.groups.get_batch(ids)` | No | 1 / 1 s | none; PyRoblox sends 100 ids per call | id, name, description, owner{id, type}, created, hasVerifiedBadge | No memberCount or shout. Use this for every group after the seed. |
| `GET /v1/groups/{groupId}/users` | `client.groups.get_members(id)` | No | 1200 / 60 s | cursor | user{userId, username, displayName, hasVerifiedBadge}, role{id, name, rank} | Names are populated here, unlike the friends list. |
| `GET /v1/groups/{groupId}/roles` | `client.groups.get_roles(id)` | No | 800 / 60 s | none | roles[]{id, name, rank, memberCount} | |
| `GET /v1/groups/{groupId}/roles/{roleSetId}/users` | `client.groups.get_role_members(id, role_id)` | No | 10000 / 60 s | cursor | userId, username, displayName, hasVerifiedBadge | |
| `GET /v1/groups/{groupId}/relationships/allies` (and `/enemies`) with `model.startRowIndex`, `model.maxRows` | `client.groups.get_allies(id)`, `client.groups.get_enemies(id)` | No | 500 / 60 s | rows (100 per page) | groupId, relationshipType, totalGroupCount, relatedGroups[] (full group objects with memberCount), nextRowIndex | A locked group returns 400 "Group is invalid or does not exist." |
| `GET /v1/groups/{groupId}/social-links` | `client.groups.get_social_links(id)` | Yes | 600 / 60 s | none | data[]{id, type, url, title} | 401 without a cookie. |
| `GET /v1/groups/{groupId}/name-history` | `client.groups.get_name_history(id)` | No | 100 / 60 s | cursor | name, created | 400 for a locked group. Empty for groups 1 and 7. |
| `GET /v1/users/{userId}/groups/roles` | `client.groups.get_user_groups(user_id)` | No | 400 / 60 s | none | group{full object incl. memberCount}, role{id, name, rank}, isPrimaryGroup | Deleted groups appear as "[ Content Deleted ]". |
| `GET /v2/users/{userId}/groups/roles` | | No | 500 / 60 s | none | group{id, name, memberCount, hasVerifiedBadge}, role{id, name, rank} | Slimmer than v1; v2 wraps v1 for the fuller group object. |
| `GET /v1/users/{userId}/groups/primary/role` | `client.groups.get_user_primary_group(user_id)` | No | 1000 / 60 s | none | group, role | The PyRoblox method returns `None` when Roblox sends an empty body. |
| `GET /v1/groups/search?keyword=` | `client.groups.search(keyword)` | No | 300 / 60 s | cursor, plus totalResults | id, name, description, memberCount, previousName, publicEntryAllowed, created, updated, hasVerifiedBadge | |
| `GET /v1/groups/search/lookup?groupName=` | `client.groups.lookup(name)` | No | 500 / 60 s | none | id, name, memberCount, hasVerifiedBadge | Exact match first. |
| `GET /v1/groups/{groupId}/roles/guest/permissions` | `client.groups.get_guest_permissions(id)` | No | 30 / 60 s | none | permissions{groupPostsPermissions, groupMembershipPermissions, groupManagementPermissions, ...} | |
| `GET /v1/groups/{groupId}/wall/posts` | | | 7 / 60 s (shares the single-group bucket) | | | 404 "NotFound" for a locked group and for the public group 7. Dead. |
| `GET /v2/groups/{groupId}/relationships/{type}` | | | not captured | | | 404 when probed as `/v2/groups/7/relationships/Allies?maxRows=100`. Use the v1 path. |

## games.roblox.com, apis.roblox.com, develop.roblox.com

| Endpoint | PyRoblox call | Cookie needed? | Rate limit (unauth) | Pagination | Notable fields | Notes |
|---|---|---|---|---|---|---|
| `GET games.roblox.com/v1/games?universeIds=` | `client.games.get_info(universe_id)`, `client.games.get_batch(ids)` | No | 300 / 60 s | none; 100 ids per call | id, rootPlaceId, name, description, creator{id, name, type, hasVerifiedBadge}, playing, visits, maxPlayers, created, updated, genre, genre_l1, genre_l2, favoritedCount, isContentRestricted | Takes universe ids. A roblox.com/games/ URL carries a place id; convert first. |
| `GET apis.roblox.com/universes/v1/places/{placeId}/universe` | `client.games.get_universe_id(place_id)`, `client.games.get_info_by_place(place_id)` | No | 60 / 60 s | none | universeId | Place 1818 (Crossroads) is universe 13058; universe 1818 is an unrelated place. |
| `GET games.roblox.com/v2/users/{userId}/games` | `client.games.get_user_games(user_id)` | No | 200 / 60 s | cursor; `limit` max 50 | id, name, description, creator{id, type}, rootPlace{id, type}, created, updated, placeVisits | `limit=100` returns 400 "Allowed values: 10, 25, 50". |
| `GET games.roblox.com/v2/groups/{groupId}/gamesV2` (and `/games`) | `client.games.get_group_games(group_id)` | No | 3 / 1 s | cursor | same shape as user games | Both paths returned 200. |
| `GET games.roblox.com/v2/users/{userId}/favorite/games` | `client.games.get_user_favorites(user_id)` | No | 200 / 60 s | cursor | id, name, description, creator{id, type, name}, rootPlace{id}, created, updated, placeVisits, price | Rejects `sortOrder=Asc` with 400 "Ascending sort order is not supported"; PyRoblox sends no sort order and gets newest first. This is what the v1 `asset_el` file was meant to contain. |
| `GET games.roblox.com/v1/games/{placeId}/servers/Public` | `client.games.get_servers(place_id)` | No | 3 / 60 s | cursor | id, maxPlayers, playing, playerTokens[], players[], fps, ping | Takes a place id; a universe id returns 400 "The place is invalid." `players` was empty in the probe. |
| `GET games.roblox.com/v1/games/votes?universeIds=` | `client.games.get_votes(id)`, `client.games.get_votes_batch(ids)` | No | 200 / 60 s | none; 100 ids per call | id, upVotes, downVotes | |
| `GET games.roblox.com/v1/games/{universeId}/favorites/count` | `client.games.get_favorites_count(id)` | No | 200 / 60 s | none | favoritesCount | |
| `GET games.roblox.com/v2/games/{universeId}/media` | `client.games.get_media(id)` | No | 200 / 60 s | none | assetTypeId, assetType, imageId, videoHash, videoTitle, approved, altText | |
| `GET apis.roblox.com/game-passes/v1/universes/{universeId}/game-passes` | `client.games.get_game_passes(id)` | No | 50 / 1 s | none observed with `limit=100` | gamePasses[]{id, productId, name, isForSale, displayName, displayDescription, displayIconImageAssetId, created, updated} | Replaces the dead games.roblox.com path. |
| `GET develop.roblox.com/v1/universes/{universeId}/places` | `client.games.get_places(universe_id)` | No | 10000 / 60 s | cursor | id, universeId, name, description | |
| `GET inventory.roblox.com/v1/users/{userId}/places/inventory?placesTab=Created` | `client.games.get_user_created_places(user_id)` | No | 1000 / 60 s | cursor (numeric cursor values) | universeId, placeId, name, creator{id, name, type}, priceInRobux | |
| `GET games.roblox.com/v1/games/multiget-place-details?placeIds=` | `client.games.get_place_details(ids)` | Yes | 1000 / 60 s | none; 100 ids per call | | 401 without a cookie. |
| `GET develop.roblox.com/v1/groups/{groupId}/universes` | | Yes | 1000 / 60 s | | | 403 "You are not authorized for access." Use `gamesV2` above instead. |
| `GET games.roblox.com/v1/games/{universeId}/game-passes` | | | not captured (no headers sent) | | | 404. Dead. |

## badges.roblox.com

| Endpoint | PyRoblox call | Cookie needed? | Rate limit (unauth) | Pagination | Notable fields | Notes |
|---|---|---|---|---|---|---|
| `GET /v1/users/{userId}/badges` | `client.badges.get_user_badges(user_id)` | Yes | 1000 / 60 s | cursor | | 401 without a cookie. This was public when v1 was written. |
| `GET /v1/users/{userId}/badges/awarded-dates?badgeIds=` | `client.badges.get_awarded_dates(user_id, badge_ids)` | Yes | 10 / 60 s | none; 100 ids per call | badgeId, awardedDate | 403 "Request Context Failure" without a cookie. |
| `GET /v1/universes/{universeId}/badges` | `client.badges.get_universe_badges(id)` | No | 100 / 60 s | cursor | id, name, description, enabled, iconImageId, created, updated, statistics{pastDayAwardedCount, awardedCount, winRatePercentage}, awardingUniverse{id, name, rootPlaceId} | |
| `GET /v1/badges/{badgeId}` | `client.badges.get_info(id)` | No | 600 / 60 s | none | same as above | |

## inventory.roblox.com, catalog.roblox.com, economy.roblox.com

| Endpoint | PyRoblox call | Cookie needed? | Rate limit (unauth) | Pagination | Notable fields | Notes |
|---|---|---|---|---|---|---|
| `GET inventory.roblox.com/v1/users/{userId}/can-view-inventory` | `client.inventory.can_view(id)` | No | 1 / 60 s | none | canView | One call per minute; v2 skips it and lets the inventory call itself report 403. |
| `GET inventory.roblox.com/v1/users/{userId}/assets/collectibles` | `client.inventory.get_collectibles(id)` | No | 60 / 60 s | cursor | userAssetId, serialNumber, assetId, name, recentAveragePrice, originalPrice, assetStock, isOnHold | |
| `GET inventory.roblox.com/v2/users/{userId}/inventory/{assetTypeId}` | `client.inventory.get_user_inventory(id, asset_type_id)` | No; 403 if the inventory is private | 50 / 60 s | cursor | userAssetId, assetId, assetName, collectibleItemId, serialNumber, owner{userId, username}, created, updated | Asset type ids are in `pyroblox.avatar.ASSET_TYPES` (for example hat = 8, shirt = 11, pants = 12). |
| `GET inventory.roblox.com/v2/assets/{assetId}/owners` | `client.inventory.get_asset_owners(asset_id)` | Yes, else values null (`owner` is null) | 15 / 60 s | cursor | id, collectibleItemInstanceId, serialNumber, owner, created, updated | |
| `GET catalog.roblox.com/v1/favorites/users/{userId}/favorites/{assetTypeId}/assets` | `client.inventory.get_favorite_assets(id, asset_type_id)` | No | 10 / 60 s | cursor | id, itemType, assetType, name, description, creatorType, creatorTargetId, creatorName, price, lowestPrice, favoriteCount, itemRestrictions, collectibleItemId, totalQuantity, isOffSale | |
| `GET catalog.roblox.com/v1/users/{userId}/bundles` | `client.inventory.get_bundles(id)` | No | 10 / 60 s | cursor | id, name, bundleType, creator{id, name, type, hasVerifiedBadge} | |
| `GET economy.roblox.com/v2/assets/{assetId}/details` | `client.catalog.get_economy_details(asset_id)` | No | 1000 / 60 s | none | PascalCase: AssetId, ProductId, Name, Description, AssetTypeId, Creator{Id, Name, CreatorType, CreatorTargetId}, Created, Updated, PriceInRobux, Sales, IsForSale, IsLimited, IsLimitedUnique, Remaining, CollectibleItemId, CollectiblesItemDetails | Works for place ids too (AssetTypeId 9). For a group-owned asset `Creator.Id` is not a user id; `CreatorTargetId` is the group id. |
| `POST catalog.roblox.com/v1/catalog/items/details` (body `items[]{itemType, id}`) | `client.catalog.get_item_details(items)`, `client.catalog.get_asset_item_details(ids)` | No | not captured (no headers on either response) | none; 100 items per call | id, itemType, assetType, name, productId, creatorType, creatorTargetId, creatorName, price, lowestResalePrice, favoriteCount, totalQuantity, itemRestrictions, isOffSale, taxonomy | The first call returns 403 "XSRF token invalid" with an `x-csrf-token` header; the retry with that header returns 200. PyRoblox handles this. |
| `GET catalog.roblox.com/v1/assets/{assetId}/bundles` | `client.catalog.get_asset_bundles(asset_id)` | | not captured | cursor | | Not probed. |
| `GET catalog.roblox.com/v1/bundles/{bundleId}/details` | `client.catalog.get_bundle(id)` | | not captured | none | | Not probed. |
| `GET economy.roblox.com/v1/assets/{assetId}/resale-data` | `client.catalog.get_resale_data(id)` | | not captured | none | | Not probed. |
| `GET develop.roblox.com/v1/assets?assetIds=` | | Yes | 100 / 60 s | | | 401 without a cookie. Not wrapped; the economy endpoint covers the same ground. |

## avatar.roblox.com

| Endpoint | PyRoblox call | Cookie needed? | Rate limit (unauth) | Pagination | Notable fields | Notes |
|---|---|---|---|---|---|---|
| `GET /v1/users/{userId}/avatar` | `client.avatar.get_avatar(id)` | No | 40 / 60 s | none | playerAvatarType, bodyColors, scales, assets[]{id, name, assetType{id, name}, currentVersionId} | Includes names and types of every worn item. |
| `GET /v1/users/{userId}/currently-wearing` | `client.avatar.get_currently_wearing(id)` | No | 6 / 60 s | none | assetIds[] | Same ids as `assets` above with no names, at a much tighter limit. Prefer `/avatar`. |
| `GET /v1/users/{userId}/outfits` | `client.avatar.get_outfits(id)` | | not captured | page | | Not probed. |

## accountinformation.roblox.com

| Endpoint | PyRoblox call | Cookie needed? | Rate limit (unauth) | Pagination | Notable fields | Notes |
|---|---|---|---|---|---|---|
| `GET /v1/users/{userId}/roblox-badges` | `client.account.get_roblox_badges(id)` | No | 3000 / 60 s | none | a bare array: id, name, description, imageUrl | Legacy platform badges (Friendship, Homestead, ...). |
| `GET /v1/users/{userId}/promotion-channels` | `client.account.get_promotion_channels(id)` | Yes, else values null | 1000 / 60 s | none | facebook, twitter, youtube, twitch | 200 without a cookie but all four values were null for six users, including two large creators. An id that is not a user returns 400 "User not found." |

## presence.roblox.com

| Endpoint | PyRoblox call | Cookie needed? | Rate limit (unauth) | Pagination | Notable fields | Notes |
|---|---|---|---|---|---|---|
| `POST /v1/presence/users` (body `userIds`) | `client.presence.get_presence(ids)` | No | 60 / 60 s | none; 100 ids per call | userPresences[]{userPresenceType, lastLocation, placeId, rootPlaceId, gameId, universeId, userId} | Both probed users returned `userPresenceType: 0` and `lastLocation: "Website"`. |
| `POST /v1/presence/last-online` (body `userIds`) | `client.presence.get_last_online(ids)` | | not captured | none; 100 ids per call | | Not probed. |

## thumbnails.roblox.com

All thumbnail endpoints take a comma-separated id list plus `size` and `format`, and return `data[]{targetId, state, imageUrl, version}`. The image itself is on `tr.rbxcdn.com`; `client.thumbnails.download(url)` and `client.thumbnails.save(kind, ids, out_dir)` fetch it, and the cookie is never sent to that host.

| Endpoint | PyRoblox call | Cookie needed? | Rate limit (unauth) | Pagination | Notable fields | Notes |
|---|---|---|---|---|---|---|
| `GET /v1/users/avatar-headshot?userIds=` | `client.thumbnails.get_user_headshots(ids)`, `client.thumbnails.get_thumbnails("user-headshot", ids)` | No | 120 / 60 s | none; 100 ids per call | targetId, state, imageUrl | `state` is "Completed" when the URL is ready. |
| `GET /v1/groups/icons?groupIds=` | `client.thumbnails.get_group_icons(ids)` | No | 100 / 60 s | none; 100 ids per call | targetId, state, imageUrl | |
| `GET /v1/games/icons?universeIds=` | `client.thumbnails.get_game_icons(ids)` | No | 1200 / 60 s | none; 100 ids per call | targetId, state, imageUrl | |
| `GET /v1/users/avatar`, `/v1/users/avatar-bust`, `/v1/games/multiget/thumbnails`, `/v1/places/gameicons`, `/v1/assets`, `/v1/badges/icons`, `/v1/bundles/thumbnails` | `client.thumbnails.get_thumbnails(kind, ids)` with kind `user-avatar`, `user-bust`, `game-thumbnail`, `place-icon`, `asset`, `badge-icon`, `bundle` | | not captured | none; 100 ids per call | | Not probed. Roblox's reference marks `/v1/assets`, `/v1/games/icons` and `/v1/places/gameicons` as able to return 403 for some ids. |

## Dead or changed endpoints

- **`api.roblox.com`** (any path): the hostname has no DNS A record; curl reports "Could not resolve host". Code that used `api.roblox.com/users/{id}` or `api.roblox.com/users/get-by-username` fails before an HTTP request is sent. Use `users.roblox.com`.
- **`GET games.roblox.com/v1/games/{universeId}/game-passes`**: 404. Use `GET apis.roblox.com/game-passes/v1/universes/{universeId}/game-passes` (200, top-level key `gamePasses`, 50 / 1 s).
- **`GET groups.roblox.com/v1/groups/{groupId}/wall/posts`**: 404 "NotFound" for both a locked group and the public group 7. Not wrapped in v2.
- **`GET users.roblox.com/v2/users/{userId}`**: 404. There is no v2 of the single-user lookup; v1 is current.
- **`GET groups.roblox.com/v2/groups/{groupId}/relationships/{type}`**: documented, but the form probed (`/v2/groups/7/relationships/Allies?maxRows=100`) returned 404 with no rate-limit headers. The v1 path with `model.startRowIndex` and `model.maxRows` works.
- **`GET develop.roblox.com/v1/groups/{groupId}/universes`**: 403 without a cookie. `games.roblox.com/v2/groups/{groupId}/gamesV2` gives the same list unauthenticated.
- **Documentation URLs**: every `<domain>.roblox.com/docs/json/<Service>?group=v1` swagger URL returns 404. `users.roblox.com/docs` redirects to `https://create.roblox.com/docs/cloud/reference/domains/users`. `groups.roblox.com/docs/index.html` redirected to the groups reference page, which returned 502 at probe time. `https://create.roblox.com/docs/cloud/legacy` redirects to the hub.

## Endpoints that need a cookie

These return 401 or 403 without a `.ROBLOSECURITY` cookie:

- `GET users.roblox.com/v1/users/authenticated`
- `GET friends.roblox.com/v1/users/{userId}/followers` and `/followings` (the `/count` variants do not need one)
- `GET groups.roblox.com/v1/groups/{groupId}/social-links`
- `GET games.roblox.com/v1/games/multiget-place-details`
- `GET badges.roblox.com/v1/users/{userId}/badges` and `/badges/awarded-dates`
- `GET develop.roblox.com/v1/assets` and `/v1/groups/{groupId}/universes`

These return 200 without a cookie but with the useful values blanked:

- `GET friends.roblox.com/v1/users/{userId}/friends`: `name` and `displayName` are empty strings (ids are complete).
- `GET accountinformation.roblox.com/v1/users/{userId}/promotion-channels`: every channel is null.
- `GET inventory.roblox.com/v2/assets/{assetId}/owners`: `owner` is null.

To get the cookie, log in to roblox.com in a browser, open the developer tools (F12), go to the Application tab in Chrome or the Storage tab in Firefox, expand Cookies, select `https://www.roblox.com`, and copy the value of the cookie named `.ROBLOSECURITY`. It begins with a `_|WARNING:-DO-NOT-SHARE-THIS.` banner, and that banner is accurate: the cookie grants full access to the account, including purchases and account settings, for as long as it is valid. Store it in a file that only you can read (`chmod 600` on macOS and Linux), point PyRoblox at it with `--cookie-file` or `ROBLOX_COOKIE_FILE`, never paste it into a script or a shared document, and never commit it. Use a dedicated research account rather than a personal one. PyRoblox attaches the cookie only to requests for `roblox.com` and `*.roblox.com` hosts; image downloads from `rbxcdn.com` never carry it.

## Tips for large collections

- **Use the batch endpoints instead of per-id GETs.** `POST users.roblox.com/v1/users` accepts 100 ids per call at 1000 calls per second, so in principle 100,000 user names cost about a second of API time; the per-user `GET /v1/users/{id}` allows 30 per minute. `GET groups.roblox.com/v2/groups` accepts 100 ids per call at 1 call per second, so 6,000 groups per minute against 7 per minute for `GET /v1/groups/{id}`. `client.users.batch_get`, `client.groups.batch_get`, `client.games.batch_get`, `client.games.batch_votes` and `client.presence.get` all chunk for you.
- **Group members are cheap.** `GET /v1/groups/{id}/users` is 1200 per minute at 100 members per call, so a 100,000-member group takes about a minute of requests.
- **The single-group GET is 7 per minute.** v2 uses it only for the seed group and takes every other group's profile from the batch endpoint or from the ally and enemy response, which already carries full group objects.
- **Servers is 3 per minute.** A game with thousands of servers cannot be enumerated quickly. Use `max_items` and expect to wait.
- **The friends list is 20 per minute**, so a depth-1 friend network of a user with 200 friends takes about 10 minutes; depth 2 is out of reach for most users without a long run.
- **Per-user profile detail is 30 per minute.** `GET /v1/users/{id}` is the only public source of `description`, `created` and `isBanned`, so 1,000 full profiles take about 35 minutes. If you only need names, the batch POST does 1,000 users per second.
- **Search and username history are 1 per minute each.** Look up an id once and cache it. The `previousUsernames` field on search results is often enough.
- **PyRoblox paces itself.** The client applies a per-host throttle (default 1 request per second), reads `x-ratelimit-remaining` and `retry-after`, sleeps when Roblox says to, and retries with backoff before raising `RateLimitedError`. Leave it at the default unless you know the endpoint's limit.
- **Limits are clock-aligned windows per endpoint.** The `x-ratelimit-reset` values suggest fixed 60 second windows. Two different 1-per-minute endpoints called back to back both succeed; the same one twice does not.

## Where Roblox documents these

- Hub: https://create.roblox.com/docs/cloud
- Per-domain reference, also available as Markdown by adding `.md`: `https://create.roblox.com/docs/cloud/reference/domains/<domain>.md`, where `<domain>` is one of `users`, `friends`, `groups`, `games`, `badges`, `inventory`, `catalog`, `economy`, `avatar`, `accountinformation`, `develop`, `thumbnails`. The `presence` page listed no GET endpoints on 2026-09-28; its POST endpoints are covered above from the probe.
- The old per-service swagger pages at `https://<domain>.roblox.com/docs` redirect to the pages above, and the `docs/json/...` swagger JSON files are gone.
- Rate limits are not documented anywhere by Roblox. The figures on this page come from response headers and will drift.
