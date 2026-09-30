# PyRoblox v2 design (2026-09-28)

## Why

An independent audit on 2026-09-28 (see `docs/AUDIT-2026-09-28.md`) found that the
working tree does not import, the committed collection pipeline writes wrong data
for two of its seven CSVs, and the newer client code targets a dead API host with
invented endpoints. The goal of v2 is a package that internal (CTEC) and external
Roblox-safety researchers, including non-programmers, can install and use to pull
public Roblox data into CSV files, and that programmers can use as a library.

## Intended outcome and constraints

Stated by the user:
- Usable by both internal and external researchers working on Roblox safety.
- Usable by non-technical researchers as well.
- Combine functionality from the `tg_archiver` Roblox module on `alex@fedora` where sensible.
- Find Roblox data that is obtainable but currently missing.
- Docs and README updated.

Assumptions made because the user could not be asked mid-task:
- Keep the import name `robloxwrapper` and the distribution name `PyRoblox`; keep the CLI
  entry point `roblox`. Renaming would break existing internal scripts for no gain.
- Public, unauthenticated data is the primary target. A `.ROBLOSECURITY` cookie is optional
  and only unlocks the few endpoints that require it (group social links, presence).
- No Google Sheets/Drive daemon plumbing is ported. PyRoblox stays a library plus CLI.
- Backwards-compatible wrappers are kept for the three documented v1 functions
  (`build_dataframes`, `group_edgelist`, `friend_edgelist`) with their bugs fixed.
- Version becomes 2.0.0 because the public API changes.

## Architecture

```
robloxwrapper/
  __init__.py     public surface: RobloxClient, errors, parse_roblox_url, collectors, compat
  client.py       RobloxClient: session, cookie scoping, per-host throttle, retries, typed
                  errors, cursor + row pagination, CSRF for authenticated POSTs
  errors.py       RobloxError, NotFoundError, PrivateError (403), AuthRequiredError (401),
                  RateLimitedError, ServerError, BadRequestError (400 with Roblox `errors` body)
  urls.py         parse_roblox_url("https://www.roblox.com/users/261/profile") -> ("user", 261)
  users.py        UsersAPI:   get, batch_get, by_usernames, username_history, search
  friends.py      FriendsAPI: friends, friend_count, followers, followings, follower/following counts
  groups.py       GroupsAPI:  get, batch_get, members, roles, role_members, allies, enemies,
                  social_links (cookie), name_history, user_groups, search
                  (wall posts dropped: the endpoint returned 404 in the live probe)
  games.py        GamesAPI:   get (by universe), place_to_universe, user_games, group_games,
                  user_favorites, servers (by place), votes, favorites_count, media, game_passes
  badges.py       BadgesAPI:  user_badges, universe_badges, get
  avatar.py       AvatarAPI:  avatar, currently_wearing, outfits; InventoryAPI: can_view,
                  collectibles, inventory(asset_type); AccountAPI: roblox_badges,
                  promotion_channels; PresenceAPI: presence (POST)
  thumbnails.py   ThumbnailsAPI: batch thumbnail URLs for users/groups/games/assets/badges;
                  download(url)
  assets.py       AssetsAPI: details (economy), catalog details (POST), bundles, resale
  collect.py      Best-effort collectors returning a Snapshot: user_snapshot, group_snapshot,
                  game_snapshot, friend_network, group_network; compat build_dataframes,
                  group_edgelist, friend_edgelist
  export.py       records -> DataFrame (json_normalize, sep="_"), Snapshot.save(out_dir)
                  writes CSV/JSON + manifest.json; edgelist -> GraphML via networkx
  config.py       RobloxConfig from env vars, YAML/JSON file, CLI flags; cookie from
                  ROBLOX_COOKIE or ROBLOX_COOKIE_FILE
  cli.py          click CLI (see below)
  legacy.py       v1 class shims: friends, groups, group_games, user_games (DeprecationWarning)
tests/
  conftest.py     FakeSession/FakeResponse/FakeClock (ported from tg_archiver tests)
  test_client.py, test_urls.py, test_users.py, ... one per module, no network
  test_cli.py     CliRunner with a FakeSession injected via a test-only hook
  live/           tests that hit the real API; skipped unless ROBLOX_LIVE_TESTS=1
docs/
  AUDIT-2026-09-28.md, getting-started.md (non-technical), cli-reference.md,
  python-api.md, data-dictionary.md, roblox-endpoints.md, responsible-use.md
```

### Client (`client.py`)

Ported from `tg_archiver/roblox_client.py` with these changes:
- Per-host token bucket throttle (`rate` req/s, `burst`), default 1 req/s burst 5. Roblox
  returns 429 with `Retry-After` when exceeded; the client sleeps that long (capped at 120 s)
  and retries up to `max_retries` (default 4) with exponential backoff, then raises
  `RateLimitedError`. 5xx retried the same way, then `ServerError`.
- 404 -> `NotFoundError`, 403 -> `PrivateError`, 401 -> `AuthRequiredError`.
  400 with a Roblox `{"errors":[{"code":..,"message":..}]}` body -> `BadRequestError`
  carrying the Roblox message (for example "The user is invalid" for banned accounts).
- Cookie is sent only to `roblox.com` and `*.roblox.com`, never to `rbxcdn.com`.
  On the first 401 while a cookie is attached, the client logs a warning, marks the cookie
  invalid, and retries unauthenticated. `client.cookie_valid` exposes the state.
- Authenticated POSTs handle Roblox's CSRF dance: on 403 with an `x-csrf-token` response
  header, store the token, resend once.
- `paginate(url, params, limit=100, max_pages=None)` yields items across `nextPageCursor`
  pages. `paginate_rows(url, key, page_size=100)` handles the `model.startRowIndex`
  style used by allies/enemies. Both accept `max_items` so callers can cap work.
- `session`, `clock`, `sleep` are injectable for tests.
- Every method returns Roblox's JSON as plain dicts/lists. No dataclasses that pin field
  names: the commit history ("fixing fields" x3) shows those break whenever Roblox changes a
  response. Flattening for CSV happens in `export.py`.

### Collectors (`collect.py`)

A `Snapshot` is a dict of table name -> list of records, plus `meta` (entity, ids,
`captured_at`, `omitted`, `truncated`, `errors`). The best-effort policy is ported from
`roblox_capture.py`: the primary lookup must succeed (404/403 raise), every secondary
lookup that fails with a 4xx is recorded in `omitted` and collection continues; rate
limit and server errors propagate.

- `user_snapshot(client, user_id, include=ALL)` tables: profile, counts, friends,
  followers, followings, groups, games, favorite_games, badges, username_history,
  avatar_assets, promotion_channels (values null without a cookie), roblox_badges, presence.
- `group_snapshot(client, group_id, include=ALL)` tables: profile, roles, members
  (with role), allies, enemies, games, name_history, social_links (cookie only).
- `game_snapshot(client, universe_or_place_id)` tables: profile, votes, servers, badges,
  media, game_passes.
- `friend_network(client, user_id, depth=1, max_users=None)` returns nodes + edges.
  Depth 1 = the user's friends and their friends (what v1 `friend_edgelist` produced).
- `group_network(client, group_id, include_members=True, max_groups=None)` returns
  allies/enemies edgelists over the one-step neighbourhood, group profiles, membership
  edgelist (fixed: per-group, not seed-group), member profiles, favourite-game edgelist
  (fixed: full pagination, correct variable), and game profiles. This replaces
  `build_dataframes`.
- Progress via `logging` at INFO and an optional `tqdm` bar in the CLI.
- Compat: `build_dataframes(group_id, cookie=None, output_dir=".")` calls `group_network`
  and writes the same seven CSV names as v1. `group_edgelist(id)` and `friend_edgelist(id)`
  return the same shapes as v1.

### Export (`export.py`)

- `to_dataframe(records)` = `pd.json_normalize(records, sep="_")`, so `owner.userId`
  becomes the `owner_userId` column. Lists of scalars are joined with `;`; lists of objects
  are left as JSON strings so nothing is silently dropped.
- `Snapshot.save(out_dir, fmt="csv")` writes one file per table named
  `<entity>_<id>_<table>.csv` plus `<entity>_<id>_manifest.json` (counts, timestamps,
  omitted/truncated flags, errors). `fmt="json"` writes one JSON per table instead.
- `edgelist_to_graphml(edges, path)` for Gephi users.

### CLI (`cli.py`)

Designed for people who will paste commands from the docs. Every command prints a short
human summary and the path of each file it wrote. Global options: `--cookie`,
`--cookie-file`, `--output-dir/-o` (default `./roblox_data`), `--format csv|json`,
`--rate` (requests per second), `--quiet`, `--config`. `--stdout` prints JSON to the
terminal instead of writing files.

```
roblox check                              connectivity, rate, cookie validity
roblox resolve <url-or-username>          URL or username -> type + id
roblox user info|friends|followers|following|groups|games|favorites|badges|history|avatar|social <id-or-username>
roblox user snapshot <id-or-username> [--skip friends,...]
roblox user network <id> [--depth 1] [--max-users N]
roblox group info|members|roles|allies|enemies|games|history|wall|social <id>
roblox group snapshot <id>
roblox group network <id> [--no-members] [--max-groups N]
roblox game info|servers|votes|badges|passes <universe-id | --place <place-id>>
roblox game snapshot <id>
roblox search users|groups <keyword>
roblox batch users|groups <ids.txt>       one id per line -> one CSV of profiles
```

`<id-or-username>` accepts a numeric id, a username, or a roblox.com URL.

### Config (`config.py`)

Flat keys, same names everywhere: `cookie`, `cookie_file`, `output_dir`, `rate`,
`burst`, `max_retries`, `timeout`, `log_level`, `log_file`. Env vars are the same
names upper-cased with a `ROBLOX_` prefix. Config file: YAML or JSON with the flat keys.
Precedence: CLI flag > env var > config file > default.

### Packaging

`pyproject.toml` (setuptools backend) replaces `setup.py`. Runtime deps: `requests`,
`click`, `pandas`, `pyyaml`, `networkx`, `tqdm`. Dev extra: `pytest`. Python >= 3.9.
`.gitignore` added; `build/`, `*.egg-info`, `__pycache__`, `.DS_Store`, `.Rhistory`,
`*.orig`, duplicate cassette dir, and the root-level `__init__.py` removed from the tree.
`LICENSE` (MIT) added because the README and GitHub already claim it.

### Error handling

- Library: typed exceptions only, never bare `except`. Collectors never swallow
  `KeyboardInterrupt`.
- CLI: catches `RobloxError` subclasses and prints a one-line plain-English message
  (`User 12345 does not exist`, `Group 7 hides its social links; add a cookie`,
  `Roblox is rate limiting us; try again in a minute`) and exits 1. Unexpected exceptions
  show the traceback only with `--debug`.

### Testing

- Unit tests use an injected `FakeSession` that maps `(method, url)` to canned JSON
  captured from the live probe on 2026-09-28. No network in the default test run.
- Each API method has a test asserting the exact URL and params it sends.
- Collector tests cover the omission policy, pagination, and the two v1 data bugs.
- CLI tests use `CliRunner` and assert files written and summaries printed.
- `tests/live/` runs a handful of real calls (user 1, group 7, universe 1818) when
  `ROBLOX_LIVE_TESTS=1`; it is the check that Roblox has not changed a response shape.

## Endpoint coverage

See `docs/roblox-endpoints.md` for the full table from the live probe on 2026-09-28,
including which endpoints need a cookie and which legacy ones are dead. Deviations
from the first draft of this spec that the probe forced: group wall posts are gone
(404), presence works without a cookie, followers/followings and user badge lists now
need one, the friends list returns ids with blank names (hydrated via the batch users
endpoint), and the favourite-games endpoint rejects `sortOrder=Asc`.

## Out of scope

- Google Sheets/Drive archiving daemon (stays in `tg_archiver`).
- Any write action on Roblox (joining groups, sending requests, posting).
- Scraping data that requires the target's consent or a logged-in friend relationship
  (private inventories, friends-only servers).
- Async client.

## Addendum, 2026-09-30: merge with the March 2026 rewrite

When this work was pushed, `origin/main` already carried a second, independent
2.0 rewrite from March 2026 (`src/pyroblox`: httpx + Pydantic v2 models, Python
3.10+, 109 tests, no CLI, endpoints not live-verified). The user chose to merge
the two designs rather than pick one. Decisions:

- Package name and layout from March: `pyroblox` under `src/`, hatchling,
  Python >= 3.10, ruff and mypy config. `robloxwrapper` becomes a shim.
- Typed Pydantic models on every API method (March style, `extra="allow"`,
  camelCase aliases), returned as models or `PagedList[Model]`. CSV export
  converts with `model_dump(by_alias=True, mode="json")`, so column names are
  unchanged.
- March's `get_*` method names are canonical (`client.users.get_info`,
  `client.groups.get_members`). `client.catalog` replaces `client.assets`
  (kept as an alias).
- The HTTP core stays on `requests` with this document's client internals
  (header-driven pacing, per-host throttle, CSRF, cookie scoping, row
  pagination, injectable clock). Added from March: context manager, jittered
  backoff, `AuthenticationError` parent for 401/403, the exception aliases
  `PyRobloxError`, `RobloxAPIError`, `RateLimitError`, and
  `pyroblox.contrib.edgelists` / `pyroblox.contrib.dataframes` entry points.
- Dropped: httpx and the pytest-httpx tests; the leftover broken v1 modules
  that March had kept beside `src/`.
