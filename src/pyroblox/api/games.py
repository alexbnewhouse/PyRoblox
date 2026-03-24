"""Interface to games.roblox.com endpoints."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from pyroblox import _endpoints as ep
from pyroblox.models.games import Game, GameServer, GameVotes
from pyroblox.pagination import paginate_endpoint

if TYPE_CHECKING:
    from pyroblox.client import RobloxClient


class GamesAPI:
    """Methods for the Roblox Games API."""

    def __init__(self, client: RobloxClient) -> None:
        self._client = client

    def get_group_games(
        self, group_id: int, *, limit: int = 100, max_pages: int | None = None
    ) -> Iterator[Game]:
        """Lazily iterate games created by a group."""
        path = ep.GROUP_GAMES.format(group_id=group_id)
        return paginate_endpoint(
            self._client, "games", path, Game,
            limit=limit, max_pages=max_pages,
            extra_params={"accessFilter": "All", "sortOrder": "Asc"},
        )

    def get_user_games(
        self, user_id: int, *, limit: int = 50, max_pages: int | None = None
    ) -> Iterator[Game]:
        """Lazily iterate games created by a user."""
        path = ep.USER_GAMES.format(user_id=user_id)
        return paginate_endpoint(
            self._client, "games", path, Game,
            limit=limit, max_pages=max_pages,
            extra_params={"accessFilter": "All", "sortOrder": "Asc"},
        )

    def get_user_favorites(
        self, user_id: int, *, limit: int = 50, max_pages: int | None = None
    ) -> Iterator[Game]:
        """Lazily iterate a user's favorite games."""
        path = ep.USER_FAVORITE_GAMES.format(user_id=user_id)
        return paginate_endpoint(
            self._client, "games", path, Game,
            limit=limit, max_pages=max_pages,
        )

    def get_info(self, universe_ids: list[int]) -> list[Game]:
        """Get information about games by universe IDs.

        Args:
            universe_ids: List of universe IDs (up to 50).
        """
        resp = self._client.get(
            "games", ep.GAME_INFO,
            params={"universeIds": ",".join(str(uid) for uid in universe_ids)},
        )
        data = resp.json()
        return [Game.model_validate(g) for g in data.get("data", [])]

    def get_votes(self, universe_ids: list[int]) -> list[GameVotes]:
        """Get upvote/downvote counts for games.

        Args:
            universe_ids: List of universe IDs (up to 50).
        """
        resp = self._client.get(
            "games", ep.GAME_VOTES,
            params={"universeIds": ",".join(str(uid) for uid in universe_ids)},
        )
        data = resp.json()
        return [GameVotes.model_validate(v) for v in data.get("data", [])]

    def get_favorites_count(self, universe_id: int) -> int:
        """Get the number of favorites for a game."""
        path = ep.GAME_FAVORITES_COUNT.format(universe_id=universe_id)
        resp = self._client.get("games", path)
        return resp.json().get("favoritesCount", 0)  # type: ignore[no-any-return]

    def get_servers(
        self,
        place_id: int,
        *,
        server_type: int = 0,
        limit: int = 100,
        max_pages: int | None = None,
    ) -> Iterator[GameServer]:
        """Lazily iterate game servers with player counts.

        Args:
            place_id: The place ID to query servers for.
            server_type: 0=Public, 1=Friend, 2=VIP.
            limit: Servers per page.
            max_pages: Safety limit on total pages fetched.
        """
        path = ep.GAME_SERVERS.format(
            place_id=place_id, server_type=server_type
        )
        return paginate_endpoint(
            self._client, "games", path, GameServer,
            limit=limit, max_pages=max_pages,
            extra_params={"sortOrder": "Desc"},
        )
