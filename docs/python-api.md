# Python API

pyroblox is a library first; the `roblox` command is a thin layer over it. This
guide covers the client, the typed models, the domain APIs, the collectors, and
migration from earlier versions.

```
pip install "git+https://github.com/CTEC-MIIS/PyRoblox"
```

```python
from pyroblox import RobloxClient

with RobloxClient() as client:
    user = client.users.get_info(261)
    print(user.name, user.created, user.is_banned)
```

`import robloxwrapper` still works and exposes the same names, for scripts
written against earlier versions.

## The client

`RobloxClient` owns the HTTP session, the optional cookie, rate limiting, and
retries. All domain APIs hang off it as attributes. Use it as a context manager
so the session is closed, or call `client.close()`.

```python
RobloxClient(
    cookie=None,        # .ROBLOSECURITY value; None for public data only
    rate=1.0,           # requests per second per Roblox host
    burst=5,            # how many requests may go out at once before pacing kicks in
    max_retries=4,      # retries on 429 and 5xx before raising
    timeout=30,         # seconds per request
    jitter=True,        # randomise backoff so many clients do not retry in lockstep
    session=None,       # a requests.Session (or a fake, for tests)
    user_agent="PyRoblox/2.0 (+https://github.com/CTEC-MIIS/PyRoblox)",
)
```

| Attribute | What it covers |
|---|---|
| `client.users` | profiles, batch id lookup, username resolution and history, search |
| `client.friends` | friends, followers, followings, counts |
| `client.groups` | group profiles, members, roles, allies, enemies, social links, name history, a user's groups, search |
| `client.games` | experiences, place-to-universe, user and group games, favourites, servers, votes, media, game passes, places |
| `client.badges` | user badges, universe badges, single badge |
| `client.avatar` | avatar, worn items, outfits |
| `client.inventory` | collectibles, inventory by type, asset owners, favourite assets, bundles |
| `client.account` | Roblox badges, promotion channels |
| `client.presence` | online presence, last online |
| `client.thumbnails` | thumbnail URLs and downloads |
| `client.catalog` | catalog item details, bundles, economy details, resale data (`client.assets` is an alias) |

### Typed models

Every method returns a Pydantic model (or a list of them) rather than a raw
dict. Models live in `pyroblox.models` and share three properties:

- **snake_case attributes with camelCase aliases.** Roblox sends `memberCount`;
  you read `group.member_count`. Both spellings work when constructing a model.
- **Nothing is dropped.** Fields the model does not declare are kept in
  `model.model_extra` and are readable as attributes with Roblox's spelling
  (`group.communityTier`). A field Roblox adds tomorrow appears automatically.
- **Timestamps are `datetime` objects** in UTC.

```python
group = client.groups.get_info(7)
group.name                 # "Roblox"
group.owner.username       # "Games"
group.member_count         # 13508012
group.communityTier        # extra field, as sent

group.to_record()          # plain dict with Roblox's keys, ISO-string dates
```

`to_record()` (and the module-level `pyroblox.to_record` / `to_records`) turn
models back into JSON-compatible dicts containing exactly the keys Roblox sent.
The CSV exporter and the manifests use it, so CSV columns keep Roblox's names.
For loosely specified endpoints the model is `RobloxRecord`, which declares no
fields and simply carries what Roblox sent.

Missing required fields (an `id`, a `name`) raise `pydantic.ValidationError`.
That only happens if Roblox changes a response shape; report it.

### Paginated results

Paginated methods return a `PagedList`, a `list` subclass with one extra
attribute:

```python
members = client.groups.get_members(7, max_items=500)
len(members)          # 500
members[0].user.username
members.truncated     # True if Roblox had more rows than the cap allowed
```

For lazy iteration over very large lists use the low-level generator:

```python
from pyroblox.models.groups import GroupMember

for m in client.paginate("https://groups.roblox.com/v1/groups/7/users",
                         model=GroupMember, limit=100, sort_order="Asc"):
    ...
```

### Rate limiting and retries

Three mechanisms, all automatic:

1. A token bucket per host (`rate`, `burst`). With the defaults, sustained
   traffic to `users.roblox.com` is one request per second.
2. Roblox's own headers. Every response carries `x-ratelimit-remaining` and
   `x-ratelimit-reset`. When a response says the per-endpoint quota is used up,
   the client sleeps until the window resets before the next call to that
   endpoint. Endpoints are keyed by host and path with ids removed, so
   `users/261/username-history` and `users/1/username-history` share a bucket.
3. Retries. A 429 or 5xx is retried up to `max_retries` times, waiting the
   longer of `Retry-After` and `x-ratelimit-reset` (capped at 120 seconds), or
   an exponential backoff starting at one second, jittered unless Roblox named
   a wait. Then `RateLimitedError` or `ServerError` is raised.

Cursor pagination stops if Roblox returns the same cursor twice.

### Cookie behaviour

- The cookie is sent only to `roblox.com` and `*.roblox.com` hosts. Thumbnail
  downloads from `rbxcdn.com` never carry it.
- If Roblox answers 401 to a request that carried the cookie, the client logs a
  warning, marks the cookie rejected, and retries that request without it. From
  then on `client.has_cookie` is `False` and `client.cookie_rejected` is `True`.
- POST endpoints need an `X-CSRF-TOKEN`. The client learns it from the first
  403 response and resends once. This happens with or without a cookie.

### Low-level calls

```python
client.get(url, params=None)              # parsed JSON
client.post(url, json=None, params=None)  # parsed JSON
client.download(url)                      # bytes

client.paginate(url, params, limit=100, max_pages=None, max_items=None, sort_order=None, model=None)
    # generator over items across nextPageCursor pages
client.fetch_all(url, params, limit=100, max_pages=None, max_items=None, sort_order=None, model=None)
    # PagedList
client.fetch_rows(url, params, key="relatedGroups", page_size=100, max_items=None, model=None)
    # PagedList; the model.startRowIndex style used by allies/enemies
```

## Errors

```python
from pyroblox import (
    RobloxError, NotFoundError, PrivateError, AuthRequiredError, AuthenticationError,
    BadRequestError, RateLimitedError, ServerError, EntityUnavailable,
)
```

| Exception | HTTP | Typical cause |
|---|---|---|
| `NotFoundError` | 404 | id does not exist or was deleted |
| `PrivateError` | 403 | private inventory, hidden data |
| `AuthRequiredError` | 401 | endpoint needs a cookie |
| `AuthenticationError` | 401 or 403 | parent of the two above |
| `BadRequestError` | 400 | banned user, locked group, bad parameter; `.roblox_message` holds Roblox's text |
| `RateLimitedError` | 429 after retries | too many requests from this IP |
| `ServerError` | 5xx after retries | Roblox outage |
| `RobloxError` | anything else | base class; catch this for "anything Roblox-related" |
| `EntityUnavailable` | | raised by collectors when the main entity cannot be fetched; `.reason` is `not-found`, `private`, or `invalid` |

All carry `.status` (alias `.status_code`), `.url`, `.roblox_message`, and
`.errors` (Roblox's error array). `PyRobloxError`, `RobloxAPIError`, and
`RateLimitError` are aliases kept from the 2.0 pre-release.

```python
try:
    profile = client.users.get_info(5)
except BadRequestError as e:
    print("Roblox refused:", e.roblox_message)    # "The user is invalid."
except NotFoundError:
    print("no such user")
except RobloxError as e:
    print("something else:", e)
```

## Domain APIs

Arguments named `max_items` cap paginated results. Rate limits are per IP
without a cookie, as measured on 2026-09-28; see
[roblox-endpoints.md](roblox-endpoints.md).

### `client.users`

| Method | Returns | Notes |
|---|---|---|
| `get_info(user_id)` | `User`: id, name, display_name, description, created, is_banned, has_verified_badge | 30/min. Works for banned users. |
| `get_batch(user_ids, exclude_banned=False)` | `list[User]` (id, name, display_name, has_verified_badge) | 100 ids per call, 1000 calls/s. The way to put names on id lists. |
| `get_by_usernames(usernames, exclude_banned=False)` | `list[UsernameMatch]` (User plus requested_username) | 100 per call |
| `resolve(username)` | `UsernameMatch` | `NotFoundError` if no match |
| `get_username_history(user_id, max_items=None)` | `PagedList[UsernameHistoryEntry]` (name) | 1/min |
| `search(keyword, max_items=None)` | `PagedList[User]` with previous_usernames | 1/min |
| `get_authenticated()` | `User`: the logged-in account | cookie |

### `client.friends`

| Method | Returns | Notes |
|---|---|---|
| `get_friends(user_id)` | `list[Friend]` (id, name, display_name) | 20/min. Names are blank unauthenticated; entries with id `-1` are deleted friends. |
| `get_friend_ids(user_id)` | `list[int]` | |
| `get_friend_count(user_id)` (alias `get_count`), `get_follower_count(user_id)`, `get_following_count(user_id)` | `int` | |
| `get_counts(user_id)` | `FriendCounts` (friends, followers, followings) | three calls |
| `get_followers(user_id, max_items=None)`, `get_followings(user_id, max_items=None)` | `PagedList[Friend]` | cookie |

### `client.groups`

| Method | Returns | Notes |
|---|---|---|
| `get_info(group_id)` | `Group` with owner, shout, member_count, is_locked | 7/min. Use `get_batch` for many groups. |
| `get_batch(group_ids)` | `list[GroupSummary]` (id, name, description, owner{id,type}, created) | 100 per call, 1/s |
| `get_members(group_id, max_items=None, sort_order="Asc")` | `PagedList[GroupMember]` (user: GroupUser, role: GroupRole) | 1200/min, 100 per page |
| `get_roles(group_id)` | `list[GroupRole]` (id, name, rank, member_count) | |
| `get_role_members(group_id, role_id, max_items=None)` | `PagedList[GroupUser]` | |
| `get_allies(group_id, max_items=None)`, `get_enemies(group_id, max_items=None)` | `PagedList[Group]` | `BadRequestError` for locked groups |
| `get_social_links(group_id)` | `list[SocialLink]` (id, type, url, title) | cookie |
| `get_name_history(group_id, max_items=None)` | `PagedList[GroupNameHistoryEntry]` (name, created) | |
| `get_user_groups(user_id)` | `list[UserGroupMembership]` (group, role, is_primary_group) | |
| `get_user_primary_group(user_id)` | `UserGroupMembership` or `None` | |
| `search(keyword, max_items=None, prioritize_exact_match=True)` | `PagedList[GroupSearchResult]` | |
| `lookup(group_name)` | `list[GroupSearchResult]` | exact-ish match |
| `get_guest_permissions(group_id)` | `RobloxRecord` | |

### `client.games`

| Method | Returns | Notes |
|---|---|---|
| `get_info(universe_id)` | `Game` with root_place_id, creator, playing, visits, favorited_count | `NotFoundError` if unknown |
| `get_batch(universe_ids)` | `list[Game]` | 100 per call |
| `get_universe_id(place_id)` | `int` | the id in game URLs is a place id |
| `get_info_by_place(place_id)` | `Game` | two calls |
| `get_user_games(user_id, max_items=None)` | `PagedList[Game]` | page size 50 (Roblox's cap) |
| `get_group_games(group_id, max_items=None)` | `PagedList[Game]` | |
| `get_user_favorites(user_id, max_items=None)` | `PagedList[Game]` | newest first; Roblox rejects ascending order here |
| `get_servers(place_id, server_type="Public", max_items=None)` | `PagedList[GameServer]` | takes a place id; 3/min |
| `get_votes(universe_id)`, `get_votes_batch(universe_ids)` | `GameVotes` / `list[GameVotes]` (up_votes, down_votes) | |
| `get_favorites_count(universe_id)` | `int` | |
| `get_media(universe_id)` | `list[GameMedia]` | |
| `get_game_passes(universe_id)` | `list[GamePass]` | |
| `get_places(universe_id, max_items=None)` | `PagedList[Place]` | every place in the universe |
| `get_place_details(place_ids)` | `list[RobloxRecord]` | cookie |
| `get_user_created_places(user_id, max_items=None)` | `PagedList[CreatedPlace]` | |

### `client.badges`

| Method | Returns | Notes |
|---|---|---|
| `get_user_badges(user_id, max_items=None)` | `PagedList[Badge]` | cookie |
| `get_awarded_dates(user_id, badge_ids)` | `list[BadgeAwardDate]` (badge_id, awarded_date) | cookie, 10/min |
| `get_universe_badges(universe_id, max_items=None)` | `PagedList[Badge]` with statistics | |
| `get_info(badge_id)` | `Badge` | |

### `client.avatar`, `client.inventory`, `client.account`, `client.presence`

| Method | Returns | Notes |
|---|---|---|
| `avatar.get_avatar(user_id)` | `Avatar` (player_avatar_type, body_colors, scales, assets) | 40/min |
| `avatar.get_currently_wearing(user_id)` | `list[int]` | 6/min; prefer `get_avatar` |
| `avatar.get_outfits(user_id, max_items=None)` | `list[Outfit]` | |
| `inventory.can_view(user_id)` | `bool` | 1/min; usually just call `get_user_inventory` and catch `PrivateError` |
| `inventory.get_collectibles(user_id, max_items=None)` | `PagedList[CollectibleAsset]` | |
| `inventory.get_user_inventory(user_id, asset_type_id, max_items=None)` (alias `get_items`) | `PagedList[InventoryItem]` | `PrivateError` if hidden; type ids in `pyroblox.avatar.ASSET_TYPES` |
| `inventory.get_asset_owners(asset_id, max_items=None)` | `PagedList[AssetOwner]` | owner null without cookie |
| `inventory.get_favorite_assets(user_id, asset_type_id, max_items=None)` | `PagedList[CatalogItem]` | 10/min |
| `inventory.get_bundles(user_id, max_items=None)` | `PagedList[Bundle]` | 10/min |
| `account.get_roblox_badges(user_id)` | `list[RobloxBadge]` | |
| `account.get_promotion_channels(user_id)` | `PromotionChannels` (facebook, twitter, youtube, twitch, guilded) | values null without cookie |
| `presence.get_presence(user_ids)` | `list[UserPresence]` | 100 ids per call; type 0 offline, 1 online, 2 in game, 3 Studio |
| `presence.get_last_online(user_ids)` | `list[LastOnline]` | |

`ASSET_TYPES` maps names to Roblox asset type ids: `hat` 8, `tshirt` 2, `shirt`
11, `pants` 12, `face` 18, `gear` 19, `head` 17, `hair` 41, `face_accessory` 42,
`neck_accessory` 43, `shoulder_accessory` 44, `front_accessory` 45,
`back_accessory` 46, `waist_accessory` 47, `emote` 61, `place` 9, `model` 10,
`decal` 13, `audio` 3, `animation` 24, `video` 62.

### `client.thumbnails`

| Method | Returns | Notes |
|---|---|---|
| `get_thumbnails(kind, ids, size="420x420", fmt="Png")` | `list[Thumbnail]` (target_id, state, image_url) | 100 ids per call; `state == "Completed"` means the URL is ready |
| `get_user_headshots(ids)`, `get_user_avatars(ids)`, `get_group_icons(ids)`, `get_game_icons(ids)`, `get_asset_thumbnails(ids)`, `get_badge_icons(ids)` | `list[Thumbnail]` | wrappers over `get_thumbnails` |
| `download(url)` | `bytes` | cookie never sent |
| `save(kind, ids, out_dir, size="420x420")` | `list[SavedThumbnail]` (kind, target_id, url, path, sha256) | writes `<kind>_<id>.png`, skips existing files |

Kinds (`pyroblox.thumbnails.KINDS`): `user-headshot`, `user-avatar`,
`user-bust`, `group-icon`, `game-icon`, `game-thumbnail`, `place-icon`,
`asset`, `badge-icon`, `bundle`.

### `client.catalog`

| Method | Returns | Notes |
|---|---|---|
| `get_item_details(items)` | `list[CatalogItem]` | `items` are `{"itemType": "Asset"|"Bundle", "id": n}`; POST with automatic CSRF |
| `get_asset_item_details(asset_ids)` | `list[CatalogItem]` | |
| `get_asset_bundles(asset_id, max_items=None)` | `PagedList[Bundle]` | |
| `get_bundle(bundle_id)` | `Bundle` | |
| `get_economy_details(asset_id)` | `EconomyAssetDetails` (asset_id, name, creator, created, price_in_robux, sales, is_limited) | PascalCase endpoint; works for place ids too |
| `get_resale_data(asset_id)` | `ResaleData` | `BadRequestError` for non-limited items |

## Collectors and snapshots

```python
from pyroblox import (
    user_snapshot, group_snapshot, game_snapshot, friend_network, group_network,
    USER_TABLES, GROUP_TABLES, GAME_TABLES,
)
```

Each collector returns a `Snapshot`. Its tables hold plain records (the models
converted with `to_record`), so everything below is JSON-ready:

```python
snap = user_snapshot(client, 261)
snap.entity, snap.entity_id      # "user", 261
snap.tables                      # {"profile": [...], "friends": [...], ...}
snap["friends"]                  # list of dicts with Roblox's keys
snap.counts()                    # {"profile": 1, "friends": 98, ...}
snap.meta                        # captured_at, omitted, truncated, errors, ...
snap.to_dataframes()             # {"profile": DataFrame, ...}
snap.save("out_dir")             # CSVs + manifest; returns the paths
snap.save("out_dir", fmt="json")
```

### Best-effort policy

The primary lookup (the user, group, or game itself) must succeed or
`EntityUnavailable` is raised. Every other table is attempted independently:

| Outcome | Effect |
|---|---|
| success | table added |
| `AuthRequiredError` | `meta["omitted"][table] = "cookie-required"` |
| `PrivateError` | `"private"` |
| `NotFoundError` | `"not-found"` |
| `BadRequestError` | `"invalid"`, plus an entry in `meta["errors"]` |
| other `RobloxError` | `"error"`, plus an entry in `meta["errors"]` |
| `RateLimitedError`, `ServerError` | **raised**; you never get a silently half-empty snapshot |

Paginated tables cut short by a cap are flagged in `meta["truncated"]`.

### Signatures

```python
user_snapshot(client, user_id, *, include=None, exclude=(), max_items=None,
              hydrate_names=True, progress=None)
group_snapshot(client, group_id, *, include=None, exclude=(), max_items=None, progress=None)
game_snapshot(client, game_id, *, by_place=False, include=None, exclude=(),
              max_servers=100, max_items=None, progress=None)
friend_network(client, user_id, *, depth=1, max_users=None, hydrate_names=True, progress=None)
group_network(client, group_id, *, include_members=True, include_member_profiles=False,
              include_favorites=False, max_groups=None, max_members=None, progress=None)
```

- `include` / `exclude` take table names from `USER_TABLES`, `GROUP_TABLES`,
  `GAME_TABLES`. Unknown names raise `ValueError`.
- `hydrate_names` fills blank names in friend lists with one batch call.
- `progress` is a callable that receives short status strings
  (`"user 261: friends"`); the CLI prints them, and the default logs at INFO.
- `friend_network` returns tables `edges` (`source`, `target`) and `nodes`
  (`id`, `name`, `displayName`, `hasVerifiedBadge`, `depth`, `expanded`).
  `depth=1` fetches the seed's friends; `depth=2` also fetches each friend's
  friends. Deleted friends (id `-1`) are skipped and counted in
  `meta["hidden_friends_skipped"]`.
- `group_network` returns `groups`, `allies`, `enemies`, `membership`,
  `members`, and with the flags `member_profiles`, `favorite_games`, `games`.
  Groups whose relationships or members could not be fetched are listed in
  `meta["failed"]`.

### Export helpers

```python
from pyroblox import flatten, to_dataframe, to_record, write_records, edgelist_to_graphml

flatten({"owner": {"userId": 1}, "tags": ["a", "b"]})
# {"owner_userId": 1, "tags": "a;b"}

df = to_dataframe(client.groups.get_members(7, max_items=100))   # models or dicts, one flattened row each
write_records(members, "members.csv")                            # or fmt="json"
edgelist_to_graphml(snap["edges"], "friends.graphml", nodes={1: {"name": "a"}})
```

## Configuration

```python
from pyroblox import RobloxConfig, load_config

cfg = load_config("settings.yaml", rate=0.5)   # file, then env, then keyword overrides
client = cfg.make_client()
```

Keys: `cookie`, `cookie_file`, `output_dir`, `rate`, `burst`, `max_retries`,
`timeout`, `log_level`, `log_file`. Environment variables are the same names
upper-cased with a `ROBLOX_` prefix (`ROBLOX_COOKIE_FILE`). `cfg.resolve_cookie()`
returns the cookie from `cookie` or the contents of `cookie_file`.
`cfg.to_dict()` redacts the cookie.

## Migrating

### From PyRoblox 1.x (`robloxwrapper`, 2021 to 2024)

The three documented v1 functions still exist with their signatures and output
files, importable from either `pyroblox` or `robloxwrapper`:

| v1 | Now | Notes |
|---|---|---|
| `build_dataframes(group_id, {".ROBLOSECURITY": c})` | `build_dataframes(group_id, cookie=None, output_dir=".", client=None, include_favorites=True)` | Writes the same seven files; membership and favourites are now correct; returns a dict of DataFrames plus `"snapshot"`. |
| `group_edgelist(id)` | `group_edgelist(id, client=None)` or `group_network(client, id, include_members=False)` | same `{"allies": [[a, b], ...], "enemies": [...]}` shape |
| `friend_edgelist(id)` | `friend_edgelist(id, client=None)` or `friend_network(client, id, depth=2)` | same `[[a, b], ...]` shape |
| `friends(id).info()` | `client.friends.get_friends(id)` | `robloxwrapper.friends` still works with a `DeprecationWarning` |
| `friends(id).user_info()` | `client.users.get_info(id)` | |
| `groups(id).info()` | `client.groups.get_info(id)` | |
| `groups(id).allies()` / `.enemies()` | `client.groups.get_allies(id)` / `.get_enemies(id)` | the shim rebuilds the v1 envelope |
| `groups(id).user_list(cursor)` | `client.groups.get_members(id)` | paginates for you |
| `groups(id).social_links(cookies)` | `RobloxClient(cookie).groups.get_social_links(id)` | |
| `group_games(id).info()` | `client.games.get_group_games(id)` | |
| `user_games(id).games_list()` | `client.games.get_user_games(id)` | |
| `user_games(id).favorites_list(cursor)` | `client.games.get_user_favorites(id)` | v1 sent a sort order Roblox now rejects |

### From the 2.0 pre-release (`pyroblox` 2.0.0a1, March 2026)

Method names, model names, and `client.<api>` attributes are unchanged. What differs:

| Pre-release | Now |
|---|---|
| `client.games.get_info([13058])` returning a list | `client.games.get_info(13058)` returns one `Game`; `get_batch([...])` returns the list |
| `client.games.get_votes([...])` | `get_votes(id)` and `get_votes_batch([...])` |
| `get_members(..., max_pages=3)` returning a lazy iterator | returns a `PagedList` (eager, with `.truncated`); use `client.paginate(..., model=...)` for laziness |
| `users.search(keyword, limit=10)` | `users.search(keyword, max_items=10)` |
| `games.get_servers(place_id, server_type=0)` | `server_type="Public"` |
| `client.catalog.search(...)`, bundle favourite counts and recommendations | not carried over (unverified endpoints) |
| `pyroblox.contrib.edgelists.group_edgelist(client, id, depth=2)`, `friend_edgelist(client, id, depth=2)` | still available with the same signatures, returning tuples |
| `pyroblox.contrib.dataframes.build_network_dataframes(client, id, output_dir=...)` | still available; membership now covers every group in the neighbourhood |
| `RateLimitError`, `AuthenticationError`, `RobloxAPIError`, `PyRobloxError` | still importable; `AuthenticationError` now has `AuthRequiredError` (401) and `PrivateError` (403) children |
| httpx | requests (the client is not async either way) |

## Recipes

### Resolve a username and dump everything about the user

```python
from pyroblox import RobloxClient, user_snapshot

with RobloxClient() as client:
    user = client.users.resolve("Shedletsky")
    snap = user_snapshot(client, user.id, exclude=["collectibles"], max_items=1000)
    paths = snap.save("data")
    print(snap.counts(), snap.meta["omitted"])
```

### Collect a group's members and add profile detail

```python
members = client.groups.get_members(7, max_items=2000)
ids = [m.user.user_id for m in members]
names = client.users.get_batch(ids)                # fast: 100 ids per call
# full profiles (created date, banned flag) are 30/min, so sample:
profiles = [client.users.get_info(uid) for uid in ids[:50]]
banned = [p.name for p in profiles if p.is_banned]
```

### Friend network to depth 2, capped, as GraphML

```python
from pyroblox import friend_network, edgelist_to_graphml

net = friend_network(client, 261, depth=2, max_users=100, progress=print)
nodes = {n["id"]: {"name": n["name"], "depth": n["depth"]} for n in net["nodes"]}
edgelist_to_graphml(net["edges"], "shedletsky.graphml", nodes=nodes)
```

### Bulk lookup from a CSV with pandas

```python
import pandas as pd
from pyroblox import to_dataframe

ids = pd.read_csv("suspects.csv")["user_id"].tolist()
names = to_dataframe(client.users.get_batch(ids))
presence = to_dataframe(client.presence.get_presence(ids))
merged = names.merge(presence, left_on="id", right_on="userId", how="left")
merged.to_csv("suspects_enriched.csv", index=False)
```

### Use a cookie from a file and check it

```python
from pyroblox import load_config, AuthRequiredError

client = load_config(cookie_file="~/.roblox_cookie").make_client()
try:
    me = client.users.get_authenticated()
    print("logged in as", me.name)
except AuthRequiredError:
    print("cookie rejected; copy a fresh one")

followers = client.friends.get_followers(261, max_items=500)
links = client.groups.get_social_links(7)
```

### Group network, the v1 way

```python
from pyroblox import build_dataframes

frames = build_dataframes(5351020, output_dir="v1_style")
frames["membership"].head()
```
