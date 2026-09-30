"""Collector tests: best-effort omission policy, name hydration, network walks,
and the fixed v1 compatibility functions. All HTTP is faked via routes."""

import json

import pandas as pd
import pytest

from pyroblox.collect import (
    GAME_TABLES, GROUP_TABLES, USER_TABLES, build_dataframes, friend_edgelist,
    friend_network, game_snapshot, group_edgelist, group_network, group_snapshot,
    user_snapshot,
)
from pyroblox.errors import EntityUnavailable, RateLimitedError
from tests.conftest import FakeResponse, make_client, page

U = "https://users.roblox.com/v1"
F = "https://friends.roblox.com/v1"
G = "https://groups.roblox.com/v1"
GM = "https://games.roblox.com"


def user_routes(uid=261, friends=(1, 2)):
    return {
        f"GET {U}/users/{uid}": {"id": uid, "name": "Shedletsky", "displayName": "Shed",
                                 "description": "", "created": "2006-03-27T00:00:00Z",
                                 "isBanned": False, "hasVerifiedBadge": True},
        f"GET {F}/users/{uid}/friends/count": {"count": len(friends)},
        f"GET {F}/users/{uid}/followers/count": {"count": 30},
        f"GET {F}/users/{uid}/followings/count": {"count": 5},
        f"GET {F}/users/{uid}/friends": {"data": [{"id": i, "name": "", "displayName": "",
                                                   "hasVerifiedBadge": False} for i in friends]},
        f"POST {U}/users": {"data": [{"id": i, "name": f"user{i}", "displayName": f"User {i}",
                                      "hasVerifiedBadge": False} for i in friends]},
        f"GET {F}/users/{uid}/followers": FakeResponse(401, {"errors": [{"code": 0, "message": "Authorization has been denied for this request."}]}),
        f"GET {F}/users/{uid}/followings": FakeResponse(401),
        f"GET {G}/users/{uid}/groups/roles": {"data": [{"group": {"id": 7, "name": "Roblox"},
                                                       "role": {"id": 1, "name": "Member", "rank": 1}}]},
        f"GET {GM}/v2/users/{uid}/games": page([{"id": 100, "name": "G"}]),
        f"GET {GM}/v2/users/{uid}/favorite/games": [
            FakeResponse(200, page([{"id": 200, "name": "Fav"}], "c1")),
            FakeResponse(200, page([{"id": 201, "name": "Fav2"}]))],
        f"GET https://badges.roblox.com/v1/users/{uid}/badges": FakeResponse(401),
        f"GET {U}/users/{uid}/username-history": page([{"name": "OldName"}]),
        f"GET https://avatar.roblox.com/v1/users/{uid}/avatar": {
            "playerAvatarType": "R15", "bodyColors": {"headColorId": 1},
            "assets": [{"id": 5, "name": "Hat", "assetType": {"id": 8, "name": "Hat"}}]},
        f"GET https://inventory.roblox.com/v1/users/{uid}/assets/collectibles": FakeResponse(403),
        f"GET https://accountinformation.roblox.com/v1/users/{uid}/roblox-badges": FakeResponse(200, [{"id": 1, "name": "Admin"}, {"id": 2, "name": "Veteran"}]),
        f"GET https://accountinformation.roblox.com/v1/users/{uid}/promotion-channels": {
            "facebook": None, "twitter": None, "youtube": None, "twitch": None},
        "POST https://presence.roblox.com/v1/presence/users": {
            "userPresences": [{"userPresenceType": 0, "userId": uid}]},
    }


def test_user_snapshot_collects_everything_and_records_omissions():
    client, session, _ = make_client(routes=user_routes())
    snap = user_snapshot(client, 261, max_items=1)
    assert snap.entity == "user" and snap.entity_id == 261
    assert snap["profile"][0]["name"] == "Shedletsky"
    assert snap["counts"] == [{"friends": 2, "followers": 30, "followings": 5}]
    # names hydrated from the batch endpoint
    assert [f["name"] for f in snap["friends"]] == ["user1", "user2"]
    assert snap["groups"][0]["group"]["id"] == 7
    assert snap["games"][0]["id"] == 100
    assert snap["favorite_games"][0]["id"] == 200
    assert snap["username_history"] == [{"name": "OldName"}]
    assert snap["avatar"][0]["playerAvatarType"] == "R15"
    assert snap["avatar"][0]["bodyColors"]["headColorId"] == 1
    assert "assets" not in snap["avatar"][0]
    assert snap["avatar_assets"][0]["name"] == "Hat"
    assert [b["name"] for b in snap["roblox_badges"]] == ["Admin", "Veteran"]
    assert snap["presence"][0]["userPresenceType"] == 0
    assert snap.meta["omitted"] == {
        "followers": "cookie-required", "followings": "cookie-required",
        "badges": "cookie-required", "collectibles": "private",
        "promotion_channels": "cookie-required",
    }
    assert snap.meta["truncated"] == {"favorite_games": True}
    assert "followers" not in snap and "badges" not in snap
    # promotion channels are still written (all null) so the columns exist
    assert snap["promotion_channels"][0]["twitter"] is None
    assert session.calls[0].url == f"{U}/users/261"


def test_user_snapshot_include_exclude_and_validation():
    client, session, _ = make_client(routes=user_routes())
    snap = user_snapshot(client, 261, include=["counts", "friends"], hydrate_names=False)
    assert set(snap.tables) == {"profile", "counts", "friends"}
    assert snap["friends"][0]["name"] == ""          # not hydrated
    assert not any(c.method == "POST" for c in session.calls)
    snap = user_snapshot(client, 261, exclude=["friends", "presence", "avatar"])
    assert "friends" not in snap and "avatar_assets" not in snap
    with pytest.raises(ValueError):
        user_snapshot(client, 261, include=["nope"])
    assert "profile" in USER_TABLES and "members" in GROUP_TABLES and "servers" in GAME_TABLES


def test_user_snapshot_primary_failure_raises_entity_unavailable():
    client, _, _ = make_client(routes={
        f"GET {U}/users/5": FakeResponse(400, {"errors": [{"code": 3, "message": "The user is invalid."}]})})
    with pytest.raises(EntityUnavailable) as exc:
        user_snapshot(client, 5)
    assert exc.value.reason == "invalid" and "The user is invalid." in str(exc.value)
    client, _, _ = make_client(routes={f"GET {U}/users/6": FakeResponse(404)})
    with pytest.raises(EntityUnavailable) as exc:
        user_snapshot(client, 6)
    assert exc.value.reason == "not-found"


def test_user_snapshot_rate_limit_propagates():
    routes = user_routes()
    routes[f"GET {F}/users/261/friends/count"] = FakeResponse(429)
    client, _, _ = make_client(routes=routes, max_retries=0)
    with pytest.raises(RateLimitedError):
        user_snapshot(client, 261, include=["counts"])


def test_progress_callback_receives_messages():
    client, _, _ = make_client(routes=user_routes())
    messages = []
    user_snapshot(client, 261, include=["counts"], progress=messages.append)
    assert messages == ["user 261: profile", "user 261: friend/follower counts"]


# -- group snapshot -----------------------------------------------------------

def group_profile(gid, name="Roblox", member_count=3):
    return {"id": gid, "name": name, "description": "", "owner": {"userId": 1, "username": "Roblox"},
            "shout": None, "memberCount": member_count, "publicEntryAllowed": True,
            "isLocked": False, "hasVerifiedBadge": True}


def rows(groups, kind="Allies"):
    return {"groupId": 7, "relationshipType": kind, "totalGroupCount": len(groups),
            "relatedGroups": groups, "nextRowIndex": len(groups)}


def member(uid, role="Member", rank=1):
    return {"user": {"userId": uid, "username": f"u{uid}", "displayName": f"U{uid}",
                     "hasVerifiedBadge": False}, "role": {"id": rank, "name": role, "rank": rank}}


def group_routes():
    return {
        f"GET {G}/groups/7": group_profile(7),
        f"GET {G}/groups/7/roles": {"groupId": 7, "roles": [{"id": 1, "name": "Member", "rank": 1, "memberCount": 3}]},
        f"GET {G}/groups/7/users": [FakeResponse(200, page([member(1), member(2)], "c1")),
                                    FakeResponse(200, page([member(3)]))],
        f"GET {G}/groups/7/relationships/allies": rows([group_profile(8, "Ally")]),
        f"GET {G}/groups/7/relationships/enemies": rows([], "Enemies"),
        f"GET {GM}/v2/groups/7/gamesV2": page([{"id": 300, "name": "Group game"}]),
        f"GET {G}/groups/7/name-history": page([]),
        f"GET {G}/groups/7/social-links": FakeResponse(401),
    }


def test_group_snapshot():
    client, _, _ = make_client(routes=group_routes())
    snap = group_snapshot(client, 7)
    assert snap["profile"][0]["name"] == "Roblox"
    assert snap["roles"][0]["name"] == "Member"
    assert [m["user"]["userId"] for m in snap["members"]] == [1, 2, 3]
    assert snap["allies"][0]["id"] == 8 and snap["enemies"] == []
    assert snap["games"][0]["id"] == 300
    assert snap["name_history"] == []
    assert snap.meta["omitted"] == {"social_links": "cookie-required"}
    assert snap.meta["truncated"] == {}


def test_group_snapshot_max_items_truncates_members():
    client, _, _ = make_client(routes=group_routes())
    snap = group_snapshot(client, 7, include=["members"], max_items=2)
    assert len(snap["members"]) == 2 and snap.meta["truncated"] == {"members": True}


# -- game snapshot ------------------------------------------------------------

def game_routes():
    return {
        "GET https://apis.roblox.com/universes/v1/places/1818/universe": {"universeId": 13058},
        f"GET {GM}/v1/games": {"data": [{"id": 13058, "rootPlaceId": 1818, "name": "Crossroads",
                                          "creator": {"id": 1, "name": "Roblox", "type": "User"},
                                          "visits": 10, "playing": 1}]},
        f"GET {GM}/v1/games/votes": {"data": [{"id": 13058, "upVotes": 9, "downVotes": 1}]},
        f"GET {GM}/v1/games/13058/favorites/count": {"favoritesCount": 42},
        "GET https://develop.roblox.com/v1/universes/13058/places": page([{"id": 1818, "name": "Crossroads"}]),
        f"GET {GM}/v1/games/1818/servers/Public": page([{"id": "s1", "playing": 3}], "more"),
        "GET https://badges.roblox.com/v1/universes/13058/badges": page([{"id": 99, "name": "Winner"}]),
        f"GET {GM}/v2/games/13058/media": {"data": [{"imageId": 5}]},
        "GET https://apis.roblox.com/game-passes/v1/universes/13058/game-passes": {"gamePasses": [{"id": 1, "name": "VIP"}]},
    }


def test_game_snapshot_by_place_resolves_universe():
    client, session, _ = make_client(routes=game_routes())
    snap = game_snapshot(client, 1818, by_place=True, max_servers=1)
    assert snap.entity == "game" and snap.entity_id == 13058
    assert snap.meta["place_id"] == 1818 and snap.meta["root_place_id"] == 1818
    assert snap["profile"][0]["name"] == "Crossroads"
    assert snap["votes"] == [{"id": 13058, "upVotes": 9, "downVotes": 1, "favoritesCount": 42}]
    assert snap["places"][0]["id"] == 1818
    assert snap["servers"][0]["id"] == "s1" and snap["servers"][0]["playing"] == 3
    assert snap.meta["truncated"] == {"servers": True}
    assert snap["badges"][0]["name"] == "Winner"
    assert snap["media"][0]["imageId"] == 5
    assert snap["game_passes"][0]["name"] == "VIP"
    assert session.calls[0].url.endswith("/places/1818/universe")


def test_game_snapshot_by_universe_and_missing_root_place():
    routes = game_routes()
    routes[f"GET {GM}/v1/games"] = {"data": [{"id": 13058, "name": "X"}]}
    client, _, _ = make_client(routes=routes)
    snap = game_snapshot(client, 13058, include=["servers"])
    assert snap.meta["omitted"] == {"servers": "no-root-place"}


def test_game_snapshot_unknown_universe():
    client, _, _ = make_client(routes={f"GET {GM}/v1/games": {"data": []}})
    with pytest.raises(EntityUnavailable):
        game_snapshot(client, 1)


# -- friend network -----------------------------------------------------------

def friend_routes():
    def friends(ids):
        return {"data": [{"id": i, "name": "", "displayName": ""} for i in ids]}
    return {
        f"GET {F}/users/1/friends": friends([2, 3]),
        f"GET {F}/users/2/friends": friends([1, 3, 4]),
        f"GET {F}/users/3/friends": FakeResponse(400, {"errors": [{"message": "The user is invalid."}]}),
        f"GET {F}/users/4/friends": friends([]),
        f"POST {U}/users": {"data": [{"id": i, "name": f"n{i}", "displayName": f"N{i}"} for i in (1, 2, 3, 4)]},
    }


def test_friend_network_depth_1():
    client, session, _ = make_client(routes=friend_routes())
    snap = friend_network(client, 1, depth=1)
    assert snap["edges"] == [{"source": 1, "target": 2}, {"source": 1, "target": 3}]
    nodes = {n["id"]: n for n in snap["nodes"]}
    assert nodes[1]["depth"] == 0 and nodes[1]["expanded"] is True
    assert nodes[2]["depth"] == 1 and nodes[2]["expanded"] is False
    assert nodes[2]["name"] == "n2"
    assert sum(c.url.endswith("/friends") for c in session.calls) == 1


def test_friend_network_depth_2_dedupes_and_records_failures():
    client, session, _ = make_client(routes=friend_routes())
    snap = friend_network(client, 1, depth=2)
    assert snap["edges"] == [{"source": 1, "target": 2}, {"source": 1, "target": 3},
                             {"source": 2, "target": 3}, {"source": 2, "target": 4}]
    assert snap.meta["failed"] == {3: "BadRequestError: The user is invalid."}
    ids = [n["id"] for n in snap["nodes"]]
    assert ids == [1, 2, 3, 4]
    assert {n["id"]: n["depth"] for n in snap["nodes"]} == {1: 0, 2: 1, 3: 1, 4: 2}


def test_friend_network_skips_deleted_friend_placeholders():
    client, _, _ = make_client(routes={
        f"GET {F}/users/1/friends": {"data": [{"id": 2, "name": ""}, {"id": -1, "name": ""},
                                              {"id": -1, "name": ""}]},
        f"POST {U}/users": {"data": [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]},
    })
    snap = friend_network(client, 1, depth=1)
    assert snap["edges"] == [{"source": 1, "target": 2}]
    assert [n["id"] for n in snap["nodes"]] == [1, 2]
    assert snap.meta["hidden_friends_skipped"] == 2


def test_friend_network_max_users_truncates():
    client, session, _ = make_client(routes=friend_routes())
    snap = friend_network(client, 1, depth=2, max_users=2, hydrate_names=False)
    assert snap.meta["truncated"] == {"edges": True}
    assert sum(c.url.endswith("/friends") for c in session.calls) == 2
    assert snap["nodes"][0]["name"] is None
    with pytest.raises(ValueError):
        friend_network(client, 1, depth=0)


# -- group network ------------------------------------------------------------

def network_routes():
    r = {
        f"GET {G}/groups/7": group_profile(7),
        f"GET {G}/groups/7/relationships/allies": rows([group_profile(8, "Ally")]),
        f"GET {G}/groups/7/relationships/enemies": rows([group_profile(9, "Enemy")], "Enemies"),
        f"GET {G}/groups/8/relationships/allies": rows([group_profile(7), group_profile(10, "AllyOfAlly")]),
        f"GET {G}/groups/8/relationships/enemies": rows([], "Enemies"),
        f"GET {G}/groups/9/relationships/allies": FakeResponse(400, {"errors": [{"message": "Group is invalid."}]}),
        f"GET {G}/groups/9/relationships/enemies": FakeResponse(400),
        f"GET {G}/groups/7/users": page([member(1), member(2)]),
        f"GET {G}/groups/8/users": page([member(2), member(3)]),
        f"GET {G}/groups/9/users": page([member(4)]),
        f"GET {U}/users/1": {"id": 1, "name": "u1", "created": "2006-01-01T00:00:00Z", "isBanned": False},
        f"GET {U}/users/2": {"id": 2, "name": "u2", "created": "2007-01-01T00:00:00Z", "isBanned": False},
        f"GET {U}/users/3": FakeResponse(400, {"errors": [{"message": "The user is invalid."}]}),
        f"GET {U}/users/4": {"id": 4, "name": "u4", "created": "2008-01-01T00:00:00Z", "isBanned": True},
        f"GET {GM}/v2/users/1/favorite/games": page([{"id": 500, "name": "A"}, {"id": 501, "name": "B"}]),
        f"GET {GM}/v2/users/2/favorite/games": page([{"id": 500, "name": "A"}]),
        f"GET {GM}/v2/users/3/favorite/games": page([]),
        f"GET {GM}/v2/users/4/favorite/games": FakeResponse(400),
    }
    return r


def test_group_network_edges_and_membership_per_group():
    client, session, _ = make_client(routes=network_routes())
    snap = group_network(client, 7)
    assert sorted(g["id"] for g in snap["groups"]) == [7, 8, 9, 10]
    assert snap["allies"] == [{"source": 7, "target": 8}, {"source": 7, "target": 10},
                              {"source": 8, "target": 10}] or \
        snap["allies"] == [{"source": 7, "target": 8}, {"source": 8, "target": 7},
                           {"source": 8, "target": 10}]
    assert snap["enemies"] == [{"source": 7, "target": 9}]
    assert snap.meta["failed"] == {9: "relationships unavailable (locked or deleted group)"}
    assert snap.meta["omitted"] == {}
    # membership rows are per group (the v1 bug assigned the seed group's members everywhere)
    pairs = sorted((m["groupId"], m["user"]["userId"]) for m in snap["membership"])
    assert pairs == [(7, 1), (7, 2), (8, 2), (8, 3), (9, 4)]
    assert sorted(u["id"] for u in snap["members"]) == [1, 2, 3, 4]
    assert "member_profiles" not in snap and "favorite_games" not in snap
    # the single-group GET (7/min) is used only for the seed group
    assert [c.url for c in session.calls if c.url.startswith(f"{G}/groups/") and c.url.count("/") == 5] == [f"{G}/groups/7"]


def test_group_network_directed_ally_edges_are_kept_as_reported():
    client, _, _ = make_client(routes=network_routes())
    snap = group_network(client, 7, include_members=False)
    assert {(e["source"], e["target"]) for e in snap["allies"]} == {(7, 8), (8, 7), (8, 10)}
    assert "membership" not in snap


def test_group_network_profiles_and_favorites():
    client, _, _ = make_client(routes=network_routes())
    snap = group_network(client, 7, include_member_profiles=True, include_favorites=True)
    assert sorted(p["id"] for p in snap["member_profiles"]) == [1, 2, 4]
    assert snap.meta["failed"][3] == "profile unavailable" or snap.meta["failed"][3] == "favorites unavailable"
    assert snap["favorite_games"] == [{"userId": 1, "universeId": 500}, {"userId": 1, "universeId": 501},
                                      {"userId": 2, "universeId": 500}]
    assert sorted(g["id"] for g in snap["games"]) == [500, 501]
    assert snap.meta["failed"][4] == "favorites unavailable"


def test_group_network_max_groups_and_max_members():
    client, _, _ = make_client(routes=network_routes())
    snap = group_network(client, 7, max_groups=1, max_members=1)
    assert snap.meta["truncated"] == {"groups": True, "membership": True}
    assert sorted({m["groupId"] for m in snap["membership"]}) == [7, 8]


# -- v1 compatibility ---------------------------------------------------------

def test_group_edgelist_and_friend_edgelist_shapes():
    client, _, _ = make_client(routes=network_routes())
    el = group_edgelist(7, client=client)
    assert set(el) == {"allies", "enemies"}
    assert [7, 8] in el["allies"] and el["enemies"] == [[7, 9]]
    client, _, _ = make_client(routes=friend_routes())
    assert friend_edgelist(1, client=client) == [[1, 2], [1, 3], [2, 3], [2, 4]]


def test_build_dataframes_writes_v1_files_with_fixed_contents(tmp_path):
    client, _, _ = make_client(routes=network_routes())
    frames = build_dataframes(7, {".ROBLOSECURITY": "ignored-when-client-given"},
                              output_dir=tmp_path, client=client)
    expected = {f"allies_7_edgelist.csv", "enemies_7_edgelist.csv", "group_info_7.csv",
                "membership_7_edgelist.csv", "user_info_membership_7.csv",
                "asset_el7.csv", "asset_info_7.csv"}
    assert {p.name for p in tmp_path.iterdir()} == expected
    membership = pd.read_csv(tmp_path / "membership_7_edgelist.csv")
    assert list(membership.columns) == ["Group", "User"]
    assert sorted(map(tuple, membership.values.tolist())) == [(7, 1), (7, 2), (8, 2), (8, 3), (9, 4)]
    assets = pd.read_csv(tmp_path / "asset_el7.csv")
    assert list(assets.columns) == ["User", "FavoritedGame"] and len(assets) == 3
    allies = pd.read_csv(tmp_path / "allies_7_edgelist.csv")
    assert list(allies.columns) == ["From", "To"]
    users = pd.read_csv(tmp_path / "user_info_membership_7.csv")
    assert "isBanned" in users.columns and len(users) == 3
    assert isinstance(frames["membership"], pd.DataFrame) and "snapshot" in frames
