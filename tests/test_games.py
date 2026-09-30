"""Tests for GamesAPI (games.roblox.com plus apis/develop/inventory hosts).
No network: every test asserts the exact URL and params sent to a FakeSession
and the unwrapped return value. Fixture bodies are trimmed copies of real
responses recorded in the API probe."""

import pytest

from robloxwrapper.client import PagedList
from robloxwrapper.errors import AuthRequiredError, BadRequestError, NotFoundError
from robloxwrapper.games import GamesAPI
from tests.conftest import FakeResponse, make_client, page

G = "https://games.roblox.com"
APIS = "https://apis.roblox.com"
DEVELOP = "https://develop.roblox.com"
INVENTORY = "https://inventory.roblox.com"

GAME_13058 = {
    "id": 13058, "rootPlaceId": 1818, "name": "Crossroads",
    "description": "The classic Roblox level is back!",
    "sourceName": None, "sourceDescription": None,
    "creator": {"id": 1, "name": "Roblox", "type": "User", "isRNVAccount": False,
                "hasVerifiedBadge": True},
    "price": None, "allowedGearGenres": ["Ninja"], "allowedGearCategories": [],
    "isGenreEnforced": True, "copyingAllowed": False,
    "playing": 413, "visits": 39206917, "maxPlayers": 15,
    "created": "2007-05-01T01:07:04.78Z", "updated": "2026-09-24T22:40:42.987Z",
    "studioAccessToApisAllowed": False, "createVipServersAllowed": False,
    "universeAvatarType": "PlayerChoice", "genre": "Fighting", "genre_l1": "Action",
    "genre_l2": "Battlegrounds & Fighting", "untranslated_genre_l1": "action",
    "isAllGenre": False, "isFavoritedByUser": False, "favoritedCount": 316809,
    "canonicalUrlPath": "/games/1818/Crossroads", "isContentRestricted": False,
}

GAME_1818 = {
    "id": 1818, "rootPlaceId": 134084118, "name": "IAmAWee's Place Number: 2",
    "description": "IAmAWee's Place", "sourceName": None, "sourceDescription": None,
    "creator": {"id": 29591091, "name": "IAmAWee", "type": "User",
                "isRNVAccount": False, "hasVerifiedBadge": False},
    "price": None, "allowedGearGenres": ["All"], "allowedGearCategories": [],
    "isGenreEnforced": True, "copyingAllowed": False,
    "playing": 0, "visits": 0, "maxPlayers": 6,
    "created": "2013-10-31T19:07:07.337Z", "updated": "2013-10-31T19:07:07.337Z",
    "genre": "All", "favoritedCount": 14, "isContentRestricted": False,
}

USER_GAMES = [
    {"id": 2434560046, "name": "Crossroads but with a million people",
     "description": "[ Content Deleted ]", "creator": {"id": 261, "type": "User"},
     "rootPlace": {"id": 6504969480, "type": "Place"},
     "created": "2021-03-11T18:19:47.947Z", "updated": "2025-08-10T04:02:03.477Z",
     "placeVisits": 24754},
    {"id": 154946585, "name": "Coming Soon", "description": "",
     "creator": {"id": 261, "type": "User"},
     "rootPlace": {"id": 410071311, "type": "Place"},
     "created": "2016-05-06T20:20:20.72Z", "updated": "2019-04-05T15:38:02.097Z",
     "placeVisits": 24},
]

FAVORITES = [
    {"price": None, "id": 7382898139, "name": "High Tides",
     "description": "A pirate-themed melee priority combat game.",
     "creator": {"id": 17097342, "type": "Group", "name": "Synesthetics"},
     "rootPlace": {"id": 95955564282682, "type": "Place"},
     "created": "2025-03-15T16:02:28.157Z", "updated": "2026-09-08T14:34:08.437Z",
     "placeVisits": 10490418},
]

SERVERS = [
    {"id": "c29d1d82-c923-4515-9e53-b3a1074d8326", "maxPlayers": 12, "playing": 1,
     "playerTokens": [], "players": [], "fps": 59.984482, "ping": 82},
    {"id": "a8c80984-7b25-4b9a-8383-e3564e46ab68", "maxPlayers": 12, "playing": 1,
     "playerTokens": [], "players": [], "fps": 59.989277, "ping": 89},
]

VOTES = [
    {"id": 1818, "upVotes": 0, "downVotes": 0},
    {"id": 994732206, "upVotes": 12720514, "downVotes": 1063632},
]

MEDIA = [
    {"assetTypeId": 1, "assetType": "Image", "imageId": 126410127976844,
     "videoHash": None, "videoTitle": None, "approved": True, "altText": ""},
    {"assetTypeId": 1, "assetType": "Image", "imageId": 140165890160958,
     "videoHash": None, "videoTitle": None, "approved": True, "altText": ""},
]

GAME_PASSES = [
    {"id": 7578721, "productId": 933434480, "name": "2x Boss Drops", "isForSale": True,
     "displayName": "2x Boss Drops",
     "displayDescription": "Bosses will drop special items twice as often!",
     "displayIconImageAssetId": 84816064670684,
     "created": "2019-11-18T21:42:55.513Z", "updated": "2026-08-05T00:29:32.278Z"},
    {"id": 6738811, "productId": 601949534, "name": "Fruit Notifier", "isForSale": True,
     "displayName": "Fruit Notifier",
     "displayDescription": "Alerts you when a fruit spawns in your server.",
     "displayIconImageAssetId": 73453348177520,
     "created": "2019-07-07T03:16:51.543Z", "updated": "2026-08-05T00:21:28.387Z"},
]

PLACES = [
    {"id": 2753915549, "universeId": 994732206, "name": "Blox Fruits",
     "description": "Welcome to Blox Fruits!"},
    {"id": 4442272183, "universeId": 994732206, "name": "Blox Fruits | Second Sea",
     "description": ""},
    {"id": 7449423635, "universeId": 994732206, "name": "Blox Fruits | Third Sea",
     "description": ""},
]

PLACE_DETAILS = [
    {"placeId": 2753915549, "name": "Blox Fruits", "description": "Welcome to Blox Fruits!",
     "sourceName": "Blox Fruits", "sourceDescription": "Welcome to Blox Fruits!",
     "url": "https://www.roblox.com/games/2753915549/Blox-Fruits",
     "builder": "Gamer Robot Inc", "builderId": 4372130, "hasVerifiedBadge": True,
     "isPlayable": True, "reasonProhibited": "None", "universeId": 994732206,
     "universeRootPlaceId": 2753915549, "price": 0, "imageToken": "T_2753915549_5a1b"},
]

CREATED_PLACES = [
    {"universeId": 2434560046, "placeId": 6504969480,
     "name": "Crossroads but with a million people",
     "creator": {"id": 261, "name": "Shedletsky", "type": "User"}, "priceInRobux": None},
    {"universeId": 154946585, "placeId": 410071311, "name": "Coming Soon",
     "creator": {"id": 261, "name": "Shedletsky", "type": "User"}, "priceInRobux": None},
]

UNAUTH_401 = FakeResponse(401, {"errors": [{
    "code": 9002, "subcode": 0, "message": "Authentication token is missing"}]})


# -- wiring -------------------------------------------------------------------

def test_client_games_attribute_is_games_api():
    client, _, _ = make_client(routes={})
    assert isinstance(client.games, GamesAPI)
    assert client.games is client.games
    assert client.games.client is client


# -- get / batch_get ----------------------------------------------------------

def test_get_sends_universe_id_and_unwraps_first_item():
    client, session, _ = make_client(routes={f"GET {G}/v1/games": {"data": [GAME_13058]}})
    assert client.games.get(13058) == GAME_13058
    call = session.calls[0]
    assert call.method == "GET" and call.url == f"{G}/v1/games"
    assert call.params == {"universeIds": "13058"}


def test_get_empty_data_raises_not_found():
    client, _, _ = make_client(routes={f"GET {G}/v1/games": {"data": []}})
    with pytest.raises(NotFoundError) as exc:
        client.games.get(999999999)
    assert "999999999" in str(exc.value)
    assert exc.value.url == f"{G}/v1/games"


def test_batch_get_joins_ids_and_unwraps_data():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/games": {"data": [GAME_1818, GAME_13058]}})
    assert client.games.batch_get([1818, 13058]) == [GAME_1818, GAME_13058]
    assert session.calls[0].url == f"{G}/v1/games"
    assert session.calls[0].params == {"universeIds": "1818,13058"}


def test_batch_get_chunks_150_ids_into_two_calls():
    client, session, _ = make_client(
        [FakeResponse(200, {"data": [{"id": 1}]}), FakeResponse(200, {"data": [{"id": 101}]})])
    out = client.games.batch_get(range(1, 151))
    assert out == [{"id": 1}, {"id": 101}]
    assert isinstance(out, list)
    assert len(session.calls) == 2
    assert session.calls[0].params["universeIds"] == ",".join(str(i) for i in range(1, 101))
    assert session.calls[1].params["universeIds"] == ",".join(str(i) for i in range(101, 151))


def test_batch_get_no_ids_makes_no_calls():
    client, session, _ = make_client(routes={})
    assert client.games.batch_get([]) == []
    assert session.calls == []


# -- place -> universe --------------------------------------------------------

def test_place_to_universe_returns_universe_id():
    client, session, _ = make_client(
        routes={f"GET {APIS}/universes/v1/places/2753915549/universe": {"universeId": 994732206}})
    assert client.games.place_to_universe(2753915549) == 994732206
    call = session.calls[0]
    assert call.method == "GET"
    assert call.url == f"{APIS}/universes/v1/places/2753915549/universe"
    assert not call.params


def test_place_to_universe_null_raises_not_found():
    url = f"{APIS}/universes/v1/places/1/universe"
    client, _, _ = make_client(routes={f"GET {url}": {"universeId": None}})
    with pytest.raises(NotFoundError) as exc:
        client.games.place_to_universe(1)
    assert "1" in str(exc.value) and exc.value.url == url


def test_place_to_universe_missing_key_raises_not_found():
    client, _, _ = make_client(routes={f"GET {APIS}/universes/v1/places/1/universe": {}})
    with pytest.raises(NotFoundError):
        client.games.place_to_universe(1)


def test_get_by_place_composes_lookup_then_get():
    client, session, _ = make_client(routes={
        f"GET {APIS}/universes/v1/places/1818/universe": {"universeId": 13058},
        f"GET {G}/v1/games": {"data": [GAME_13058]},
    })
    assert client.games.get_by_place(1818) == GAME_13058
    assert session.urls == [f"{APIS}/universes/v1/places/1818/universe", f"{G}/v1/games"]
    assert session.calls[1].params == {"universeIds": "13058"}


# -- listings -----------------------------------------------------------------

def test_user_games_paginates_with_limit_50_asc():
    client, session, _ = make_client(
        routes={f"GET {G}/v2/users/261/games": [
            page(USER_GAMES[:1], "50_1_277d87efc82ea67f572b0c853f1b3951"),
            page(USER_GAMES[1:], None)]})
    out = client.games.user_games(261)
    assert isinstance(out, PagedList) and out.truncated is False
    assert out == USER_GAMES
    assert session.calls[0].url == f"{G}/v2/users/261/games"
    assert session.calls[0].params == {"limit": 50, "sortOrder": "Asc"}
    assert session.calls[1].params == {"limit": 50, "sortOrder": "Asc",
                                       "cursor": "50_1_277d87efc82ea67f572b0c853f1b3951"}


def test_user_games_max_items_truncates():
    client, session, _ = make_client(
        routes={f"GET {G}/v2/users/261/games": page(USER_GAMES, "c1")})
    out = client.games.user_games(261, max_items=1)
    assert out == USER_GAMES[:1] and out.truncated is True
    assert len(session.calls) == 1


def test_group_games_uses_games_v2_with_limit_100_asc():
    client, session, _ = make_client(
        routes={f"GET {G}/v2/groups/33548380/gamesV2": page(USER_GAMES, None)})
    out = client.games.group_games(33548380)
    assert isinstance(out, PagedList) and out == USER_GAMES
    assert session.calls[0].url == f"{G}/v2/groups/33548380/gamesV2"
    assert session.calls[0].params == {"limit": 100, "sortOrder": "Asc"}


def test_group_games_empty():
    client, _, _ = make_client(routes={f"GET {G}/v2/groups/7/gamesV2": page([], None)})
    assert client.games.group_games(7) == []


def test_user_favorites_paginates_with_limit_100_and_no_sort_order():
    # Roblox answers 400 "Ascending sort order is not supported" if sortOrder=Asc is sent
    client, session, _ = make_client(
        routes={f"GET {G}/v2/users/261/favorite/games": page(FAVORITES, None)})
    out = client.games.user_favorites(261)
    assert isinstance(out, PagedList) and out == FAVORITES
    assert session.calls[0].url == f"{G}/v2/users/261/favorite/games"
    assert session.calls[0].params == {"limit": 100}


def test_servers_takes_place_id_and_defaults_to_public():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/games/2753915549/servers/Public": page(SERVERS, None)})
    out = client.games.servers(2753915549)
    assert isinstance(out, PagedList) and out == SERVERS
    assert session.calls[0].url == f"{G}/v1/games/2753915549/servers/Public"
    assert session.calls[0].params == {"limit": 100, "sortOrder": "Asc"}


def test_servers_server_type_in_path_and_max_items():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/games/2753915549/servers/Friends": page(SERVERS, "c1")})
    out = client.games.servers(2753915549, server_type="Friends", max_items=1)
    assert out == SERVERS[:1] and out.truncated is True
    assert session.calls[0].url == f"{G}/v1/games/2753915549/servers/Friends"
    assert len(session.calls) == 1


def test_servers_with_universe_id_propagates_bad_request():
    client, _, _ = make_client(routes={f"GET {G}/v1/games/994732206/servers/Public":
                                       FakeResponse(400, {"errors": [{"code": 1, "message": "The place is invalid."}]})})
    with pytest.raises(BadRequestError) as exc:
        client.games.servers(994732206)
    assert exc.value.roblox_message == "The place is invalid."


# -- votes / favorites / media ------------------------------------------------

def test_votes_unwraps_first_item():
    client, session, _ = make_client(routes={f"GET {G}/v1/games/votes": {"data": VOTES[1:]}})
    assert client.games.votes(994732206) == VOTES[1]
    assert session.calls[0].url == f"{G}/v1/games/votes"
    assert session.calls[0].params == {"universeIds": "994732206"}


def test_votes_empty_data_raises_not_found():
    client, _, _ = make_client(routes={f"GET {G}/v1/games/votes": {"data": []}})
    with pytest.raises(NotFoundError) as exc:
        client.games.votes(42)
    assert "42" in str(exc.value) and exc.value.url == f"{G}/v1/games/votes"


def test_batch_votes_joins_ids_and_unwraps_data():
    client, session, _ = make_client(routes={f"GET {G}/v1/games/votes": {"data": VOTES}})
    assert client.games.batch_votes([1818, 994732206]) == VOTES
    assert session.calls[0].params == {"universeIds": "1818,994732206"}


def test_batch_votes_chunks_150_ids_into_two_calls():
    client, session, _ = make_client(
        [FakeResponse(200, {"data": [{"id": 1, "upVotes": 1, "downVotes": 0}]}),
         FakeResponse(200, {"data": [{"id": 101, "upVotes": 0, "downVotes": 1}]})])
    out = client.games.batch_votes(range(1, 151))
    assert [v["id"] for v in out] == [1, 101]
    assert len(session.calls) == 2
    assert session.calls[0].url == f"{G}/v1/games/votes"
    assert session.calls[0].params["universeIds"] == ",".join(str(i) for i in range(1, 101))
    assert session.calls[1].params["universeIds"] == ",".join(str(i) for i in range(101, 151))


def test_favorites_count_unwraps_int():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/games/994732206/favorites/count": {"favoritesCount": 19996862}})
    assert client.games.favorites_count(994732206) == 19996862
    assert session.calls[0].url == f"{G}/v1/games/994732206/favorites/count"
    assert not session.calls[0].params


def test_media_unwraps_data():
    client, session, _ = make_client(
        routes={f"GET {G}/v2/games/994732206/media": {"data": MEDIA}})
    assert client.games.media(994732206) == MEDIA
    assert session.calls[0].url == f"{G}/v2/games/994732206/media"
    assert not session.calls[0].params


# -- apis / develop / inventory hosts -----------------------------------------

def test_game_passes_uses_apis_host_and_unwraps_game_passes():
    url = f"{APIS}/game-passes/v1/universes/994732206/game-passes"
    client, session, _ = make_client(routes={f"GET {url}": {"gamePasses": GAME_PASSES}})
    assert client.games.game_passes(994732206) == GAME_PASSES
    assert session.calls[0].url == url
    assert session.calls[0].params == {"limit": 100}


def test_places_uses_develop_host_with_limit_100():
    client, session, _ = make_client(
        routes={f"GET {DEVELOP}/v1/universes/994732206/places": [
            page(PLACES[:2], "c1"), page(PLACES[2:], None)]})
    out = client.games.places(994732206)
    assert isinstance(out, PagedList) and out == PLACES
    assert session.calls[0].url == f"{DEVELOP}/v1/universes/994732206/places"
    assert session.calls[0].params == {"limit": 100}
    assert session.calls[1].params == {"limit": 100, "cursor": "c1"}


def test_place_details_returns_bare_array_and_sends_cookie():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/games/multiget-place-details": FakeResponse(200, PLACE_DETAILS)},
        cookie="SECRET")
    out = client.games.place_details([2753915549])
    assert out == PLACE_DETAILS and isinstance(out, list)
    call = session.calls[0]
    assert call.url == f"{G}/v1/games/multiget-place-details"
    assert call.params == {"placeIds": "2753915549"}
    assert call.cookies == {".ROBLOSECURITY": "SECRET"}


def test_place_details_chunks_150_ids_into_two_calls():
    client, session, _ = make_client(
        [FakeResponse(200, [{"placeId": 1}]), FakeResponse(200, [{"placeId": 101}])],
        cookie="SECRET")
    out = client.games.place_details(range(1, 151))
    assert out == [{"placeId": 1}, {"placeId": 101}]
    assert len(session.calls) == 2
    assert session.calls[0].params["placeIds"] == ",".join(str(i) for i in range(1, 101))
    assert session.calls[1].params["placeIds"] == ",".join(str(i) for i in range(101, 151))


def test_place_details_without_cookie_raises_auth_required():
    client, _, _ = make_client(routes={f"GET {G}/v1/games/multiget-place-details": UNAUTH_401})
    with pytest.raises(AuthRequiredError):
        client.games.place_details([2753915549])


def test_user_created_places_uses_inventory_host_with_places_tab():
    client, session, _ = make_client(
        routes={f"GET {INVENTORY}/v1/users/261/places/inventory": [
            page(CREATED_PLACES[:1], "2"), page(CREATED_PLACES[1:], None)]})
    out = client.games.user_created_places(261)
    assert isinstance(out, PagedList) and out == CREATED_PLACES
    assert session.calls[0].url == f"{INVENTORY}/v1/users/261/places/inventory"
    assert session.calls[0].params == {"placesTab": "Created", "limit": 100}
    assert session.calls[1].params == {"placesTab": "Created", "limit": 100, "cursor": "2"}
