"""Tests for GamesAPI (games.roblox.com plus apis/develop/inventory hosts).
No network: every test asserts the exact URL and params sent to a FakeSession
and the typed return value. Fixture bodies are trimmed copies of real
responses recorded in the API probe."""

import pytest
from pydantic import ValidationError

from pyroblox.client import PagedList
from pyroblox.errors import AuthRequiredError, BadRequestError, NotFoundError
from pyroblox.games import GamesAPI
from pyroblox.models.base import RobloxRecord
from pyroblox.models.games import (
    CreatedPlace,
    Game,
    GameCreator,
    GameMedia,
    GamePass,
    GameServer,
    GameVotes,
    Place,
    RootPlace,
)
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


def _ids(models):
    return [m.id for m in models]


# -- wiring -------------------------------------------------------------------

def test_client_games_attribute_is_games_api():
    client, _, _ = make_client(routes={})
    assert isinstance(client.games, GamesAPI)
    assert client.games is client.games
    assert client.games.client is client


# -- get_info / get_batch -----------------------------------------------------

def test_get_info_sends_universe_id_and_returns_game():
    client, session, _ = make_client(routes={f"GET {G}/v1/games": {"data": [GAME_13058]}})
    out = client.games.get_info(13058)
    assert isinstance(out, Game)
    assert out.id == 13058 and out.root_place_id == 1818 and out.name == "Crossroads"
    assert out.root_place is None  # v1 shape has rootPlaceId, not rootPlace
    assert isinstance(out.creator, GameCreator)
    assert out.creator.id == 1 and out.creator.name == "Roblox" and out.creator.type == "User"
    assert out.creator.is_rnv_account is False and out.creator.has_verified_badge is True
    assert out.playing == 413 and out.visits == 39206917 and out.max_players == 15
    assert out.genre == "Fighting" and out.genre_l1 == "Action"
    assert out.genre_l2 == "Battlegrounds & Fighting"
    assert out.favorited_count == 316809 and out.is_content_restricted is False
    assert out.price is None and out.source_name is None
    assert out.created.year == 2007 and out.updated.year == 2026
    assert out.universeAvatarType == "PlayerChoice"  # undeclared field survives
    call = session.calls[0]
    assert call.method == "GET" and call.url == f"{G}/v1/games"
    assert call.params == {"universeIds": "13058"}


def test_get_info_empty_data_raises_not_found():
    client, _, _ = make_client(routes={f"GET {G}/v1/games": {"data": []}})
    with pytest.raises(NotFoundError) as exc:
        client.games.get_info(999999999)
    assert "999999999" in str(exc.value)
    assert exc.value.url == f"{G}/v1/games"


def test_get_batch_joins_ids_and_unwraps_data():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/games": {"data": [GAME_1818, GAME_13058]}})
    out = client.games.get_batch([1818, 13058])
    assert isinstance(out, list) and all(isinstance(g, Game) for g in out)
    assert _ids(out) == [1818, 13058]
    assert out[0].creator.name == "IAmAWee" and out[0].favorited_count == 14
    assert session.calls[0].url == f"{G}/v1/games"
    assert session.calls[0].params == {"universeIds": "1818,13058"}


def test_get_batch_chunks_150_ids_into_two_calls():
    client, session, _ = make_client(
        [FakeResponse(200, {"data": [{"id": 1, "name": "g1"}]}),
         FakeResponse(200, {"data": [{"id": 101, "name": "g101"}]})])
    out = client.games.get_batch(range(1, 151))
    assert _ids(out) == [1, 101]
    assert isinstance(out, list)
    assert len(session.calls) == 2
    assert session.calls[0].params["universeIds"] == ",".join(str(i) for i in range(1, 101))
    assert session.calls[1].params["universeIds"] == ",".join(str(i) for i in range(101, 151))


def test_get_batch_no_ids_makes_no_calls():
    client, session, _ = make_client(routes={})
    assert client.games.get_batch([]) == []
    assert session.calls == []


# -- place -> universe --------------------------------------------------------

def test_get_universe_id_returns_int():
    client, session, _ = make_client(
        routes={f"GET {APIS}/universes/v1/places/2753915549/universe": {"universeId": 994732206}})
    out = client.games.get_universe_id(2753915549)
    assert out == 994732206 and isinstance(out, int)
    call = session.calls[0]
    assert call.method == "GET"
    assert call.url == f"{APIS}/universes/v1/places/2753915549/universe"
    assert not call.params


def test_get_universe_id_null_raises_not_found():
    url = f"{APIS}/universes/v1/places/1/universe"
    client, _, _ = make_client(routes={f"GET {url}": {"universeId": None}})
    with pytest.raises(NotFoundError) as exc:
        client.games.get_universe_id(1)
    assert "1" in str(exc.value) and exc.value.url == url


def test_get_universe_id_missing_key_raises_not_found():
    client, _, _ = make_client(routes={f"GET {APIS}/universes/v1/places/1/universe": {}})
    with pytest.raises(NotFoundError):
        client.games.get_universe_id(1)


def test_get_info_by_place_composes_lookup_then_get():
    client, session, _ = make_client(routes={
        f"GET {APIS}/universes/v1/places/1818/universe": {"universeId": 13058},
        f"GET {G}/v1/games": {"data": [GAME_13058]},
    })
    out = client.games.get_info_by_place(1818)
    assert isinstance(out, Game) and out.id == 13058 and out.root_place_id == 1818
    assert session.urls == [f"{APIS}/universes/v1/places/1818/universe", f"{G}/v1/games"]
    assert session.calls[1].params == {"universeIds": "13058"}


# -- listings -----------------------------------------------------------------

def test_get_user_games_paginates_with_limit_50_asc():
    client, session, _ = make_client(
        routes={f"GET {G}/v2/users/261/games": [
            page(USER_GAMES[:1], "50_1_277d87efc82ea67f572b0c853f1b3951"),
            page(USER_GAMES[1:], None)]})
    out = client.games.get_user_games(261)
    assert isinstance(out, PagedList) and out.truncated is False
    assert all(isinstance(g, Game) for g in out)
    assert _ids(out) == [2434560046, 154946585]
    assert out[0].name == "Crossroads but with a million people"
    assert out[0].creator.id == 261 and out[0].creator.type == "User"
    assert out[0].creator.name is None  # v2 listings omit the creator name
    assert isinstance(out[0].root_place, RootPlace)
    assert out[0].root_place.id == 6504969480 and out[0].root_place.type == "Place"
    assert out[0].root_place_id is None  # v2 shape has rootPlace, not rootPlaceId
    assert out[0].place_visits == 24754 and out[1].place_visits == 24
    assert out[0].created.year == 2021
    assert session.calls[0].url == f"{G}/v2/users/261/games"
    assert session.calls[0].params == {"limit": 50, "sortOrder": "Asc"}
    assert session.calls[1].params == {"limit": 50, "sortOrder": "Asc",
                                       "cursor": "50_1_277d87efc82ea67f572b0c853f1b3951"}


def test_get_user_games_max_items_truncates():
    client, session, _ = make_client(
        routes={f"GET {G}/v2/users/261/games": page(USER_GAMES, "c1")})
    out = client.games.get_user_games(261, max_items=1)
    assert _ids(out) == [2434560046] and out.truncated is True
    assert len(session.calls) == 1


def test_get_group_games_uses_games_v2_with_limit_100_asc():
    client, session, _ = make_client(
        routes={f"GET {G}/v2/groups/33548380/gamesV2": page(USER_GAMES, None)})
    out = client.games.get_group_games(33548380)
    assert isinstance(out, PagedList) and _ids(out) == [2434560046, 154946585]
    assert isinstance(out[0], Game) and out[0].root_place.id == 6504969480
    assert session.calls[0].url == f"{G}/v2/groups/33548380/gamesV2"
    assert session.calls[0].params == {"limit": 100, "sortOrder": "Asc"}


def test_get_group_games_empty():
    client, _, _ = make_client(routes={f"GET {G}/v2/groups/7/gamesV2": page([], None)})
    assert client.games.get_group_games(7) == []


def test_get_user_favorites_paginates_with_limit_100_and_no_sort_order():
    # Roblox answers 400 "Ascending sort order is not supported" if sortOrder=Asc is sent
    client, session, _ = make_client(
        routes={f"GET {G}/v2/users/261/favorite/games": page(FAVORITES, None)})
    out = client.games.get_user_favorites(261)
    assert isinstance(out, PagedList) and _ids(out) == [7382898139]
    assert isinstance(out[0], Game) and out[0].name == "High Tides"
    assert out[0].price is None and out[0].place_visits == 10490418
    assert out[0].creator.type == "Group" and out[0].creator.name == "Synesthetics"
    assert session.calls[0].url == f"{G}/v2/users/261/favorite/games"
    assert session.calls[0].params == {"limit": 100}


def test_get_servers_takes_place_id_and_defaults_to_public():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/games/2753915549/servers/Public": page(SERVERS, None)})
    out = client.games.get_servers(2753915549)
    assert isinstance(out, PagedList) and len(out) == 2
    assert all(isinstance(s, GameServer) for s in out)
    assert out[0].id == "c29d1d82-c923-4515-9e53-b3a1074d8326"
    assert out[0].max_players == 12 and out[0].playing == 1
    assert out[0].player_tokens == [] and out[0].players == []
    assert out[0].fps == 59.984482 and out[0].ping == 82
    assert out[1].ping == 89
    assert session.calls[0].url == f"{G}/v1/games/2753915549/servers/Public"
    assert session.calls[0].params == {"limit": 100, "sortOrder": "Asc"}


def test_get_servers_server_type_in_path_and_max_items():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/games/2753915549/servers/Friends": page(SERVERS, "c1")})
    out = client.games.get_servers(2753915549, server_type="Friends", max_items=1)
    assert _ids(out) == [SERVERS[0]["id"]] and out.truncated is True
    assert session.calls[0].url == f"{G}/v1/games/2753915549/servers/Friends"
    assert len(session.calls) == 1


def test_get_servers_with_universe_id_propagates_bad_request():
    client, _, _ = make_client(routes={f"GET {G}/v1/games/994732206/servers/Public":
                                       FakeResponse(400, {"errors": [{"code": 1, "message": "The place is invalid."}]})})
    with pytest.raises(BadRequestError) as exc:
        client.games.get_servers(994732206)
    assert exc.value.roblox_message == "The place is invalid."


# -- votes / favorites / media ------------------------------------------------

def test_get_votes_returns_game_votes():
    client, session, _ = make_client(routes={f"GET {G}/v1/games/votes": {"data": VOTES[1:]}})
    out = client.games.get_votes(994732206)
    assert isinstance(out, GameVotes)
    assert out.id == 994732206 and out.up_votes == 12720514 and out.down_votes == 1063632
    assert session.calls[0].url == f"{G}/v1/games/votes"
    assert session.calls[0].params == {"universeIds": "994732206"}


def test_get_votes_empty_data_raises_not_found():
    client, _, _ = make_client(routes={f"GET {G}/v1/games/votes": {"data": []}})
    with pytest.raises(NotFoundError) as exc:
        client.games.get_votes(42)
    assert "42" in str(exc.value) and exc.value.url == f"{G}/v1/games/votes"


def test_get_votes_batch_joins_ids_and_unwraps_data():
    client, session, _ = make_client(routes={f"GET {G}/v1/games/votes": {"data": VOTES}})
    out = client.games.get_votes_batch([1818, 994732206])
    assert isinstance(out, list) and all(isinstance(v, GameVotes) for v in out)
    assert _ids(out) == [1818, 994732206]
    assert out[0].up_votes == 0 and out[1].down_votes == 1063632
    assert session.calls[0].params == {"universeIds": "1818,994732206"}


def test_get_votes_batch_chunks_150_ids_into_two_calls():
    client, session, _ = make_client(
        [FakeResponse(200, {"data": [{"id": 1, "upVotes": 1, "downVotes": 0}]}),
         FakeResponse(200, {"data": [{"id": 101, "upVotes": 0, "downVotes": 1}]})])
    out = client.games.get_votes_batch(range(1, 151))
    assert _ids(out) == [1, 101]
    assert out[0].up_votes == 1 and out[1].down_votes == 1
    assert len(session.calls) == 2
    assert session.calls[0].url == f"{G}/v1/games/votes"
    assert session.calls[0].params["universeIds"] == ",".join(str(i) for i in range(1, 101))
    assert session.calls[1].params["universeIds"] == ",".join(str(i) for i in range(101, 151))


def test_get_favorites_count_unwraps_int():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/games/994732206/favorites/count": {"favoritesCount": 19996862}})
    assert client.games.get_favorites_count(994732206) == 19996862
    assert session.calls[0].url == f"{G}/v1/games/994732206/favorites/count"
    assert not session.calls[0].params


def test_get_media_unwraps_data():
    client, session, _ = make_client(
        routes={f"GET {G}/v2/games/994732206/media": {"data": MEDIA}})
    out = client.games.get_media(994732206)
    assert isinstance(out, list) and all(isinstance(m, GameMedia) for m in out)
    assert [m.image_id for m in out] == [126410127976844, 140165890160958]
    assert out[0].asset_type_id == 1 and out[0].asset_type == "Image"
    assert out[0].video_hash is None and out[0].video_title is None
    assert out[0].approved is True and out[0].alt_text == ""
    assert session.calls[0].url == f"{G}/v2/games/994732206/media"
    assert not session.calls[0].params


# -- apis / develop / inventory hosts -----------------------------------------

def test_get_game_passes_uses_apis_host_and_unwraps_game_passes():
    url = f"{APIS}/game-passes/v1/universes/994732206/game-passes"
    client, session, _ = make_client(routes={f"GET {url}": {"gamePasses": GAME_PASSES}})
    out = client.games.get_game_passes(994732206)
    assert isinstance(out, list) and all(isinstance(p, GamePass) for p in out)
    assert _ids(out) == [7578721, 6738811]
    assert out[0].product_id == 933434480 and out[0].name == "2x Boss Drops"
    assert out[0].display_name == "2x Boss Drops"
    assert out[0].display_description.startswith("Bosses will drop")
    assert out[0].is_for_sale is True
    assert out[0].display_icon_image_asset_id == 84816064670684
    assert out[0].created.year == 2019 and out[0].updated.year == 2026
    assert session.calls[0].url == url
    assert session.calls[0].params == {"limit": 100}


def test_get_places_uses_develop_host_with_limit_100():
    client, session, _ = make_client(
        routes={f"GET {DEVELOP}/v1/universes/994732206/places": [
            page(PLACES[:2], "c1"), page(PLACES[2:], None)]})
    out = client.games.get_places(994732206)
    assert isinstance(out, PagedList) and _ids(out) == [2753915549, 4442272183, 7449423635]
    assert all(isinstance(p, Place) for p in out)
    assert out[0].universe_id == 994732206 and out[0].name == "Blox Fruits"
    assert out[0].description == "Welcome to Blox Fruits!" and out[1].description == ""
    assert session.calls[0].url == f"{DEVELOP}/v1/universes/994732206/places"
    assert session.calls[0].params == {"limit": 100}
    assert session.calls[1].params == {"limit": 100, "cursor": "c1"}


def test_get_place_details_returns_records_and_sends_cookie():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/games/multiget-place-details": FakeResponse(200, PLACE_DETAILS)},
        cookie="SECRET")
    out = client.games.get_place_details([2753915549])
    assert isinstance(out, list) and isinstance(out[0], RobloxRecord)
    assert out[0].placeId == 2753915549 and out[0].builderId == 4372130
    assert out[0].universeId == 994732206 and out[0].isPlayable is True
    assert out[0].to_record() == PLACE_DETAILS[0]
    call = session.calls[0]
    assert call.url == f"{G}/v1/games/multiget-place-details"
    assert call.params == {"placeIds": "2753915549"}
    assert call.cookies == {".ROBLOSECURITY": "SECRET"}


def test_get_place_details_chunks_150_ids_into_two_calls():
    client, session, _ = make_client(
        [FakeResponse(200, [{"placeId": 1}]), FakeResponse(200, [{"placeId": 101}])],
        cookie="SECRET")
    out = client.games.get_place_details(range(1, 151))
    assert [r.placeId for r in out] == [1, 101]
    assert len(session.calls) == 2
    assert session.calls[0].params["placeIds"] == ",".join(str(i) for i in range(1, 101))
    assert session.calls[1].params["placeIds"] == ",".join(str(i) for i in range(101, 151))


def test_get_place_details_without_cookie_raises_auth_required():
    client, _, _ = make_client(routes={f"GET {G}/v1/games/multiget-place-details": UNAUTH_401})
    with pytest.raises(AuthRequiredError):
        client.games.get_place_details([2753915549])


def test_get_user_created_places_uses_inventory_host_with_places_tab():
    client, session, _ = make_client(
        routes={f"GET {INVENTORY}/v1/users/261/places/inventory": [
            page(CREATED_PLACES[:1], "2"), page(CREATED_PLACES[1:], None)]})
    out = client.games.get_user_created_places(261)
    assert isinstance(out, PagedList) and len(out) == 2
    assert all(isinstance(p, CreatedPlace) for p in out)
    assert [p.place_id for p in out] == [6504969480, 410071311]
    assert [p.universe_id for p in out] == [2434560046, 154946585]
    assert out[0].name == "Crossroads but with a million people"
    assert isinstance(out[0].creator, GameCreator)
    assert out[0].creator.id == 261 and out[0].creator.name == "Shedletsky"
    assert out[0].price_in_robux is None
    assert session.calls[0].url == f"{INVENTORY}/v1/users/261/places/inventory"
    assert session.calls[0].params == {"placesTab": "Created", "limit": 100}
    assert session.calls[1].params == {"placesTab": "Created", "limit": 100, "cursor": "2"}


# -- models -------------------------------------------------------------------

def test_game_creator_model_roundtrip_keeps_rnv_spelling():
    raw = dict(GAME_13058["creator"], isPremium=True)
    m = GameCreator.model_validate(raw)
    assert m.id == 1 and m.name == "Roblox" and m.type == "User"
    assert m.is_rnv_account is False and m.has_verified_badge is True
    assert m.model_extra == {"isPremium": True}
    rec = m.to_record()
    assert rec == raw and "isRNVAccount" in rec and "isRnvAccount" not in rec


def test_root_place_model_roundtrip():
    raw = {"id": 6504969480, "type": "Place", "isRoot": True}
    m = RootPlace.model_validate(raw)
    assert m.id == 6504969480 and m.type == "Place"
    assert m.model_extra == {"isRoot": True}
    assert m.to_record() == raw


def test_game_model_roundtrip_v1_shape():
    m = Game.model_validate(GAME_13058)
    assert m.id == 13058 and m.root_place_id == 1818 and m.max_players == 15
    assert m.genre_l1 == "Action" and m.genre_l2 == "Battlegrounds & Fighting"
    assert m.creator.is_rnv_account is False
    extras = m.model_extra
    assert extras["universeAvatarType"] == "PlayerChoice"
    assert extras["allowedGearGenres"] == ["Ninja"] and extras["isAllGenre"] is False
    rec = m.to_record()
    assert rec["rootPlaceId"] == 1818 and rec["maxPlayers"] == 15
    assert rec["favoritedCount"] == 316809 and rec["isContentRestricted"] is False
    assert rec["genre_l1"] == "Action" and "genreL1" not in rec  # Roblox's own spelling
    assert rec["creator"]["isRNVAccount"] is False
    assert rec["created"].startswith("2007-05-01T01:07:04.78")
    assert rec["universeAvatarType"] == "PlayerChoice"
    assert "rootPlace" not in rec  # declared-but-unsent fields are not emitted


def test_game_model_roundtrip_v2_listing_shape():
    raw = dict(USER_GAMES[0], isArchived=False)
    m = Game.model_validate(raw)
    assert m.root_place.id == 6504969480 and m.root_place_id is None
    assert m.place_visits == 24754 and m.creator.name is None
    assert m.model_extra == {"isArchived": False}
    rec = m.to_record()
    assert rec["rootPlace"] == {"id": 6504969480, "type": "Place"}
    assert rec["placeVisits"] == 24754 and rec["creator"]["id"] == 261
    assert rec["isArchived"] is False


def test_game_votes_model_roundtrip_and_defaults():
    raw = dict(VOTES[1], likeRatio=0.92)
    m = GameVotes.model_validate(raw)
    assert m.id == 994732206 and m.up_votes == 12720514 and m.down_votes == 1063632
    assert m.model_extra == {"likeRatio": 0.92}
    assert m.to_record() == raw
    assert GameVotes.model_validate({"id": 5}).up_votes == 0
    assert GameVotes.model_validate({"id": 5}).down_votes == 0


def test_game_server_model_roundtrip():
    raw = dict(SERVERS[0], vipServerId=None)
    m = GameServer.model_validate(raw)
    assert m.id == "c29d1d82-c923-4515-9e53-b3a1074d8326"
    assert m.max_players == 12 and m.playing == 1 and m.fps == 59.984482 and m.ping == 82
    assert m.player_tokens == [] and m.players == []
    assert m.model_extra == {"vipServerId": None}
    rec = m.to_record()
    assert rec == raw and rec["maxPlayers"] == 12 and rec["playerTokens"] == []


def test_game_pass_model_roundtrip():
    raw = dict(GAME_PASSES[0], price=99)
    m = GamePass.model_validate(raw)
    assert m.id == 7578721 and m.product_id == 933434480 and m.is_for_sale is True
    assert m.display_icon_image_asset_id == 84816064670684 and m.created.year == 2019
    assert m.model_extra == {"price": 99}
    rec = m.to_record()
    assert rec["productId"] == 933434480 and rec["displayIconImageAssetId"] == 84816064670684
    assert rec["isForSale"] is True and rec["price"] == 99
    assert rec["created"].startswith("2019-11-18T21:42:55.513")


def test_place_model_roundtrip():
    raw = dict(PLACES[0], isRootPlace=True)
    m = Place.model_validate(raw)
    assert m.id == 2753915549 and m.universe_id == 994732206 and m.name == "Blox Fruits"
    assert m.model_extra == {"isRootPlace": True}
    assert m.to_record() == raw


def test_game_media_model_roundtrip():
    raw = dict(MEDIA[0], displayOrder=0)
    m = GameMedia.model_validate(raw)
    assert m.asset_type_id == 1 and m.asset_type == "Image" and m.image_id == 126410127976844
    assert m.video_hash is None and m.approved is True and m.alt_text == ""
    assert m.model_extra == {"displayOrder": 0}
    assert m.to_record() == raw


def test_created_place_model_roundtrip():
    raw = dict(CREATED_PLACES[0], isActive=True)
    m = CreatedPlace.model_validate(raw)
    assert m.universe_id == 2434560046 and m.place_id == 6504969480
    assert m.creator.name == "Shedletsky" and m.price_in_robux is None
    assert m.model_extra == {"isActive": True}
    rec = m.to_record()
    assert rec["universeId"] == 2434560046 and rec["placeId"] == 6504969480
    assert rec["priceInRobux"] is None and rec["isActive"] is True
    assert "hasVerifiedBadge" not in rec["creator"]  # defaults are not emitted either


def test_models_accept_snake_case_construction():
    m = Game(id=1, name="x", root_place_id=2, genre_l1="Action", favorited_count=3)
    rec = m.to_record()
    assert rec["rootPlaceId"] == 2 and rec["genre_l1"] == "Action" and rec["favoritedCount"] == 3


def test_missing_required_field_raises_validation_error():
    with pytest.raises(ValidationError):
        Game.model_validate({"id": 1})  # name required
    with pytest.raises(ValidationError):
        Game.model_validate({"name": "no id"})
    with pytest.raises(ValidationError):
        GameVotes.model_validate({"upVotes": 1})
    with pytest.raises(ValidationError):
        CreatedPlace.model_validate({"universeId": 1, "name": "no placeId"})
    with pytest.raises(ValidationError):
        GamePass.model_validate({"id": "not-an-int"})
