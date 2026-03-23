# pyroblox

Python wrapper for the Roblox API with typed responses, rate-limit handling, and automatic pagination.

## Notes

Roblox's API does not require a developer account. Its endpoints are exposed to the public, and its rate limits are generous. Please use common sense when using this so we can continue researching Roblox data in such an open capacity.

## Installation

```bash
pip install pyroblox
```

For social network analysis features (DataFrames, CSV export):

```bash
pip install pyroblox[analysis]
```

## Quick Start

```python
from pyroblox import RobloxClient

with RobloxClient() as client:
    # Get group info
    group = client.groups.get_info(5351020)
    print(group.name, group.member_count)

    # Get a user's friends
    friends = client.friends.get_friends(724484845)
    for f in friends:
        print(f.name, f.display_name)

    # Paginated endpoints are lazy iterators
    for member in client.groups.get_members(5351020, max_pages=5):
        print(member.user.username)
```

### Authentication

Some endpoints (like social links) require authentication via your ROBLOSECURITY cookie:

```python
client = RobloxClient(cookie="your_roblosecurity_cookie")
links = client.groups.get_social_links(5351020)
```

## API Coverage

### Groups (`client.groups`)
- `get_info(group_id)` — Group details
- `get_allies(group_id)` — Allied groups
- `get_enemies(group_id)` — Enemy groups
- `get_members(group_id)` — Group members (paginated)
- `get_roles(group_id)` — Group roles
- `get_social_links(group_id)` — Social links (requires auth)

### Users (`client.users`)
- `get_info(user_id)` — User profile
- `get_batch(user_ids)` — Bulk user lookup (up to 100)
- `search(keyword)` — Search users

### Friends (`client.friends`)
- `get_friends(user_id)` — Friends list
- `get_count(user_id)` — Friend count
- `get_followers(user_id)` — Followers (paginated)
- `get_followings(user_id)` — Followings (paginated)

### Games (`client.games`)
- `get_group_games(group_id)` — Group's games (paginated)
- `get_user_games(user_id)` — User's games (paginated)
- `get_user_favorites(user_id)` — Favorite games (paginated)
- `get_info(universe_ids)` — Game details by universe ID

## Social Network Analysis

Build edgelists and DataFrames for network analysis (requires `pyroblox[analysis]`):

```python
from pyroblox import RobloxClient
from pyroblox.contrib.edgelists import group_edgelist, friend_edgelist
from pyroblox.contrib.dataframes import build_network_dataframes

with RobloxClient(cookie="...") as client:
    # Group relationship network (2-hop)
    edges = group_edgelist(client, 5351020)
    # edges["allies"] = [(from_id, to_id), ...]
    # edges["enemies"] = [(from_id, to_id), ...]

    # Friend network (2-hop)
    friend_edges = friend_edgelist(client, 724484845)

    # Full dataset: edgelists, group info, user info, favorites → DataFrames + CSVs
    dfs = build_network_dataframes(client, 5351020, output_dir="./output")
```

## Features

- **Typed responses** — Pydantic models with IDE autocomplete
- **Schema-flexible** — New API fields are captured automatically, never cause errors
- **Rate-limit handling** — Exponential backoff with jitter, respects Retry-After headers
- **Automatic pagination** — Lazy iterators for paginated endpoints
- **Bounded retries** — Configurable retry count (no infinite loops)

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check src/
```
