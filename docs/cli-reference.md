# Command reference

Every `roblox` command fetches something from Roblox, prints a one-line summary,
and writes the result to a file. Run `roblox --help` or `roblox user --help` for
the same information in the terminal.

## Global options

These go before the command name: `roblox -o data user info 261`.

| Option | Environment variable | Default | Meaning |
|---|---|---|---|
| `-c`, `--cookie TEXT` | `ROBLOX_COOKIE` | none | Your `.ROBLOSECURITY` cookie value. Unlocks the endpoints marked "cookie" below. |
| `--cookie-file FILE` | `ROBLOX_COOKIE_FILE` | none | A file containing the cookie. Safer than pasting it. |
| `-o`, `--output-dir DIR` | `ROBLOX_OUTPUT_DIR` | `roblox_data` | Folder for output files. Created if missing. |
| `-f`, `--format csv\|json` | | `csv` | File format for every table. |
| `--rate FLOAT` | `ROBLOX_RATE` | `1.0` | Requests per second per Roblox host. Lower it if you share a network. |
| `--config FILE` | | none | YAML or JSON file with any of the keys `cookie`, `cookie_file`, `output_dir`, `rate`, `burst`, `max_retries`, `timeout`, `log_level`, `log_file`. |
| `--stdout` | | off | Print JSON to the terminal instead of writing files. |
| `-q`, `--quiet` | | off | Suppress progress lines; print only results and errors. |
| `--debug` | | off | Show Python tracebacks and debug logging. |
| `--version` | | | Print the version and exit. |

Precedence when a setting is given more than once: command-line flag, then
environment variable, then config file, then the default.

A config file looks like this:

```yaml
# settings.yaml
output_dir: ~/roblox_study
cookie_file: ~/.roblox_cookie
rate: 0.5
```

```
roblox --config settings.yaml group snapshot 7
```

## Identifiers

- **Users** accept a numeric id (`261`), a username (`Shedletsky`), or a profile
  link (`https://www.roblox.com/users/261/profile`). Usernames are resolved with
  one extra request.
- **Groups** accept a numeric id or a `roblox.com/groups/<id>/...` or
  `roblox.com/communities/<id>/...` link. Group names are not unique, so names are
  not accepted; use `roblox search groups` to find the id.
- **Games** accept a universe id, or a `roblox.com/games/<placeId>/...` link, or a
  place id with `--place`. Links and `--place` are converted to the universe id
  with one extra request. Roblox uses two ids for every game; the one in the URL
  is the place id, and most data hangs off the universe id.

## `roblox check`

Tests the connection and your cookie.

```
roblox check
```

Prints the version, the output folder, whether Roblox answered, and whether the
cookie was accepted (`Cookie: valid, logged in as ...`), rejected, or absent.

## `roblox resolve VALUE`

Turns a link, a username, or a `type:id` string into an entity type and numeric id.

```
roblox resolve https://www.roblox.com/groups/7/Roblox        -> group 7
roblox resolve Shedletsky                                    -> user 261 (Shedletsky, ...)
roblox resolve https://www.roblox.com/games/1818/Crossroads  -> game: place 1818 belongs to universe 13058
```

A bare number is refused because it could be a user, group, or game id.

## `roblox user <command> WHO`

| Command | What it fetches | Output file | Notes |
|---|---|---|---|
| `info` | Profile: name, display name, description, created, banned, verified | `user_<id>_profile` | |
| `counts` | Friend, follower, and following counts | `user_<id>_counts` | |
| `friends` | Friend list with usernames | `user_<id>_friends` | Roblox returns ids only; names are looked up in one batch call. Deleted friends appear as id `-1`. `--max` |
| `followers` | Who follows the user | `user_<id>_followers` | Cookie. `--max` |
| `following` | Who the user follows | `user_<id>_followings` | Cookie. `--max` |
| `groups` | Groups the user is in, with role and rank | `user_<id>_groups` | `--max` |
| `games` | Experiences the user published | `user_<id>_games` | `--max` |
| `favorites` | Experiences the user favourited | `user_<id>_favorite_games` | Newest first. `--max` |
| `badges` | Badges earned in games | `user_<id>_badges` | Cookie. `--max` |
| `history` | Previous usernames | `user_<id>_username_history` | Roblox allows about one call per minute. `--max` |
| `avatar` | Items currently worn | `user_<id>_avatar_assets` | The summary also shows the avatar type (R6/R15). |
| `social` | Linked Facebook, X, YouTube, Twitch accounts | `user_<id>_promotion_channels` | Values are blank without a cookie. |
| `presence` | Online status and last location | `user_<id>_presence` | |
| `snapshot` | All of the above (see below) | one file per table + manifest | |
| `network` | Friend network edge list | `friend_network_<id>_edges`, `_nodes` | See below. |

Examples and the summary each prints:

```
roblox user info Shedletsky           Shedletsky (display name 'Shedletsky', id 261)
                                        created: 2006-06-22T01:33:56.45Z  banned: False  verified: True
roblox user friends 261               98 friend(s)
roblox user counts 261                friends 98, followers 2124380, following 457735
roblox user groups 261                33 group(s)
roblox user favorites 261 --max 50    50 favourite game(s)
roblox user presence 261              status: offline
```

Every command then prints `Wrote <n> row(s) to <path>`.

### `roblox user snapshot WHO`

Collects every table in one run.

| Option | Meaning |
|---|---|
| `--only a,b,c` | Collect only these tables (the profile is always collected). |
| `--skip a,b,c` | Collect everything except these. |
| `--max N` | Cap rows in each paginated table. Capped tables are marked truncated in the manifest. |

Table names: `profile`, `counts`, `friends`, `followers`\*, `followings`\*,
`groups`, `games`, `favorite_games`, `badges`\*, `username_history`, `avatar`
(writes `avatar` and `avatar_assets`), `collectibles`, `roblox_badges`,
`promotion_channels`\*, `presence`. Starred tables need a cookie and are
reported as skipped without one.

```
roblox user snapshot Shedletsky --skip collectibles,presence --max 500
```

### `roblox user network WHO`

| Option | Default | Meaning |
|---|---|---|
| `--depth N` | 1 | 1 fetches the user's friends; 2 also fetches each friend's friends. |
| `--max-users N` | none | Stop after fetching this many friend lists. |
| `--graphml` | off | Also write `friend_network_<id>.graphml` for Gephi. |

Roblox allows about 20 friend-list calls per minute, so depth 2 on a user with
200 friends takes about ten minutes. Edges are undirected and deduplicated.
Deleted friends (id `-1`) are counted in the manifest but not added to the graph.

## `roblox group <command> WHICH`

| Command | What it fetches | Output file | Notes |
|---|---|---|---|
| `info` | Profile: name, owner, member count, description, locked flag | `group_<id>_profile` | Roblox allows about 7 of these per minute. |
| `members` | Every member with role and rank | `group_<id>_members` | About 100 members per second. `--max` |
| `roles` | Roles (ranks) and how many members hold each | `group_<id>_roles` | |
| `allies` | Allied groups (full profiles) | `group_<id>_allies` | Locked groups are refused by Roblox. `--max` |
| `enemies` | Enemy groups (full profiles) | `group_<id>_enemies` | `--max` |
| `games` | Experiences the group publishes | `group_<id>_games` | `--max` |
| `history` | Previous group names | `group_<id>_name_history` | `--max` |
| `social` | Discord, X, YouTube links | `group_<id>_social_links` | Cookie. |
| `snapshot` | All of the above | one file per table + manifest | Tables: `profile`, `roles`, `members`, `allies`, `enemies`, `games`, `name_history`, `social_links`\*. Same `--only`, `--skip`, `--max` options as the user snapshot. |
| `network` | Ally/enemy neighbourhood plus membership | see below | |

```
roblox group info 7                   Roblox (id 7)
                                        owner: Games (id 21557)  members: 13508012  locked: False
roblox group members 7 --max 1000     1000 member(s) (truncated by --max)
roblox group snapshot 7 --skip members
```

### `roblox group network WHICH`

This is the v1 "master function" (`build_dataframes`) with its bugs fixed.

| Option | Meaning |
|---|---|
| `--no-members` | Only map allies and enemies; skip member lists. |
| `--profiles` | Also fetch every member's full profile (created date, banned flag, description). About 30 per minute, so slow for big groups. |
| `--favorites` | Also fetch every member's favourite games. One call per member. |
| `--max-groups N` | Expand at most this many related groups. |
| `--max-members N` | Cap members fetched per group. |
| `--graphml` | Also write `group_network_<id>_allies.graphml` and `_enemies.graphml`. |

Steps: fetch the seed group's allies and enemies; fetch the allies and enemies of
each of those groups; fetch the member list of the seed group and every related
group. Tables written: `groups` (every group seen, with profile), `allies` and
`enemies` (`source`, `target` edges), `membership` (one row per group-member
pair), `members` (unique users), and with the flags `member_profiles`,
`favorite_games` (`userId`, `universeId` edges), and `games`.

```
roblox group network 5351020 --max-members 5000 --graphml
```

## `roblox game <command> WHICH`

All game commands accept `--place` to say that WHICH is a place id.

| Command | What it fetches | Output file | Notes |
|---|---|---|---|
| `info` | Profile: creator, visits, players online, created, genre | `game_<universe>_profile` | |
| `votes` | Up votes, down votes, favourite count | `game_<universe>_votes` | |
| `servers` | Public servers running right now | `game_<universe>_servers` | Roblox allows about 3 calls per minute. Default cap 100 servers. `--max` |
| `badges` | Badges the experience awards, with award counts | `game_<universe>_badges` | `--max` |
| `passes` | Game passes (for sale or not) | `game_<universe>_game_passes` | |
| `places` | All places inside the experience | `game_<universe>_places` | `--max` |
| `snapshot` | All of the above plus `media` | one file per table + manifest | Tables: `profile`, `votes`, `places`, `servers`, `badges`, `media`, `game_passes`. Options `--only`, `--skip`, `--max-servers N` (default 100). |

```
roblox game info 13058                        Crossroads (universe 13058, root place 1818)
roblox game info 1818 --place                 Resolved place 1818 to universe 13058 ...
roblox game info https://www.roblox.com/games/1818/Classic-Crossroads
roblox game votes 13058                       up 93974  down 10715  favourites 316859
roblox game snapshot 1818 --place --max-servers 25
```

## `roblox search <users|groups> KEYWORD`

| Command | Notes |
|---|---|
| `search users KEYWORD` | Matches usernames. Each hit includes `previousUsernames`. Roblox allows about one search per minute. |
| `search groups KEYWORD` | Matches group names. Each hit includes `previousName`, `memberCount`, and `created`. |

Both take `--max N` (default 100) and write `search_users_<keyword>` or
`search_groups_<keyword>` (the keyword is reduced to letters, digits, and
underscores).

```
roblox search groups "roblox"          10 result(s)
```

## `roblox batch <users|groups> FILE`

Looks up many ids from a text file with one id or link per line. Blank lines
and lines starting with `#` are ignored.

| Command | Notes |
|---|---|
| `batch users FILE` | Usernames and display names for every id, in one fast batch call (1000 ids per second). Add `--full` to fetch complete profiles one by one (about 30 per minute) including `created`, `isBanned`, and `description`; rows Roblox refuses get an `error` column. |
| `batch groups FILE` | Basic profiles (name, description, owner, created) for group ids. |

Output file: `batch_users_<filename>` or `batch_groups_<filename>`.

```
roblox batch users suspects.txt        3 of 3 found
roblox batch users suspects.txt --full
```

## Output formats

- **CSV** (default). One row per record. Nested values are flattened into columns
  joined with `_` (`owner_userId`), lists of simple values are joined with `;`,
  and lists of objects are kept as JSON text in one cell. See
  [data-dictionary.md](data-dictionary.md).
- **JSON** (`--format json`). The records exactly as Roblox returned them, one
  file per table.
- **`--stdout`**. Prints JSON to the terminal and writes nothing. Useful for
  piping into other tools: `roblox --stdout user info 261 | jq .name`.

Snapshots and networks always write a `<entity>_<id>_manifest.json` beside the
tables with `captured_at`, per-table row counts, `omitted` (table name to
reason), `truncated`, `errors`, and `files`.

## Exit codes and errors

| Exit code | Meaning |
|---|---|
| 0 | Success. |
| 1 | A Roblox or PyRoblox error, explained in one line (not found, cookie needed, private, rate limited, Roblox server error, invalid request). |
| 2 | A usage error: unknown command, missing argument, bad option value. |

Inside a snapshot or network, a refused secondary table does not fail the run;
it is listed as skipped and recorded in the manifest. Only a failure to fetch
the main entity (the user, group, or game itself) exits with code 1.

Ctrl-C stops the run and keeps any files already written. Add `--debug` to see
the full traceback for a bug report.
