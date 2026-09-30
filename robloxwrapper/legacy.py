"""v1 class names kept so old notebooks keep running.

These wrap the v2 client and return the same raw JSON shapes that v1 returned.
They emit a :class:`DeprecationWarning`; new code should use
:class:`~robloxwrapper.RobloxClient` directly.
"""

from __future__ import annotations

import warnings
from typing import Any, Dict, Optional

from .client import RobloxClient

_default_client: Optional[RobloxClient] = None


def default_client() -> RobloxClient:
    """A process-wide client built from environment variables / config file."""
    global _default_client
    if _default_client is None:
        from .config import load_config
        _default_client = load_config().make_client()
    return _default_client


def set_default_client(client: Optional[RobloxClient]) -> None:
    global _default_client
    _default_client = client


def _warn(old: str, new: str) -> None:
    warnings.warn(f"robloxwrapper.{old} is deprecated; use {new}",
                  DeprecationWarning, stacklevel=3)


class friends:
    """v1: ``friends(user_id).info()`` and ``.user_info()``."""

    def __init__(self, id: int, client: Optional[RobloxClient] = None):
        _warn("friends", "RobloxClient().friends / .users")
        self.id = id
        self.client = client or default_client()

    def info(self) -> Dict[str, Any]:
        return {"data": self.client.friends.friends(self.id)}

    def user_info(self) -> Dict[str, Any]:
        return self.client.users.get(self.id)


class groups:
    """v1: ``groups(group_id).info()``, ``.allies()``, ``.enemies()``,
    ``.user_list(cursor)``, ``.social_links(cookies)``."""

    def __init__(self, id: int, client: Optional[RobloxClient] = None):
        _warn("groups", "RobloxClient().groups")
        self.id = id
        self.client = client or default_client()

    def info(self) -> Dict[str, Any]:
        return self.client.groups.get(self.id)

    def _relationships(self, kind: str) -> Dict[str, Any]:
        rows = getattr(self.client.groups, kind)(self.id)
        return {"groupId": self.id, "relationshipType": kind.capitalize(),
                "totalGroupCount": len(rows), "relatedGroups": list(rows),
                "nextRowIndex": len(rows)}

    def allies(self) -> Dict[str, Any]:
        return self._relationships("allies")

    def enemies(self) -> Dict[str, Any]:
        return self._relationships("enemies")

    def user_list(self, cursor: Optional[str] = None) -> Dict[str, Any]:
        params = {"sortOrder": "Asc", "limit": 100}
        if cursor:
            params["cursor"] = cursor
        return self.client.get(f"https://groups.roblox.com/v1/groups/{self.id}/users", params)

    def social_links(self, cookies: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        client = self.client
        if cookies and cookies.get(".ROBLOSECURITY") and not client.has_cookie:
            client = RobloxClient(cookies[".ROBLOSECURITY"])
        return {"data": client.groups.social_links(self.id)}


class group_games:
    """v1: ``group_games(group_id).info()``."""

    def __init__(self, id: int, client: Optional[RobloxClient] = None):
        _warn("group_games", "RobloxClient().games.group_games")
        self.id = id
        self.client = client or default_client()

    def info(self) -> Dict[str, Any]:
        return self.client.get(f"https://games.roblox.com/v2/groups/{self.id}/gamesV2",
                               {"sortOrder": "Asc", "limit": 100})


class user_games:
    """v1: ``user_games(user_id).games_list()`` and ``.favorites_list(cursor)``."""

    def __init__(self, id: int, client: Optional[RobloxClient] = None):
        _warn("user_games", "RobloxClient().games.user_games / .user_favorites")
        self.id = id
        self.client = client or default_client()

    def games_list(self) -> Dict[str, Any]:
        return self.client.get(f"https://games.roblox.com/v2/users/{self.id}/games",
                               {"sortOrder": "Asc", "limit": 50})

    def favorites_list(self, cursor: Optional[str] = None) -> Dict[str, Any]:
        # v1 sent sortOrder=Asc here; Roblox now rejects that with HTTP 400.
        params: Dict[str, Any] = {"limit": 50}
        if cursor is not None:
            params["cursor"] = cursor
        return self.client.get(f"https://games.roblox.com/v2/users/{self.id}/favorite/games", params)
