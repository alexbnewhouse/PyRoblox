"""PyRoblox: pull public Roblox data into CSV files or pandas DataFrames.

Quick start::

    from robloxwrapper import RobloxClient, user_snapshot

    client = RobloxClient()                       # add cookie="..." for cookie-only data
    client.users.get(261)                         # one user, as a dict
    client.groups.members(7, max_items=500)       # paginated list
    snap = user_snapshot(client, 261)             # everything about a user
    snap.save("roblox_data")                      # one CSV per table + manifest

Command line (after ``pip install .``)::

    roblox user snapshot Shedletsky
    roblox group network 7 -o my_folder

See ``docs/`` for the full guide.
"""

from .client import PagedList, RobloxClient, chunked
from .collect import (
    GAME_TABLES,
    GROUP_TABLES,
    USER_TABLES,
    build_dataframes,
    friend_edgelist,
    friend_network,
    game_snapshot,
    group_edgelist,
    group_network,
    group_snapshot,
    user_snapshot,
)
from .config import RobloxConfig, load_config
from .errors import (
    AuthRequiredError,
    BadRequestError,
    EntityUnavailable,
    NotFoundError,
    PrivateError,
    RateLimitedError,
    RobloxError,
    ServerError,
)
from .export import Snapshot, edgelist_to_graphml, flatten, to_dataframe, write_records
from .urls import parse_roblox_url

__version__ = "2.0.0"

__all__ = [
    "RobloxClient", "PagedList", "chunked",
    "RobloxConfig", "load_config",
    "Snapshot", "to_dataframe", "flatten", "write_records", "edgelist_to_graphml",
    "parse_roblox_url",
    "user_snapshot", "group_snapshot", "game_snapshot",
    "friend_network", "group_network",
    "build_dataframes", "group_edgelist", "friend_edgelist",
    "USER_TABLES", "GROUP_TABLES", "GAME_TABLES",
    "RobloxError", "NotFoundError", "PrivateError", "AuthRequiredError",
    "BadRequestError", "RateLimitedError", "ServerError", "EntityUnavailable",
    "__version__",
]
