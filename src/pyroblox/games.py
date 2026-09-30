"""Game (experience) data from ``games.roblox.com``, with a few helpers that
live on sibling hosts: place-to-universe lookup on ``apis.roblox.com``, game
passes on ``apis.roblox.com``, a universe's places on ``develop.roblox.com``,
and a user's created places on ``inventory.roblox.com``. Roblox has two ids
for every game: the *universe* id (what most endpoints here take) and the
*place* id you see in game URLs; :meth:`GamesAPI.get_universe_id` converts
between them. Everything is public except :meth:`GamesAPI.get_place_details`,
which needs a ``.ROBLOSECURITY`` cookie."""

from __future__ import annotations

from typing import Iterable, Optional

from .client import PagedList, RobloxClient, chunked
from .errors import NotFoundError
from .models.base import RobloxRecord
from .models.games import (
    CreatedPlace,
    Game,
    GameMedia,
    GamePass,
    GameServer,
    GameVotes,
    Place,
)


class GamesAPI:
    """Read-only access to the games endpoints.

    Every method returns typed models from :mod:`pyroblox.models.games` (or a
    :class:`~pyroblox.client.PagedList` of them) with the obvious envelope
    (``data``, ``gamePasses``, ``favoritesCount``...) already unwrapped.
    Fields Roblox adds that the models do not declare are kept as extras.
    """

    BASE = "https://games.roblox.com"
    APIS = "https://apis.roblox.com"
    DEVELOP = "https://develop.roblox.com"
    INVENTORY = "https://inventory.roblox.com"

    def __init__(self, client: RobloxClient):
        self.client = client

    def _multiget(self, path: str, universe_ids: Iterable[int]) -> list[dict]:
        """GET ``path?universeIds=a,b,c`` in chunks of 100 and concatenate raw ``data``."""
        url = f"{self.BASE}{path}"
        out: list[dict] = []
        for chunk in chunked(universe_ids, 100):
            body = self.client.get(url, {"universeIds": ",".join(str(i) for i in chunk)})
            out.extend(body.get("data") or [])
        return out

    # -- game objects ---------------------------------------------------------

    def get_info(self, universe_id: int) -> Game:
        """Return the :class:`Game` for a universe id (root_place_id, name, creator, playing, visits, favorited_count...); NotFoundError if Roblox returns nothing."""
        data = self._multiget("/v1/games", [universe_id])
        if not data:
            raise NotFoundError(f"universe {universe_id} not found", url=f"{self.BASE}/v1/games")
        return Game.model_validate(data[0])

    def get_batch(self, universe_ids: Iterable[int]) -> list[Game]:
        """Return the concatenated :class:`Game` objects for ``universe_ids``, 100 per call; unknown ids are silently omitted."""
        return Game.from_list(self._multiget("/v1/games", universe_ids))

    def get_universe_id(self, place_id: int) -> int:
        """Return the universe id (``int``) that owns ``place_id``; NotFoundError if Roblox answers null."""
        url = f"{self.APIS}/universes/v1/places/{place_id}/universe"
        body = self.client.get(url)
        universe_id = body.get("universeId") if isinstance(body, dict) else None
        if universe_id is None:
            raise NotFoundError(f"place {place_id} not found", url=url)
        return universe_id

    def get_info_by_place(self, place_id: int) -> Game:
        """Return the :class:`Game` for a place id (the id in game URLs) by resolving its universe first."""
        return self.get_info(self.get_universe_id(place_id))

    # -- listings -------------------------------------------------------------

    def get_user_games(self, user_id: int, max_items: Optional[int] = None) -> PagedList[Game]:
        """Return the :class:`Game` records a user has published (id, name, creator, root_place{id,type}, created, updated, place_visits); Roblox caps this page size at 50."""
        return self.client.fetch_all(f"{self.BASE}/v2/users/{user_id}/games",
                                     limit=50, max_items=max_items, sort_order="Asc",
                                     model=Game)

    def get_group_games(self, group_id: int, max_items: Optional[int] = None) -> PagedList[Game]:
        """Return the :class:`Game` records a group has published (same shape as :meth:`get_user_games`); Roblox allows about 3 calls per second unauthenticated."""
        return self.client.fetch_all(f"{self.BASE}/v2/groups/{group_id}/gamesV2",
                                     limit=100, max_items=max_items, sort_order="Asc",
                                     model=Game)

    def get_user_favorites(self, user_id: int, max_items: Optional[int] = None) -> PagedList[Game]:
        """Return the :class:`Game` records a user has favorited (same shape as :meth:`get_user_games`, plus price).

        Roblox rejects ``sortOrder=Asc`` on this endpoint ("Ascending sort order is
        not supported"), so no sort order is sent; results come newest first.
        """
        return self.client.fetch_all(f"{self.BASE}/v2/users/{user_id}/favorite/games",
                                     limit=100, max_items=max_items, model=Game)

    def get_servers(self, place_id: int, server_type: str = "Public",
                    max_items: Optional[int] = None) -> PagedList[GameServer]:
        """Return the running :class:`GameServer` records of a PLACE id (not a universe id): id, max_players, playing, player_tokens, players, fps, ping. Roblox allows about 3 calls per minute unauthenticated."""
        return self.client.fetch_all(f"{self.BASE}/v1/games/{place_id}/servers/{server_type}",
                                     limit=100, max_items=max_items, sort_order="Asc",
                                     model=GameServer)

    # -- votes / favorites / media --------------------------------------------

    def get_votes(self, universe_id: int) -> GameVotes:
        """Return the :class:`GameVotes` (id, up_votes, down_votes) for a universe; NotFoundError if Roblox returns nothing."""
        data = self._multiget("/v1/games/votes", [universe_id])
        if not data:
            raise NotFoundError(f"universe {universe_id} not found",
                                url=f"{self.BASE}/v1/games/votes")
        return GameVotes.model_validate(data[0])

    def get_votes_batch(self, universe_ids: Iterable[int]) -> list[GameVotes]:
        """Return the concatenated :class:`GameVotes` records (id, up_votes, down_votes) for ``universe_ids``, 100 per call."""
        return GameVotes.from_list(self._multiget("/v1/games/votes", universe_ids))

    def get_favorites_count(self, universe_id: int) -> int:
        """Return how many users have favorited the universe (``int``)."""
        body = self.client.get(f"{self.BASE}/v1/games/{universe_id}/favorites/count")
        return body["favoritesCount"]

    def get_media(self, universe_id: int) -> list[GameMedia]:
        """Return the universe's :class:`GameMedia` entries (asset_type_id, asset_type, image_id, video_hash, approved, alt_text)."""
        body = self.client.get(f"{self.BASE}/v2/games/{universe_id}/media")
        return GameMedia.from_list(body.get("data"))

    # -- other hosts ----------------------------------------------------------

    def get_game_passes(self, universe_id: int) -> list[GamePass]:
        """Return the universe's :class:`GamePass` records (id, product_id, name, is_for_sale, display_description, created, updated)."""
        body = self.client.get(f"{self.APIS}/game-passes/v1/universes/{universe_id}/game-passes",
                               {"limit": 100})
        return GamePass.from_list(body.get("gamePasses"))

    def get_places(self, universe_id: int, max_items: Optional[int] = None) -> PagedList[Place]:
        """Return every :class:`Place` inside a universe (id, universe_id, name, description), 100 per page."""
        return self.client.fetch_all(f"{self.DEVELOP}/v1/universes/{universe_id}/places",
                                     limit=100, max_items=max_items, model=Place)

    def get_place_details(self, place_ids: Iterable[int]) -> list[RobloxRecord]:
        """Return place detail :class:`RobloxRecord` entries (``placeId``, ``name``, ``builder``, ``builderId``, ``universeId``, ``isPlayable``... in Roblox's own spelling) for ``place_ids``, 100 per call. Requires a cookie."""
        url = f"{self.BASE}/v1/games/multiget-place-details"
        out: list[RobloxRecord] = []
        for chunk in chunked(place_ids, 100):
            body = self.client.get(url, {"placeIds": ",".join(str(i) for i in chunk)})
            out.extend(RobloxRecord.from_list(body))
        return out

    def get_user_created_places(self, user_id: int,
                                max_items: Optional[int] = None) -> PagedList[CreatedPlace]:
        """Return the :class:`CreatedPlace` records a user created (universe_id, place_id, name, creator), 100 per page."""
        return self.client.fetch_all(f"{self.INVENTORY}/v1/users/{user_id}/places/inventory",
                                     {"placesTab": "Created"}, limit=100, max_items=max_items,
                                     model=CreatedPlace)
