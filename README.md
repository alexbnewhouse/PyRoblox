# pyroblox

A Python wrapper for the Roblox Web API designed for researchers studying online social platforms. Provides typed responses, automatic rate-limit handling, cursor-based pagination, and high-level utilities for social network analysis.

> **Roblox's API is publicly accessible and does not require a developer account.** Its rate limits are generous. Please use common sense when querying so this remains available for open research.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Authentication](#authentication)
- [API Reference](#api-reference)
  - [Users](#users-clientusers)
  - [Groups](#groups-clientgroups)
  - [Friends](#friends-clientfriends)
  - [Games](#games-clientgames)
  - [Badges](#badges-clientbadges)
  - [Inventory](#inventory-clientinventory)
  - [Catalog](#catalog-clientcatalog)
  - [Avatar](#avatar-clientavatar)
  - [Thumbnails](#thumbnails-clientthumbnails)
- [Pagination](#pagination)
- [Social Network Analysis](#social-network-analysis)
  - [Edgelists](#edgelists)
  - [DataFrames & CSV Export](#dataframes--csv-export)
- [Error Handling](#error-handling)
- [Client Configuration](#client-configuration)
- [Development](#development)
- [License](#license)

## Installation

Requires **Python 3.10+**.

```bash
pip install pyroblox
```

For social network analysis features (pandas DataFrames, CSV export):

```bash
pip install pyroblox[analysis]
```

To install from source:

```bash
git clone https://github.com/yourusername/PyRoblox.git
cd PyRoblox
pip install -e ".[dev,analysis]"
```

## Quick Start

```python
from pyroblox import RobloxClient

# Use as a context manager so the HTTP session is cleaned up automatically
with RobloxClient() as client:
    # Look up a user
    user = client.users.get_info(1)
    print(f"{user.name} (created {user.created})")

    # Get group info
    group = client.groups.get_info(5351020)
    print(f"{group.name} — {group.member_count} members")

    # List a user's friends
    friends = client.friends.get_friends(724484845)
    for f in friends:
        print(f.name)

    # Paginated endpoints return lazy iterators — pages are fetched on demand
    for member in client.groups.get_members(5351020, max_pages=3):
        print(member.user.username, member.role.name if member.role else "")
```

All responses are **Pydantic models** with full IDE autocomplete and type safety. Unknown fields from the API are captured automatically and never cause errors.

## Authentication

Most read endpoints work without authentication. Some (like group social links) require your `.ROBLOSECURITY` cookie:

```python
client = RobloxClient(cookie="your_roblosecurity_cookie")
links = client.groups.get_social_links(5351020)
```

**How to get your cookie:** Log in to roblox.com, open browser DevTools, go to Application > Cookies, and copy the `.ROBLOSECURITY` value. Keep this secret — it grants full access to your account.

## API Reference

### Users (`client.users`)

```python
# Single user lookup
user = client.users.get_info(1)
# user.id, user.name, user.display_name, user.description,
# user.created, user.is_banned, user.has_verified_badge

# Batch lookup (up to 100 users per call)
users = client.users.get_batch([1, 2, 3])

# Search by keyword
results = client.users.search("builderman", limit=10)
```

### Groups (`client.groups`)

```python
# Group details
group = client.groups.get_info(5351020)
# group.id, group.name, group.description, group.owner,
# group.member_count, group.public_entry_allowed, group.has_verified_badge

# Relationships
allies = client.groups.get_allies(5351020)    # list[Group]
enemies = client.groups.get_enemies(5351020)  # list[Group]

# Members (paginated — lazy iterator)
for member in client.groups.get_members(5351020, max_pages=5):
    print(member.user.username, member.role.name if member.role else "")

# Roles
roles = client.groups.get_roles(5351020)  # list[GroupRole]

# Social links (requires authentication)
links = client.groups.get_social_links(5351020)  # list[SocialLink]
```

### Friends (`client.friends`)

```python
# Full friends list (not paginated — Roblox caps at 200 friends)
friends = client.friends.get_friends(724484845)  # list[Friend]

# Friend count
count = client.friends.get_count(724484845)  # int

# Followers and followings (paginated — lazy iterators)
for follower in client.friends.get_followers(724484845, max_pages=3):
    print(follower.name)

for following in client.friends.get_followings(724484845, max_pages=3):
    print(following.name)
```

### Games (`client.games`)

```python
# Games by universe ID (up to 50)
games = client.games.get_info([3260590327])
# game.id, game.name, game.description, game.creator,
# game.place_visits, game.playing, game.max_players, game.genre,
# game.created, game.updated

# Games created by a user or group (paginated)
for game in client.games.get_user_games(724484845):
    print(game.name, game.place_visits)

for game in client.games.get_group_games(5351020):
    print(game.name)

# User's favorite games (paginated)
for game in client.games.get_user_favorites(724484845, max_pages=2):
    print(game.name)

# Upvote/downvote counts
votes = client.games.get_votes([3260590327])
# votes[0].up_votes, votes[0].down_votes

# Favorites count
fav_count = client.games.get_favorites_count(3260590327)

# Live server list with player counts (paginated)
for server in client.games.get_servers(606849621, max_pages=1):
    print(server.playing, server.max_players, server.fps)
```

### Badges (`client.badges`)

```python
# Single badge details
badge = client.badges.get_info(100)
# badge.id, badge.name, badge.description, badge.statistics,
# badge.statistics.awarded_count, badge.statistics.win_rate_percentage

# All badges for a game (paginated)
for badge in client.badges.get_universe_badges(3260590327, max_pages=3):
    print(badge.name, badge.statistics.awarded_count if badge.statistics else 0)

# Badges earned by a user (paginated)
for badge in client.badges.get_user_badges(724484845, max_pages=5):
    print(badge.name)

# When were specific badges earned?
dates = client.badges.get_awarded_dates(724484845, [100, 200])
for d in dates:
    print(d.badge_id, d.awarded_date)
```

### Inventory (`client.inventory`)

```python
# Check if a user's inventory is public
if client.inventory.can_view(724484845):
    # Collectible/limited items
    for item in client.inventory.get_collectibles(724484845, max_pages=3):
        print(item.name, item.recent_average_price)

    # Inventory by asset type (8=Hat, 11=Shirt, 12=Pants, etc.)
    for item in client.inventory.get_user_inventory(724484845, 8, max_pages=2):
        print(item.name)

# Who owns a specific asset? (paginated)
for owner in client.inventory.get_asset_owners(1234567, max_pages=1):
    print(owner.owner.name if owner.owner else "Hidden")
```

### Catalog (`client.catalog`)

```python
# Search the marketplace with filters
for item in client.catalog.search(keyword="hat", min_price=0, max_price=100, max_pages=1):
    print(item.name, item.price, item.creator_name)

# Batch item details
details = client.catalog.get_item_details([
    {"itemType": "Asset", "id": 1234},
    {"itemType": "Bundle", "id": 567},
])

# Bundle info
bundle = client.catalog.get_bundle(500)
bundles = client.catalog.get_bundles([500, 501])

# Favorite counts
print(client.catalog.get_asset_favorite_count(1234))
print(client.catalog.get_bundle_favorite_count(500))

# Bundle recommendations
recs = client.catalog.get_bundle_recommendations(500)
```

### Avatar (`client.avatar`)

```python
# What a user is wearing (assets, colors, scales)
avatar = client.avatar.get_avatar(1)
# avatar.player_avatar_type, avatar.body_colors, avatar.scales, avatar.assets
for asset in avatar.assets or []:
    print(asset.name, asset.asset_type.name if asset.asset_type else "")

# Just the asset IDs
wearing = client.avatar.get_currently_wearing(1)  # [100, 200, 300]

# Saved outfits (paginated)
for outfit in client.avatar.get_outfits(1, max_pages=1):
    print(outfit.name)
```

### Thumbnails (`client.thumbnails`)

```python
# User headshots and full avatars (batch, up to 100)
headshots = client.thumbnails.get_user_headshots([1, 2, 3], size="150x150")
avatars = client.thumbnails.get_user_avatars([1, 2, 3])

# Asset, game, group, and badge thumbnails
asset_thumbs = client.thumbnails.get_asset_thumbnails([1234])
game_icons = client.thumbnails.get_game_icons([3260590327])
group_icons = client.thumbnails.get_group_icons([5351020])
badge_icons = client.thumbnails.get_badge_icons([100, 200])

# Each returns list[Thumbnail] with .target_id, .state, .image_url
for t in headshots:
    print(t.target_id, t.image_url)
```

## Pagination

Endpoints that return large result sets use Roblox's cursor-based pagination. pyroblox wraps these as **lazy iterators** — pages are only fetched as you consume items:

```python
# Iterate all members (fetches pages on demand)
for member in client.groups.get_members(5351020):
    print(member.user.username)

# Limit how many pages are fetched with max_pages
for member in client.groups.get_members(5351020, max_pages=5):
    print(member.user.username)

# Collect into a list (fetches everything — use max_pages to bound)
all_members = list(client.groups.get_members(5351020, max_pages=10))
```

Paginated methods: `get_members`, `get_followers`, `get_followings`, `get_user_games`, `get_group_games`, `get_user_favorites`, `get_servers`, `get_universe_badges`, `get_user_badges`, `get_collectibles`, `get_user_inventory`, `get_asset_owners`, `search` (catalog), `get_outfits`.

## Social Network Analysis

The `pyroblox.contrib` module provides high-level utilities for building social network datasets. Requires the `analysis` extra (`pip install pyroblox[analysis]`).

### Edgelists

Build `(source, target)` edgelists suitable for NetworkX, igraph, or any graph library:

```python
from pyroblox import RobloxClient
from pyroblox.contrib.edgelists import group_edgelist, friend_edgelist

with RobloxClient() as client:
    # Group alliance/enemy network — 2-hop traversal by default
    edges = group_edgelist(client, 5351020, depth=2)
    print(edges["allies"])   # [(5351020, 123), (5351020, 456), (123, 789), ...]
    print(edges["enemies"])  # [(5351020, 111), ...]

    # Friend network — 2-hop traversal
    friend_edges = friend_edgelist(client, 724484845, depth=2)
    # [(724484845, 111), (724484845, 222), (111, 333), ...]
```

Load into NetworkX:

```python
import networkx as nx

G = nx.DiGraph()
G.add_edges_from(friend_edges)
print(f"Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")
```

### DataFrames & CSV Export

Build a comprehensive dataset with a single call:

```python
from pyroblox import RobloxClient
from pyroblox.contrib.dataframes import build_network_dataframes

with RobloxClient() as client:
    dfs = build_network_dataframes(client, 5351020, output_dir="./output")
```

This returns a dict of pandas DataFrames and optionally writes CSVs:

| Key | Description |
|-----|-------------|
| `"allies"` | Group ally edges `(source_id, target_id)` |
| `"enemies"` | Group enemy edges `(source_id, target_id)` |
| `"group_info"` | Group metadata (one row per group) |
| `"membership"` | Group-user membership pairs `(group_id, user_id)` |
| `"user_info"` | User profiles (one row per user) |
| `"favorites"` | User-game favorite pairs `(user_id, game_id)` |
| `"game_info"` | Game metadata (one row per game) |

## Error Handling

pyroblox raises structured exceptions for API errors:

```python
from pyroblox import RobloxClient, NotFoundError, RateLimitError, AuthenticationError

with RobloxClient() as client:
    try:
        user = client.users.get_info(999999999999)
    except NotFoundError:
        print("User does not exist")
    except RateLimitError as e:
        print(f"Rate limited — retry after {e.retry_after}s")
    except AuthenticationError:
        print("Authentication required or invalid cookie")
```

**Exception hierarchy:**

```
PyRobloxError                  # Base for all pyroblox errors
└── RobloxAPIError             # API returned an error response
    ├── RateLimitError         # HTTP 429 — includes retry_after
    ├── AuthenticationError    # HTTP 401/403
    └── NotFoundError          # HTTP 404
```

Rate limits and server errors (5xx) are retried automatically with exponential backoff before raising. You only see these exceptions after all retries are exhausted.

## Client Configuration

```python
client = RobloxClient(
    cookie=None,          # .ROBLOSECURITY cookie for authenticated endpoints
    max_retries=5,        # Number of retries on 429/5xx/transport errors
    base_delay=1.0,       # Initial backoff delay in seconds
    max_delay=120.0,      # Maximum backoff delay cap
    timeout=30.0,         # HTTP request timeout in seconds
)
```

**Logging:** pyroblox uses Python's standard `logging` module. Enable debug logging to see retry attempts and request details:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Development

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev,analysis]"

# Run tests
pytest

# Lint and format
ruff check src/
ruff format src/

# Type check
mypy src/
```

## License

MIT
