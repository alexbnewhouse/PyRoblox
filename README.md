# PyRoblox

Pull public Roblox data about users, groups, and games into CSV files or pandas
DataFrames. Built for trust-and-safety researchers, including people who do not
write code.

```
pip install "git+https://github.com/CTEC-MIIS/PyRoblox"

roblox user snapshot Shedletsky
roblox group network 7 --output-dir my_study
roblox game info https://www.roblox.com/games/1818/Classic-Crossroads
```

Every command writes plain CSV files you can open in Excel or Google Sheets, plus
a manifest that says exactly what was collected, what Roblox refused, and why.

## What you can collect

| About a user | About a group | About a game |
|---|---|---|
| profile (name, created, banned) | profile, roles, member count | profile, creator, visits, players |
| friends (with usernames) | full member list with roles | public servers running now |
| friend / follower counts | allies and enemies | votes and favourite count |
| groups and rank in each | games the group publishes | badges it awards |
| games published | name history | game passes, places, media |
| favourite games | social links (cookie) | |
| previous usernames | | |
| avatar and worn items | | |
| collectible inventory | | |
| Roblox badges, presence | | |
| followers, following, badges (cookie) | | |

Plus networks: `roblox user network` walks friend lists into an edge list, and
`roblox group network` maps a group's ally and enemy neighbourhood with the
membership of every group in it (the v1 "master function", with its data bugs
fixed). Both can write GraphML for Gephi.

Everything is public data that anyone can see on roblox.com. A `.ROBLOSECURITY`
cookie is optional and unlocks only the few endpoints marked "cookie" above.

## Documentation

- **[Getting started](docs/getting-started.md)**: install and first commands, written for non-programmers.
- **[Command reference](docs/cli-reference.md)**: every `roblox` command, option, and output file.
- **[Data dictionary](docs/data-dictionary.md)**: what each CSV column means.
- **[Python API](docs/python-api.md)**: using PyRoblox as a library, with recipes and a v1 migration guide.
- **[Roblox endpoints](docs/roblox-endpoints.md)**: which endpoints work without a cookie, their rate limits, and what is dead.
- **[Responsible use](docs/responsible-use.md)**: ethics, data protection, and reporting abuse.
- **[Audit, 2026-09-28](docs/AUDIT-2026-09-28.md)**: what was wrong with v1 and why v2 exists.
- **[Changelog](CHANGELOG.md)**

## Quick start (Python)

```python
from robloxwrapper import RobloxClient, user_snapshot, group_network

client = RobloxClient()                      # RobloxClient(cookie="...") for cookie-only data

user = client.users.get(261)                 # one user, as a dict
members = client.groups.members(7, max_items=500)   # paginated list with .truncated flag

snap = user_snapshot(client, 261)            # every table about a user
snap.save("roblox_data")                     # one CSV per table + manifest.json
frames = snap.to_dataframes()                # or work in pandas

net = group_network(client, 7, max_groups=20)
net["allies"]                                # [{"source": 7, "target": 8}, ...]
```

## Install

Requires Python 3.9 or newer.

```
pip install "git+https://github.com/CTEC-MIIS/PyRoblox"
roblox check
```

From a clone: `pip install -e .` then `python -m pytest` (306 tests, no network).

## Rate limits and good behaviour

Roblox limits each endpoint per IP address, from 1 call per minute (username
history, user search) to 10,000 per minute (role members). PyRoblox reads
Roblox's rate-limit headers and pauses on its own, retries with backoff, and
stops with a clear message if Roblox keeps refusing. Please do not run many
copies in parallel to get around this. See [Responsible use](docs/responsible-use.md).

## Upgrading from v1

The v1 functions `build_dataframes(group_id, cookie)`, `group_edgelist(id)`, and
`friend_edgelist(id)` still exist with the same signatures and output files.
Two of the seven v1 CSVs were wrong (see the audit); they are correct now. The old
`friends`, `groups`, `group_games`, and `user_games` classes live in
`robloxwrapper.legacy` and emit a deprecation warning.

## License

MIT. Copyright Center on Terrorism, Extremism, and Counterterrorism (CTEC),
Middlebury Institute of International Studies, and contributors.
