# Python API

PyRoblox is a library first; the `roblox` command is a thin layer over it. This
guide covers the client, the domain APIs, the collectors, and migration from v1.

```
pip install "git+https://github.com/CTEC-MIIS/PyRoblox"
```

```python
from robloxwrapper import RobloxClient

client = RobloxClient()
client.users.get(261)
```

## The client

`RobloxClient` owns the HTTP session, the optional cookie, rate limiting, and
retries. All domain APIs hang off it as attributes.

```python
RobloxClient(
    cookie=None,        # .ROBLOSECURITY value; None for public data only
    rate=1.0,           # requests per second per Roblox host
    burst=5,            # how many requests may go out at once before pacing kicks in
    max_retries=4,      # retries on 429 and 5xx before raising
    timeout=30,         # seconds per request
    session=None,       # a requests.Session (or a fake, for tests)
    user_agent="PyRoblox/2.0 (+https://github.com/CTEC-MIIS/PyRoblox)",
)
```

| Attribute | Module | What it covers |
|---|---|---|
| `client.users` | `users.py` | profiles, batch id lookup, username resolution and history, search |
| `client.friends` | `friends.py` | friends, followers, followings, counts |
| `client.groups` | `groups.py` | group profiles, members, roles, allies, enemies, social links, name history, a user's groups, search |
| `client.games` | `games.py` | experiences, place-to-universe, user and group games, favourites, servers, votes, media, game passes, places |
| `client.badges` | `badges.py` | user badges, universe badges, single badge |
| `client.avatar` | `avatar.py` | avatar, worn items, outfits |
| `client.inventory` | `avatar.py` | collectibles, inventory by type, asset owners, favourite assets, bundles |
| `client.account` | `avatar.py` | Roblox badges, promotion channels |
| `client.presence` | `avatar.py` | online presence, last online |
| `client.thumbnails` | `thumbnails.py` | thumbnail URLs and downloads |
| `client.assets` | `assets.py` | economy and catalog details, bundles, resale data |

### Return values

Every method returns Roblox's JSON as plain `dict` or `list` values with the
outer envelope removed (`["data"]`, `["roles"]`, `["count"]`). There are no
dataclasses. When Roblox adds a field, you see it; when Roblox renames one, your
code that reads it breaks at the point of use rather than at parse time.

Paginated methods return a `PagedList`, a `list` subclass with one extra
attribute:

```python
members = client.groups.members(7, max_items=500)
len(members)          # 500
members.truncated     # True if Roblox had more rows than the cap allowed
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
   an exponential backoff starting at one second. Then `RateLimitedError` or
   `ServerError` is raised.

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

client.paginate(url, params, limit=100, max_pages=None, max_items=None, sort_order=None)
    # generator over items across nextPageCursor pages
client.fetch_all(url, params, limit=100, max_pages=None, max_items=None, sort_order=None)
    # PagedList
client.fetch_rows(url, params, key="relatedGroups", page_size=100, max_items=None)
    # PagedList; the model.startRowIndex style used by allies/enemies
```

## Errors

```python
from robloxwrapper import (
    RobloxError, NotFoundError, PrivateError, AuthRequiredError,
    BadRequestError, RateLimitedError, ServerError, EntityUnavailable,
)
```

| Exception | HTTP | Typical cause |
|---|---|---|
| `NotFoundError` | 404 | id does not exist or was deleted |
| `PrivateError` | 403 | private inventory, hidden data |
| `AuthRequiredError` | 401 | endpoint needs a cookie |
| `BadRequestError` | 400 | banned user, locked group, bad parameter; `.roblox_message` holds Roblox's text |
| `RateLimitedError` | 429 after retries | too many requests from this IP |
| `ServerError` | 5xx after retries | Roblox outage |
| `RobloxError` | anything else | base class; catch this for "anything Roblox-related" |
| `EntityUnavailable` | | raised by collectors when the main entity cannot be fetched; `.reason` is `not-found`, `private`, or `invalid` |

All carry `.status`, `.url`, and `.roblox_message`.

```python
try:
    profile = client.users.get(5)
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
| `get(user_id)` | dict: id, name, displayName, description, created, isBanned, hasVerifiedBadge | 30/min. Works for banned users. |
| `batch_get(user_ids, exclude_banned=False)` | list of id, name, displayName, hasVerifiedBadge | 100 ids per call, 1000 calls/s. The way to put names on id lists. |
| `by_usernames(usernames, exclude_banned=False)` | list with requestedUsername, id, name, displayName | 100 per call |
| `resolve(username)` | dict | `NotFoundError` if no match |
| `username_history(user_id, max_items=None)` | PagedList of `{"name"}` | 1/min |
| `search(keyword, max_items=None)` | PagedList with previousUsernames | 1/min |
| `authenticated()` | dict: the logged-in account | cookie |

### `client.friends`

| Method | Returns | Notes |
|---|---|---|
| `friends(user_id)` | list of id, name, displayName | 20/min. Names are blank unauthenticated; entries with id `-1` are deleted friends. |
| `friend_ids(user_id)` | list of int | |
| `friend_count(user_id)`, `follower_count(user_id)`, `following_count(user_id)` | int | |
| `counts(user_id)` | `{"friends", "followers", "followings"}` | three calls |
| `followers(user_id, max_items=None)`, `followings(user_id, max_items=None)` | PagedList | cookie |

### `client.groups`

| Method | Returns | Notes |
|---|---|---|
| `get(group_id)` | dict with owner, shout, memberCount, isLocked | 7/min. Use `batch_get` for many groups. |
| `batch_get(group_ids)` | list with id, name, description, owner{id,type}, created | 100 per call, 1/s |
| `members(group_id, max_items=None, sort_order="Asc")` | PagedList of `{"user": {...}, "role": {...}}` | 1200/min, 100 per page |
| `roles(group_id)` | list of id, name, rank, memberCount | |
| `role_members(group_id, role_id, max_items=None)` | PagedList | |
| `allies(group_id, max_items=None)`, `enemies(group_id, max_items=None)` | PagedList of full group objects | `BadRequestError` for locked groups |
| `social_links(group_id)` | list of id, type, url, title | cookie |
| `name_history(group_id, max_items=None)` | PagedList of name, created | |
| `user_groups(user_id)` | list of `{"group", "role", "isPrimaryGroup"}` | |
| `user_primary_group(user_id)` | dict or None | |
| `search(keyword, max_items=None, prioritize_exact_match=True)` | PagedList | |
| `lookup(group_name)` | list | exact-ish match |
| `guest_permissions(group_id)` | dict | |

### `client.games`

| Method | Returns | Notes |
|---|---|---|
| `get(universe_id)` | dict with rootPlaceId, creator, playing, visits, favoritedCount | `NotFoundError` if unknown |
| `batch_get(universe_ids)` | list | 100 per call |
| `place_to_universe(place_id)` | int | the id in game URLs is a place id |
| `get_by_place(place_id)` | dict | two calls |
| `user_games(user_id, max_items=None)` | PagedList | page size 50 (Roblox's cap) |
| `group_games(group_id, max_items=None)` | PagedList | |
| `user_favorites(user_id, max_items=None)` | PagedList | newest first; Roblox rejects ascending order here |
| `servers(place_id, server_type="Public", max_items=None)` | PagedList | takes a place id; 3/min |
| `votes(universe_id)`, `batch_votes(universe_ids)` | dict / list of upVotes, downVotes | |
| `favorites_count(universe_id)` | int | |
| `media(universe_id)` | list | |
| `game_passes(universe_id)` | list | |
| `places(universe_id, max_items=None)` | PagedList | every place in the universe |
| `place_details(place_ids)` | list | cookie |
| `user_created_places(user_id, max_items=None)` | PagedList | |

### `client.badges`

| Method | Returns | Notes |
|---|---|---|
| `user_badges(user_id, max_items=None)` | PagedList | cookie |
| `awarded_dates(user_id, badge_ids)` | list of badgeId, awardedDate | cookie, 10/min |
| `universe_badges(universe_id, max_items=None)` | PagedList with statistics | |
| `get(badge_id)` | dict | |

### `client.avatar`, `client.inventory`, `client.account`, `client.presence`

| Method | Returns | Notes |
|---|---|---|
| `avatar.get(user_id)` | dict: playerAvatarType, bodyColors, scales, assets[] | 40/min |
| `avatar.currently_wearing(user_id)` | list of asset ids | 6/min; prefer `get` |
| `avatar.outfits(user_id, max_items=None)` | list | |
| `inventory.can_view(user_id)` | bool | 1/min; usually just call `items` and catch `PrivateError` |
| `inventory.collectibles(user_id, max_items=None)` | PagedList | |
| `inventory.items(user_id, asset_type_id, max_items=None)` | PagedList | `PrivateError` if hidden; type ids in `robloxwrapper.avatar.ASSET_TYPES` |
| `inventory.asset_owners(asset_id, max_items=None)` | PagedList | owner null without cookie |
| `inventory.favorite_assets(user_id, asset_type_id, max_items=None)` | PagedList | 10/min |
| `inventory.bundles(user_id, max_items=None)` | PagedList | 10/min |
| `account.roblox_badges(user_id)` | list | |
| `account.promotion_channels(user_id)` | dict: facebook, twitter, youtube, twitch | values null without cookie |
| `presence.get(user_ids)` | list of userPresences | 100 ids per call; type 0 offline, 1 online, 2 in game, 3 Studio |
| `presence.last_online(user_ids)` | list of userId, lastOnline | |

`ASSET_TYPES` maps names to Roblox asset type ids: `hat` 8, `tshirt` 2, `shirt`
11, `pants` 12, `face` 18, `gear` 19, `head` 17, `hair` 41, `face_accessory` 42,
`neck_accessory` 43, `shoulder_accessory` 44, `front_accessory` 45,
`back_accessory` 46, `waist_accessory` 47, `emote` 61, `place` 9, `model` 10,
`decal` 13, `audio` 3, `animation` 24, `video` 62.

### `client.thumbnails`

| Method | Returns | Notes |
|---|---|---|
| `get(kind, ids, size="420x420", fmt="Png")` | list of targetId, state, imageUrl | 100 ids per call; `state == "Completed"` means the URL is ready |
| `user_headshots(ids)`, `user_avatars(ids)`, `group_icons(ids)`, `game_icons(ids)`, `asset_thumbnails(ids)`, `badge_icons(ids)` | list | wrappers over `get` |
| `download(url)` | bytes | cookie never sent |
| `save(kind, ids, out_dir, size="420x420")` | list of kind, targetId, url, path, sha256 | writes `<kind>_<id>.png`, skips existing files |

Kinds (`robloxwrapper.thumbnails.KINDS`): `user-headshot`, `user-avatar`,
`user-bust`, `group-icon`, `game-icon`, `game-thumbnail`, `place-icon`,
`asset`, `badge-icon`, `bundle`.

### `client.assets`

| Method | Returns | Notes |
|---|---|---|
| `details(asset_id)` | dict, PascalCase keys (AssetId, Name, Creator, Created, PriceInRobux, IsLimited) | works for place ids too |
| `catalog_details(items)` | list | `items` are `{"itemType": "Asset"|"Bundle", "id": n}`; POST with automatic CSRF |
| `catalog_asset_details(asset_ids)` | list | |
| `bundles(asset_id, max_items=None)` | PagedList | |
| `resale(asset_id)` | dict | `BadRequestError` for non-limited items |
| `bundle_details(bundle_id)` | dict | |

## Collectors and snapshots

```python
from robloxwrapper import (
    user_snapshot, group_snapshot, game_snapshot, friend_network, group_network,
    USER_TABLES, GROUP_TABLES, GAME_TABLES,
)
```

Each collector returns a `Snapshot`:

```python
snap = user_snapshot(client, 261)
snap.entity, snap.entity_id      # "user", 261
snap.tables                      # {"profile": [...], "friends": [...], ...}
snap["friends"]                  # list of dicts
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
from robloxwrapper import flatten, to_dataframe, write_records, edgelist_to_graphml

flatten({"owner": {"userId": 1}, "tags": ["a", "b"]})
# {"owner_userId": 1, "tags": "a;b"}

df = to_dataframe(client.groups.members(7, max_items=100))   # one flattened row per record
write_records(records, "members.csv")                        # or fmt="json"
edgelist_to_graphml(snap["edges"], "friends.graphml", nodes={1: {"name": "a"}})
```

## Configuration

```python
from robloxwrapper import RobloxConfig, load_config

cfg = load_config("settings.yaml", rate=0.5)   # file, then env, then keyword overrides
client = cfg.make_client()
```

Keys: `cookie`, `cookie_file`, `output_dir`, `rate`, `burst`, `max_retries`,
`timeout`, `log_level`, `log_file`. Environment variables are the same names
upper-cased with a `ROBLOX_` prefix (`ROBLOX_COOKIE_FILE`). `cfg.resolve_cookie()`
returns the cookie from `cookie` or the contents of `cookie_file`.
`cfg.to_dict()` redacts the cookie.

## Migrating from v1

The three documented v1 functions still exist and keep their outputs:

| v1 | v2 equivalent | Notes |
|---|---|---|
| `build_dataframes(group_id, {".ROBLOSECURITY": c})` | `build_dataframes(group_id, cookie=None, output_dir=".", client=None, include_favorites=True)` | Writes the same seven files; membership and favourites are now correct; returns a dict of DataFrames plus `"snapshot"`. |
| `group_edgelist(id)` | `group_edgelist(id, client=None)` or `group_network(client, id, include_members=False)` | same `{"allies": [[a, b], ...], "enemies": [...]}` shape |
| `friend_edgelist(id)` | `friend_edgelist(id, client=None)` or `friend_network(client, id, depth=2)` | same `[[a, b], ...]` shape |
| `friends(id).info()` | `client.friends.friends(id)` | `robloxwrapper.legacy.friends` still works with a `DeprecationWarning` |
| `friends(id).user_info()` | `client.users.get(id)` | |
| `groups(id).info()` | `client.groups.get(id)` | |
| `groups(id).allies()` / `.enemies()` | `client.groups.allies(id)` / `.enemies(id)` | v2 returns the list directly; the legacy shim rebuilds the v1 envelope |
| `groups(id).user_list(cursor)` | `client.groups.members(id)` | v2 paginates for you |
| `groups(id).social_links(cookies)` | `RobloxClient(cookie).groups.social_links(id)` | |
| `group_games(id).info()` | `client.games.group_games(id)` | |
| `user_games(id).games_list()` | `client.games.user_games(id)` | |
| `user_games(id).favorites_list(cursor)` | `client.games.user_favorites(id)` | v1 sent a sort order Roblox now rejects |
| `from robloxwrapper import sess` | `RobloxClient().get(url)` | |

## Recipes

### Resolve a username and dump everything about the user

```python
from robloxwrapper import RobloxClient, user_snapshot

client = RobloxClient()
user = client.users.resolve("Shedletsky")
snap = user_snapshot(client, user["id"], exclude=["collectibles"], max_items=1000)
paths = snap.save("data")
print(snap.counts(), snap.meta["omitted"])
```

### Collect a group's members and add profile detail

```python
members = client.groups.members(7, max_items=2000)
ids = [m["user"]["userId"] for m in members]
names = client.users.batch_get(ids)                 # fast: 100 ids per call
# full profiles (created date, banned flag) are 30/min, so sample:
profiles = [client.users.get(uid) for uid in ids[:50]]
```

### Friend network to depth 2, capped, as GraphML

```python
from robloxwrapper import friend_network, edgelist_to_graphml

net = friend_network(client, 261, depth=2, max_users=100, progress=print)
nodes = {n["id"]: {"name": n["name"], "depth": n["depth"]} for n in net["nodes"]}
edgelist_to_graphml(net["edges"], "shedletsky.graphml", nodes=nodes)
```

### Bulk lookup from a CSV with pandas

```python
import pandas as pd
from robloxwrapper import to_dataframe

ids = pd.read_csv("suspects.csv")["user_id"].tolist()
names = to_dataframe(client.users.batch_get(ids))
presence = to_dataframe(client.presence.get(ids))
merged = names.merge(presence, left_on="id", right_on="userId", how="left")
merged.to_csv("suspects_enriched.csv", index=False)
```

### Use a cookie from a file and check it

```python
from robloxwrapper import load_config, AuthRequiredError

client = load_config(cookie_file="~/.roblox_cookie").make_client()
try:
    me = client.users.authenticated()
    print("logged in as", me["name"])
except AuthRequiredError:
    print("cookie rejected; copy a fresh one")

followers = client.friends.followers(261, max_items=500)
links = client.groups.social_links(7)
```

### Group network, the v1 way

```python
from robloxwrapper import build_dataframes

frames = build_dataframes(5351020, output_dir="v1_style")
frames["membership"].head()
```
