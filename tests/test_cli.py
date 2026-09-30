"""CLI tests. A fake client is injected through ``obj={"client": ...}`` so no
command ever touches the network."""

import json
from pathlib import Path

import pandas as pd
import pytest
from click.testing import CliRunner

from robloxwrapper import __version__
from robloxwrapper.cli import cli
from tests.conftest import FakeResponse, make_client, page

U = "https://users.roblox.com/v1"
F = "https://friends.roblox.com/v1"
G = "https://groups.roblox.com/v1"
GM = "https://games.roblox.com"


@pytest.fixture
def runner():
    return CliRunner()


def run(runner, client, args, cwd):
    """Invoke the CLI with a fake client, output dir inside ``cwd``."""
    return runner.invoke(cli, ["-o", str(cwd / "out")] + args, obj={"client": client},
                         catch_exceptions=False)


def user_profile(uid=261):
    return {"id": uid, "name": "Shedletsky", "displayName": "Shed", "description": "hi",
            "created": "2006-03-27T00:00:00Z", "isBanned": False, "hasVerifiedBadge": True}


# -- basics -------------------------------------------------------------------

def test_help_and_version(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    for group_name in ("check", "resolve", "user", "group", "game", "search", "batch"):
        assert group_name in result.output
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0 and __version__ in result.output
    for sub in ("user", "group", "game", "search", "batch"):
        result = runner.invoke(cli, [sub, "--help"])
        assert result.exit_code == 0, sub


def test_max_option_only_on_paginated_commands(runner):
    paged = [["user", "friends"], ["user", "groups"], ["group", "members"], ["group", "allies"],
             ["game", "servers"], ["game", "badges"], ["game", "places"]]
    unpaged = [["user", "info"], ["user", "counts"], ["user", "avatar"], ["user", "presence"],
               ["group", "info"], ["group", "roles"], ["game", "info"], ["game", "votes"],
               ["game", "passes"]]
    for args in paged:
        assert "--max" in runner.invoke(cli, args + ["--help"]).output, args
    for args in unpaged:
        assert "--max" not in runner.invoke(cli, args + ["--help"]).output, args


def test_check_without_cookie(runner, tmp_path):
    client, _, _ = make_client(routes={f"GET {U}/users/1": {"id": 1, "name": "Roblox"}})
    result = run(runner, client, ["check"], tmp_path)
    assert result.exit_code == 0
    assert "Roblox reachable: yes" in result.output
    assert "Cookie: none" in result.output
    assert "Everything looks good." in result.output


def test_check_with_valid_and_rejected_cookie(runner, tmp_path):
    client, _, _ = make_client(routes={
        f"GET {U}/users/1": {"id": 1, "name": "Roblox"},
        f"GET {U}/users/authenticated": {"id": 5, "name": "me"}}, cookie="SECRET")
    result = run(runner, client, ["check"], tmp_path)
    assert "Cookie: valid, logged in as 'me'" in result.output

    client, _, _ = make_client(routes={
        f"GET {U}/users/1": {"id": 1, "name": "Roblox"},
        f"GET {U}/users/authenticated": [FakeResponse(401), FakeResponse(401)]}, cookie="BAD")
    result = run(runner, client, ["check"], tmp_path)
    assert "Cookie: REJECTED" in result.output


def test_resolve_link_username_and_place(runner, tmp_path):
    client, _, _ = make_client(routes={
        f"POST {U}/usernames/users": {"data": [{"requestedUsername": "Shedletsky", "id": 261,
                                                 "name": "Shedletsky", "displayName": "Shed"}]},
        "GET https://apis.roblox.com/universes/v1/places/1818/universe": {"universeId": 13058},
    })
    assert run(runner, client, ["resolve", "https://www.roblox.com/groups/7/Roblox"], tmp_path).output.strip() == "group 7"
    out = run(runner, client, ["resolve", "Shedletsky"], tmp_path).output
    assert "user 261 (Shedletsky" in out
    out = run(runner, client, ["resolve", "https://www.roblox.com/games/1818/x"], tmp_path).output
    assert "place 1818 belongs to universe 13058" in out
    result = run(runner, client, ["resolve", "1818"], tmp_path)
    assert result.exit_code != 0 and "bare number" in result.output


# -- user commands ------------------------------------------------------------

def test_user_info_writes_csv_and_accepts_username_and_link(runner, tmp_path):
    client, session, _ = make_client(routes={
        f"GET {U}/users/261": user_profile(),
        f"POST {U}/usernames/users": {"data": [{"requestedUsername": "Shedletsky", "id": 261, "name": "Shedletsky"}]},
    })
    result = run(runner, client, ["user", "info", "261"], tmp_path)
    assert result.exit_code == 0, result.output
    assert "Shedletsky (display name 'Shed', id 261)" in result.output
    csv_path = tmp_path / "out" / "user_261_profile.csv"
    assert f"Wrote 1 row(s) to {csv_path}" in result.output
    df = pd.read_csv(csv_path)
    assert df.iloc[0]["name"] == "Shedletsky" and df.iloc[0]["id"] == 261

    result = run(runner, client, ["user", "info", "Shedletsky"], tmp_path)
    assert result.exit_code == 0 and "Resolved username 'Shedletsky' to user id 261" in result.output
    result = run(runner, client, ["user", "info", "https://www.roblox.com/users/261/profile"], tmp_path)
    assert result.exit_code == 0
    result = run(runner, client, ["user", "info", "https://www.roblox.com/groups/7/x"], tmp_path)
    assert result.exit_code != 0 and "group link, not a user" in result.output


def test_user_info_stdout_and_json_format(runner, tmp_path):
    client, _, _ = make_client(routes={f"GET {U}/users/261": user_profile()})
    result = runner.invoke(cli, ["--stdout", "user", "info", "261"], obj={"client": client})
    assert result.exit_code == 0
    assert json.loads(result.output)["name"] == "Shedletsky"
    result = run(runner, client, ["-f", "json", "user", "info", "261"], tmp_path)
    assert json.loads((tmp_path / "out" / "user_261_profile.json").read_text())[0]["id"] == 261


def test_user_friends_hydrates_names(runner, tmp_path):
    client, _, _ = make_client(routes={
        f"GET {F}/users/261/friends": {"data": [{"id": 1, "name": ""}, {"id": 2, "name": ""}]},
        f"POST {U}/users": {"data": [{"id": 1, "name": "a", "displayName": "A"},
                                     {"id": 2, "name": "b", "displayName": "B"}]},
    })
    result = run(runner, client, ["user", "friends", "261", "--max", "1"], tmp_path)
    assert result.exit_code == 0 and "1 friend(s)" in result.output
    df = pd.read_csv(tmp_path / "out" / "user_261_friends.csv")
    assert list(df["name"]) == ["a"]


def test_user_simple_commands(runner, tmp_path):
    client, _, _ = make_client(routes={
        f"GET {F}/users/261/friends/count": {"count": 2},
        f"GET {F}/users/261/followers/count": {"count": 3},
        f"GET {F}/users/261/followings/count": {"count": 4},
        f"GET {G}/users/261/groups/roles": {"data": [{"group": {"id": 7, "name": "R"}, "role": {"name": "Member"}}]},
        f"GET {GM}/v2/users/261/games": page([{"id": 1}]),
        f"GET {GM}/v2/users/261/favorite/games": page([{"id": 2}]),
        f"GET {U}/users/261/username-history": page([{"name": "old"}]),
        "GET https://avatar.roblox.com/v1/users/261/avatar": {"playerAvatarType": "R15", "assets": [{"id": 9, "name": "Hat"}]},
        "GET https://accountinformation.roblox.com/v1/users/261/promotion-channels": {"twitter": "shed", "youtube": None},
        "POST https://presence.roblox.com/v1/presence/users": {"userPresences": [{"userPresenceType": 2, "userId": 261}]},
    })
    checks = [
        (["user", "counts", "261"], "friends 2, followers 3, following 4", "user_261_counts.csv"),
        (["user", "groups", "261"], "1 group(s)", "user_261_groups.csv"),
        (["user", "games", "261"], "1 game(s)", "user_261_games.csv"),
        (["user", "favorites", "261"], "1 favourite game(s)", "user_261_favorite_games.csv"),
        (["user", "history", "261"], "1 previous name(s)", "user_261_username_history.csv"),
        (["user", "avatar", "261"], "1 worn item(s); avatar type R15", "user_261_avatar_assets.csv"),
        (["user", "social", "261"], "twitter: shed", "user_261_promotion_channels.csv"),
        (["user", "presence", "261"], "status: in game", "user_261_presence.csv"),
    ]
    for args, expected, filename in checks:
        result = run(runner, client, args, tmp_path)
        assert result.exit_code == 0, (args, result.output)
        assert expected in result.output, (args, result.output)
        assert (tmp_path / "out" / filename).exists(), filename
    df = pd.read_csv(tmp_path / "out" / "user_261_groups.csv")
    assert "group_name" in df.columns and "role_name" in df.columns


def test_user_cookie_only_commands_explain_the_cookie(runner, tmp_path):
    client, _, _ = make_client(routes={
        f"GET {F}/users/261/followers": FakeResponse(401),
        "GET https://badges.roblox.com/v1/users/261/badges": FakeResponse(401),
    })
    result = run(runner, client, ["user", "followers", "261"], tmp_path)
    assert result.exit_code == 1 and "logged-in accounts" in result.output and "--cookie" in result.output
    result = run(runner, client, ["user", "badges", "261"], tmp_path)
    assert result.exit_code == 1 and "--cookie" in result.output


def test_user_snapshot_reports_tables_and_omissions(runner, tmp_path):
    client, _, _ = make_client(routes={
        f"GET {U}/users/261": user_profile(),
        f"GET {F}/users/261/friends/count": {"count": 0},
        f"GET {F}/users/261/followers/count": {"count": 0},
        f"GET {F}/users/261/followings/count": {"count": 0},
        f"GET {F}/users/261/followers": FakeResponse(401),
    })
    result = run(runner, client, ["user", "snapshot", "261", "--only", "counts,followers"], tmp_path)
    assert result.exit_code == 0, result.output
    assert "Saved 2 table(s) for user 261" in result.output
    assert "followers" in result.output and "logged-in accounts" in result.output
    manifest = json.loads((tmp_path / "out" / "user_261_manifest.json").read_text())
    assert manifest["omitted"] == {"followers": "cookie-required"}
    assert "  ... user 261: profile" in result.output   # progress goes to stderr, captured together
    assert (tmp_path / "out" / "user_261_counts.csv").exists()
    result = run(runner, client, ["user", "snapshot", "261", "--only", "bogus"], tmp_path)
    assert result.exit_code == 1 and "unknown table" in result.output


def test_user_snapshot_entity_unavailable_message(runner, tmp_path):
    client, _, _ = make_client(routes={f"GET {U}/users/5": FakeResponse(400, {"errors": [{"message": "The user is invalid."}]})})
    result = run(runner, client, ["user", "snapshot", "5"], tmp_path)
    assert result.exit_code == 1
    assert "user 5 rejected by Roblox: The user is invalid." in result.output


def test_user_network_with_graphml(runner, tmp_path):
    client, _, _ = make_client(routes={
        f"GET {F}/users/1/friends": {"data": [{"id": 2, "name": ""}]},
        f"POST {U}/users": {"data": [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]},
    })
    result = run(runner, client, ["user", "network", "1", "--graphml"], tmp_path)
    assert result.exit_code == 0, result.output
    assert (tmp_path / "out" / "friend_network_1_edges.csv").exists()
    assert (tmp_path / "out" / "friend_network_1.graphml").exists()
    assert "GraphML:" in result.output
    result = run(runner, client, ["user", "network", "1", "--depth", "2", "--max-users", "1"], tmp_path)
    assert result.exit_code == 0 and "Depth 2+" in result.output


# -- group commands -----------------------------------------------------------

def group_profile(gid=7):
    return {"id": gid, "name": "Roblox", "owner": {"userId": 1, "username": "Roblox"},
            "memberCount": 2, "isLocked": False, "description": ""}


def test_group_commands(runner, tmp_path):
    rows = {"groupId": 7, "relationshipType": "Allies", "totalGroupCount": 1,
            "relatedGroups": [{"id": 8, "name": "Ally"}], "nextRowIndex": 1}
    client, _, _ = make_client(routes={
        f"GET {G}/groups/7": group_profile(),
        f"GET {G}/groups/7/users": page([{"user": {"userId": 1, "username": "a"}, "role": {"name": "Member"}}]),
        f"GET {G}/groups/7/roles": {"roles": [{"id": 1, "name": "Member", "rank": 1}]},
        f"GET {G}/groups/7/relationships/allies": rows,
        f"GET {G}/groups/7/relationships/enemies": dict(rows, relatedGroups=[], totalGroupCount=0),
        f"GET {GM}/v2/groups/7/gamesV2": page([{"id": 3}]),
        f"GET {G}/groups/7/name-history": page([]),
        f"GET {G}/groups/7/social-links": FakeResponse(401),
    })
    checks = [
        (["group", "info", "7"], "Roblox (id 7)", "group_7_profile.csv"),
        (["group", "members", "https://www.roblox.com/communities/7/Roblox"], "1 member(s)", "group_7_members.csv"),
        (["group", "roles", "7"], "1 role(s)", "group_7_roles.csv"),
        (["group", "allies", "7"], "1 ally group(s)", "group_7_allies.csv"),
        (["group", "enemies", "7"], "0 enemy group(s)", "group_7_enemies.csv"),
        (["group", "games", "7"], "1 game(s)", "group_7_games.csv"),
        (["group", "history", "7"], "0 previous name(s)", "group_7_name_history.csv"),
    ]
    for args, expected, filename in checks:
        result = run(runner, client, args, tmp_path)
        assert result.exit_code == 0, (args, result.output)
        assert expected in result.output, (args, result.output)
        assert (tmp_path / "out" / filename).exists(), filename
    df = pd.read_csv(tmp_path / "out" / "group_7_members.csv")
    assert "user_userId" in df.columns and "role_name" in df.columns
    result = run(runner, client, ["group", "social", "7"], tmp_path)
    assert result.exit_code == 1 and "--cookie" in result.output
    result = run(runner, client, ["group", "info", "Roblox"], tmp_path)
    assert result.exit_code != 0 and "search groups" in result.output
    result = run(runner, client, ["group", "snapshot", "7", "--skip", "members,social_links"], tmp_path)
    assert result.exit_code == 0 and "Saved 6 table(s) for group 7" in result.output


def test_group_network_command(runner, tmp_path):
    rows = {"groupId": 7, "relationshipType": "Allies", "totalGroupCount": 1,
            "relatedGroups": [{"id": 8, "name": "Ally", "memberCount": 1}], "nextRowIndex": 1}
    empty = dict(rows, relatedGroups=[], totalGroupCount=0)
    client, _, _ = make_client(routes={
        f"GET {G}/groups/7": group_profile(),
        f"GET {G}/groups/7/relationships/allies": rows,
        f"GET {G}/groups/7/relationships/enemies": empty,
        f"GET {G}/groups/8/relationships/allies": empty,
        f"GET {G}/groups/8/relationships/enemies": empty,
        f"GET {G}/groups/7/users": page([{"user": {"userId": 1, "username": "a"}, "role": {"name": "M"}}]),
        f"GET {G}/groups/8/users": page([{"user": {"userId": 2, "username": "b"}, "role": {"name": "M"}}]),
    })
    result = run(runner, client, ["group", "network", "7", "--graphml"], tmp_path)
    assert result.exit_code == 0, result.output
    assert "Saved 5 table(s) for group_network 7" in result.output
    assert (tmp_path / "out" / "group_network_7_membership.csv").exists()
    assert (tmp_path / "out" / "group_network_7_allies.graphml").exists()
    result = run(runner, client, ["group", "network", "7", "--no-members"], tmp_path)
    assert "Saved 3 table(s)" in result.output


# -- game commands ------------------------------------------------------------

def test_game_commands(runner, tmp_path):
    client, _, _ = make_client(routes={
        "GET https://apis.roblox.com/universes/v1/places/1818/universe": {"universeId": 13058},
        f"GET {GM}/v1/games": {"data": [{"id": 13058, "rootPlaceId": 1818, "name": "Crossroads",
                                          "creator": {"id": 1, "name": "Roblox", "type": "User"},
                                          "visits": 5, "playing": 0}]},
        f"GET {GM}/v1/games/votes": {"data": [{"id": 13058, "upVotes": 1, "downVotes": 0}]},
        f"GET {GM}/v1/games/13058/favorites/count": {"favoritesCount": 3},
        f"GET {GM}/v1/games/1818/servers/Public": page([{"id": "s", "playing": 1}]),
        "GET https://badges.roblox.com/v1/universes/13058/badges": page([{"id": 1}]),
        "GET https://apis.roblox.com/game-passes/v1/universes/13058/game-passes": {"gamePasses": []},
        "GET https://develop.roblox.com/v1/universes/13058/places": page([{"id": 1818}]),
        f"GET {GM}/v2/games/13058/media": {"data": []},
    })
    checks = [
        (["game", "info", "13058"], "Crossroads (universe 13058, root place 1818)", "game_13058_profile.csv"),
        (["game", "info", "1818", "--place"], "Resolved place 1818 to universe 13058", "game_13058_profile.csv"),
        (["game", "info", "https://www.roblox.com/games/1818/Classic-Crossroads"], "Crossroads", "game_13058_profile.csv"),
        (["game", "votes", "13058"], "up 1  down 0  favourites 3", "game_13058_votes.csv"),
        (["game", "servers", "13058"], "1 server(s)", "game_13058_servers.csv"),
        (["game", "badges", "13058"], "1 badge(s)", "game_13058_badges.csv"),
        (["game", "passes", "13058"], "0 game pass(es)", "game_13058_game_passes.csv"),
        (["game", "places", "13058"], "1 place(s)", "game_13058_places.csv"),
    ]
    for args, expected, filename in checks:
        result = run(runner, client, args, tmp_path)
        assert result.exit_code == 0, (args, result.output)
        assert expected in result.output, (args, result.output)
        assert (tmp_path / "out" / filename).exists(), filename
    result = run(runner, client, ["game", "snapshot", "1818", "--place"], tmp_path)
    assert result.exit_code == 0 and "Saved 7 table(s) for game 13058" in result.output
    result = run(runner, client, ["game", "info", "https://www.roblox.com/users/1/profile"], tmp_path)
    assert result.exit_code != 0 and "user link, not a game" in result.output


# -- search / batch -----------------------------------------------------------

def test_search_and_batch(runner, tmp_path):
    client, session, _ = make_client(routes={
        f"GET {U}/users/search": page([{"id": 261, "name": "Shedletsky", "previousUsernames": ["x", "y"]}]),
        f"GET {G}/groups/search": page([{"id": 7, "name": "Roblox"}]),
        f"POST {U}/users": {"data": [{"id": 1, "name": "Roblox"}, {"id": 261, "name": "Shedletsky"}]},
        "GET https://groups.roblox.com/v2/groups": {"data": [{"id": 7, "name": "Roblox"}]},
        f"GET {U}/users/1": {"id": 1, "name": "Roblox"},
        f"GET {U}/users/261": FakeResponse(400, {"errors": [{"message": "The user is invalid."}]}),
    })
    result = run(runner, client, ["search", "users", "shedletsky"], tmp_path)
    assert result.exit_code == 0 and "1 result(s)" in result.output
    df = pd.read_csv(tmp_path / "out" / "search_users_shedletsky.csv")
    assert df.iloc[0]["previousUsernames"] == "x;y"
    result = run(runner, client, ["search", "groups", "Roblox admins!"], tmp_path)
    assert result.exit_code == 0 and (tmp_path / "out" / "search_groups_Roblox_admins_.csv").exists()

    ids = tmp_path / "ids.txt"
    ids.write_text("1\nhttps://www.roblox.com/users/261/profile\n# comment\n\n")
    result = run(runner, client, ["batch", "users", str(ids)], tmp_path)
    assert result.exit_code == 0 and "2 of 2 found" in result.output
    assert session.calls[-1].json == {"userIds": [1, 261], "excludeBannedUsers": False}
    result = run(runner, client, ["batch", "users", str(ids), "--full"], tmp_path)
    assert result.exit_code == 0
    df = pd.read_csv(tmp_path / "out" / "batch_users_ids.csv")
    assert df.iloc[1]["error"] == "The user is invalid."
    gids = tmp_path / "groups.txt"
    gids.write_text("7\n")
    result = run(runner, client, ["batch", "groups", str(gids)], tmp_path)
    assert result.exit_code == 0 and "1 of 1 found" in result.output
    bad = tmp_path / "bad.txt"
    bad.write_text("not an id\n")
    result = run(runner, client, ["batch", "users", str(bad)], tmp_path)
    assert result.exit_code != 0 and "Cannot read an id" in result.output


# -- error handling -----------------------------------------------------------

def test_friendly_errors_and_debug(runner, tmp_path):
    client, _, _ = make_client(routes={
        f"GET {U}/users/1": FakeResponse(404),
        f"GET {U}/users/2": FakeResponse(429),
        f"GET {U}/users/3": FakeResponse(503),
        f"GET {U}/users/4": FakeResponse(403),
    }, max_retries=0)
    assert "Not found" in run(runner, client, ["user", "info", "1"], tmp_path).output
    assert "rate limiting" in run(runner, client, ["user", "info", "2"], tmp_path).output
    assert "servers returned an error" in run(runner, client, ["user", "info", "3"], tmp_path).output
    assert "private or hidden" in run(runner, client, ["user", "info", "4"], tmp_path).output
    result = runner.invoke(cli, ["--debug", "-o", str(tmp_path), "user", "info", "1"], obj={"client": client})
    assert result.exit_code != 0 and result.exception is not None
    assert type(result.exception).__name__ == "NotFoundError"


def test_config_file_and_env_are_used(runner, tmp_path, monkeypatch):
    cfg = tmp_path / "settings.yaml"
    cfg.write_text(f"output_dir: {tmp_path / 'from_config'}\n")
    client, _, _ = make_client(routes={f"GET {U}/users/261": user_profile()})
    result = runner.invoke(cli, ["--config", str(cfg), "user", "info", "261"], obj={"client": client})
    assert result.exit_code == 0 and (tmp_path / "from_config" / "user_261_profile.csv").exists()
    monkeypatch.setenv("ROBLOX_OUTPUT_DIR", str(tmp_path / "from_env"))
    result = runner.invoke(cli, ["user", "info", "261"], obj={"client": client})
    assert result.exit_code == 0 and (tmp_path / "from_env" / "user_261_profile.csv").exists()
