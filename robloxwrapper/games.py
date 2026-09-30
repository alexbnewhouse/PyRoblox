"""Game (experience) data from ``games.roblox.com``, with a few helpers that
live on sibling hosts: place-to-universe lookup on ``apis.roblox.com``, game
passes on ``apis.roblox.com``, a universe's places on ``develop.roblox.com``,
and a user's created places on ``inventory.roblox.com``. Roblox has two ids
for every game: the *universe* id (what most endpoints here take) and the
*place* id you see in game URLs; :meth:`GamesAPI.place_to_universe` converts
between them. Everything is public except :meth:`GamesAPI.place_details`,
which needs a ``.ROBLOSECURITY`` cookie."""

from __future__ import annotations

from typing import Iterable, List, Optional

from .client import PagedList, RobloxClient, chunked
from .errors import NotFoundError


class GamesAPI:
    """Read-only access to the games endpoints.

    All methods return Roblox's JSON as plain ``dict`` / ``list`` values with
    the obvious envelope (``data``, ``gamePasses``, ``favoritesCount``...)
    already unwrapped.
    """

    BASE = "https://games.roblox.com"
    APIS = "https://apis.roblox.com"
    DEVELOP = "https://develop.roblox.com"
    INVENTORY = "https://inventory.roblox.com"

    def __init__(self, client: RobloxClient):
        self.client = client

    def _multiget(self, path: str, universe_ids: Iterable[int]) -> List[dict]:
        """GET ``path?universeIds=a,b,c`` in chunks of 100 and concatenate ``data``."""
        url = f"{self.BASE}{path}"
        out: List[dict] = []
        for chunk in chunked(universe_ids, 100):
            body = self.client.get(url, {"universeIds": ",".join(str(i) for i in chunk)})
            out.extend(body.get("data") or [])
        return out

    # -- game objects ---------------------------------------------------------

    def get(self, universe_id: int) -> dict:
        """Return the game object for a universe id (rootPlaceId, name, creator, playing, visits, favoritedCount...); NotFoundError if Roblox returns nothing."""
        data = self._multiget("/v1/games", [universe_id])
        if not data:
            raise NotFoundError(f"universe {universe_id} not found", url=f"{self.BASE}/v1/games")
        return data[0]

    def batch_get(self, universe_ids: Iterable[int]) -> list:
        """Return the concatenated game objects for ``universe_ids``, 100 per call; unknown ids are silently omitted."""
        return self._multiget("/v1/games", universe_ids)

    def place_to_universe(self, place_id: int) -> int:
        """Return the universe id that owns ``place_id``; NotFoundError if Roblox answers null."""
        url = f"{self.APIS}/universes/v1/places/{place_id}/universe"
        body = self.client.get(url)
        universe_id = body.get("universeId") if isinstance(body, dict) else None
        if universe_id is None:
            raise NotFoundError(f"place {place_id} not found", url=url)
        return universe_id

    def get_by_place(self, place_id: int) -> dict:
        """Return the game object for a place id (the id in game URLs) by resolving its universe first."""
        return self.get(self.place_to_universe(place_id))

    # -- listings -------------------------------------------------------------

    def user_games(self, user_id: int, max_items: Optional[int] = None) -> PagedList:
        """Return the games a user has published (id, name, creator, rootPlace{id,type}, created, updated, placeVisits); Roblox caps this page size at 50."""
        return self.client.fetch_all(f"{self.BASE}/v2/users/{user_id}/games",
                                     limit=50, max_items=max_items, sort_order="Asc")

    def group_games(self, group_id: int, max_items: Optional[int] = None) -> PagedList:
        """Return the games a group has published (same shape as :meth:`user_games`); Roblox allows about 3 calls per second unauthenticated."""
        return self.client.fetch_all(f"{self.BASE}/v2/groups/{group_id}/gamesV2",
                                     limit=100, max_items=max_items, sort_order="Asc")

    def user_favorites(self, user_id: int, max_items: Optional[int] = None) -> PagedList:
        """Return the games a user has favorited (same shape as :meth:`user_games`, plus price).

        Roblox rejects ``sortOrder=Asc`` on this endpoint ("Ascending sort order is
        not supported"), so no sort order is sent; results come newest first.
        """
        return self.client.fetch_all(f"{self.BASE}/v2/users/{user_id}/favorite/games",
                                     limit=100, max_items=max_items)

    def servers(self, place_id: int, server_type: str = "Public",
                max_items: Optional[int] = None) -> PagedList:
        """Return the running servers of a PLACE id (not a universe id): id, maxPlayers, playing, playerTokens, players, fps, ping. Roblox allows about 3 calls per minute unauthenticated."""
        return self.client.fetch_all(f"{self.BASE}/v1/games/{place_id}/servers/{server_type}",
                                     limit=100, max_items=max_items, sort_order="Asc")

    # -- votes / favorites / media --------------------------------------------

    def votes(self, universe_id: int) -> dict:
        """Return ``{"id", "upVotes", "downVotes"}`` for a universe; NotFoundError if Roblox returns nothing."""
        data = self._multiget("/v1/games/votes", [universe_id])
        if not data:
            raise NotFoundError(f"universe {universe_id} not found",
                                url=f"{self.BASE}/v1/games/votes")
        return data[0]

    def batch_votes(self, universe_ids: Iterable[int]) -> list:
        """Return the concatenated vote records (id, upVotes, downVotes) for ``universe_ids``, 100 per call."""
        return self._multiget("/v1/games/votes", universe_ids)

    def favorites_count(self, universe_id: int) -> int:
        """Return how many users have favorited the universe."""
        body = self.client.get(f"{self.BASE}/v1/games/{universe_id}/favorites/count")
        return body["favoritesCount"]

    def media(self, universe_id: int) -> list:
        """Return the universe's media entries (assetTypeId, assetType, imageId, videoHash, approved, altText)."""
        body = self.client.get(f"{self.BASE}/v2/games/{universe_id}/media")
        return body.get("data") or []

    # -- other hosts ----------------------------------------------------------

    def game_passes(self, universe_id: int) -> list:
        """Return the universe's game passes (id, productId, name, isForSale, displayDescription, created, updated)."""
        body = self.client.get(f"{self.APIS}/game-passes/v1/universes/{universe_id}/game-passes",
                               {"limit": 100})
        return body.get("gamePasses") or []

    def places(self, universe_id: int, max_items: Optional[int] = None) -> PagedList:
        """Return every place inside a universe (id, universeId, name, description), 100 per page."""
        return self.client.fetch_all(f"{self.DEVELOP}/v1/universes/{universe_id}/places",
                                     limit=100, max_items=max_items)

    def place_details(self, place_ids: Iterable[int]) -> list:
        """Return place detail records (placeId, name, builder, builderId, universeId, isPlayable...) for ``place_ids``, 100 per call. Requires a cookie."""
        url = f"{self.BASE}/v1/games/multiget-place-details"
        out: List[dict] = []
        for chunk in chunked(place_ids, 100):
            body = self.client.get(url, {"placeIds": ",".join(str(i) for i in chunk)})
            out.extend(body or [])
        return out

    def user_created_places(self, user_id: int, max_items: Optional[int] = None) -> PagedList:
        """Return the places a user created (universeId, placeId, name, creator), 100 per page."""
        return self.client.fetch_all(f"{self.INVENTORY}/v1/users/{user_id}/places/inventory",
                                     {"placesTab": "Created"}, limit=100, max_items=max_items)
