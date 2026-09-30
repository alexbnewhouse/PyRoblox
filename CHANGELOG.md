# Changelog

All notable changes to PyRoblox. The format follows [Keep a Changelog](https://keepachangelog.com/).

## 2.0.0 - 2026-09-28

A rewrite. The import name (`robloxwrapper`) and the three documented v1
functions are kept; everything else is new. See `docs/AUDIT-2026-09-28.md` for
the audit that motivated it.

### Added

- `RobloxClient`, one object that owns the HTTP session, the optional
  `.ROBLOSECURITY` cookie, a per-host rate limiter, retries with backoff, and
  pagination helpers (`paginate`, `fetch_all`, `fetch_rows`). It reads Roblox's
  `x-ratelimit-*` headers and pauses before hitting a per-endpoint quota,
  honours `Retry-After`, handles the CSRF token dance for POSTs, and sends the
  cookie only to `*.roblox.com` hosts.
- Domain APIs on the client: `users`, `friends`, `groups`, `games`, `badges`,
  `avatar`, `inventory`, `account`, `presence`, `thumbnails`, `assets`, covering
  about sixty verified public endpoints. New data compared with v1: batch
  id-to-name lookup, username resolution and history, user search with
  previous usernames, follower and following counts, group roles and role
  members, group batch lookup, group name history and search, a user's groups
  and primary group, place-to-universe resolution, game votes, favourites count,
  public servers, places, media, game passes, universe badges, avatar and worn
  items, collectibles and inventory by type, Roblox badges, promotion channels,
  presence, thumbnails with download, economy and catalog asset details.
- Typed exceptions: `RobloxError`, `NotFoundError`, `PrivateError`,
  `AuthRequiredError`, `BadRequestError` (carrying Roblox's message),
  `RateLimitedError`, `ServerError`, `EntityUnavailable`.
- Collectors returning a `Snapshot`: `user_snapshot`, `group_snapshot`,
  `game_snapshot`, `friend_network`, `group_network`. Best-effort policy: the
  primary lookup must succeed; refused secondary tables are recorded in the
  manifest and collection continues; rate-limit and server errors propagate.
- `Snapshot.save()` writes one CSV (or JSON) per table plus a manifest with
  timestamps, counts, omissions, truncations, and errors. Nested JSON is
  flattened to columns (`owner_userId`), lists of scalars are `;`-joined, lists
  of objects are kept as JSON text.
- `roblox` command line tool with `check`, `resolve`, `user`, `group`, `game`,
  `search`, and `batch` groups; accepts ids, usernames, or roblox.com links;
  writes CSV by default; prints plain-language errors; `--stdout`, `--format
  json`, `--only`/`--skip`, `--max*` caps, `--graphml` for Gephi.
- `parse_roblox_url()` for profile, group, community, game, catalog, library,
  badge, and bundle links, plus `type:id` shorthand.
- Configuration via flags, `ROBLOX_*` environment variables, or a YAML/JSON file
  (`RobloxConfig`, `load_config`), including `cookie_file`.
- `robloxwrapper.legacy` with the v1 classes `friends`, `groups`, `group_games`,
  `user_games` as deprecated shims.
- Tests: 306 unit tests with a fake HTTP session; no network needed.
- Documentation: getting-started guide for non-programmers, CLI reference, data
  dictionary, Python API guide, endpoint and rate-limit reference, responsible
  use guide, audit report, `LICENSE` (MIT), `.gitignore`, `pyproject.toml`.

### Changed

- Public API. `from robloxwrapper import RobloxClient` replaces the module-level
  `sess` and the `friends(id)` / `groups(id)` classes.
- Methods return Roblox's JSON as plain dicts and lists. No dataclasses pin
  field names, so a field Roblox adds or renames no longer breaks collection.
- Config keys are flat and identical everywhere (`cookie`, `cookie_file`,
  `output_dir`, `rate`, `burst`, `max_retries`, `timeout`, `log_level`,
  `log_file`). Precedence: flag, then environment, then file, then default.
- Rate limiting is a per-host token bucket (default 1 request per second, burst
  5) plus header-driven quota pauses, instead of `time.sleep(60)` on any error.
- `build_dataframes()` now takes an optional cookie (string or v1-style dict),
  an `output_dir`, and returns the DataFrames; it still writes the seven v1 file
  names. `friend_edgelist()` and `group_edgelist()` keep their shapes.
- Packaging moved to `pyproject.toml`; distribution `PyRoblox`, import
  `robloxwrapper`, console script `roblox`. Runtime dependencies: `requests`,
  `click`, `pandas`, `pyyaml`, `networkx`. Python 3.9 or newer.
- Group profiles in `group_network` come from the relationship responses and the
  batch endpoint; the single-group GET (7 calls per minute) is used only for the
  seed group.

### Fixed

- `membership_<id>_edgelist.csv` assigned the seed group's members to every
  group in the network (the loop fetched `groups(group_id)` instead of
  `groups(i)`). Each group's own members are now collected and the group id on
  every edge is tested.
- `asset_el<id>.csv` was built from the last raw API response instead of the
  accumulated `[user, game]` list, so it contained no edges; and favourites were
  fetched two pages at most. The edge list is now complete and fully paginated.
- The favourites request sent `sortOrder=Asc`, which Roblox now rejects with
  HTTP 400. No sort order is sent.
- Bare `except:` around every request looped forever on deleted groups and
  banned users and swallowed Ctrl-C. Errors are typed, omissions are recorded,
  and `KeyboardInterrupt` is never caught.
- Group info key filtering raised `KeyError` on Roblox error bodies before the
  error check could run.
- The uncommitted working tree did not import (`__init__.py` referenced modules
  that did not exist) and its client targeted `https://api.roblox.com`, a host
  with no DNS record, using invented endpoints.
- `requirements.txt` listed `time==1.0.0`, which is not a package, so it could
  not be installed.
- Friend lists include placeholder entries with id `-1` for deleted accounts;
  they are kept in the `friends` table but excluded from friend networks.
- Roblox's bare-string 400 bodies are surfaced in error messages and manifests.

### Removed

- The dataclass models (`UserInfo`, `GroupInfo`, `SocialLink`, `AssetInfo`,
  `AssetVersion`, `GameInfo`, `GameVersion`, `GameStats`).
- The invented `AssetsClient` and `GamesClient` endpoints.
- `analysis.py`, `build_dataframes.py.orig`, the vcr cassettes and `vcrpy`
  dependency, `setup.py`, `requirements.txt`.
- Committed build artefacts: `build/`, `PyRoblox.egg-info/`, `__pycache__/`,
  `.DS_Store`, `.Rhistory`, the duplicate `tests/tests/` directory, and the
  root-level `__init__.py`.

## 1.0 - 2024-09-30

Original release: `friends` and `groups` classes returning raw JSON,
`friend_edgelist`, `group_edgelist`, and the `build_dataframes` "master
function" that wrote seven CSV files for a group's ally and enemy network.
