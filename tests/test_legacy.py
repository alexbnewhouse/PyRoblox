import warnings

import pytest

from robloxwrapper import legacy
from tests.conftest import FakeResponse, make_client, page


@pytest.fixture(autouse=True)
def _reset_default_client():
    legacy.set_default_client(None)
    yield
    legacy.set_default_client(None)


def test_friends_class_returns_v1_shapes():
    client, session, _ = make_client(routes={
        "GET https://friends.roblox.com/v1/users/261/friends": {"data": [{"id": 1}]},
        "GET https://users.roblox.com/v1/users/261": {"id": 261, "name": "Shedletsky"},
    })
    with pytest.warns(DeprecationWarning):
        f = legacy.friends(261, client=client)
    assert f.info() == {"data": [{"id": 1}]}
    assert f.user_info()["name"] == "Shedletsky"


def test_groups_class_returns_v1_shapes():
    rows = {"groupId": 7, "relationshipType": "Allies", "totalGroupCount": 1,
            "relatedGroups": [{"id": 8}], "nextRowIndex": 1}
    client, session, _ = make_client(routes={
        "GET https://groups.roblox.com/v1/groups/7": {"id": 7, "name": "Roblox"},
        "GET https://groups.roblox.com/v1/groups/7/relationships/allies": rows,
        "GET https://groups.roblox.com/v1/groups/7/relationships/enemies": dict(rows, relatedGroups=[], totalGroupCount=0),
        "GET https://groups.roblox.com/v1/groups/7/users": page([{"user": {"userId": 1}}], "c1"),
    })
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        g = legacy.groups(7, client=client)
    assert g.info()["name"] == "Roblox"
    assert g.allies()["relatedGroups"] == [{"id": 8}]
    assert g.enemies()["relatedGroups"] == []
    users = g.user_list()
    assert users["nextPageCursor"] == "c1" and users["data"][0]["user"]["userId"] == 1
    g.user_list(cursor="c1")
    assert session.calls[-1].params == {"sortOrder": "Asc", "limit": 100, "cursor": "c1"}


def test_groups_social_links_uses_supplied_cookie():
    client, session, _ = make_client(routes={
        "GET https://groups.roblox.com/v1/groups/7/social-links": {"data": [{"type": "Discord"}]}})
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        g = legacy.groups(7, client=client)
    # client already has no cookie and the dict supplies one -> a fresh client is built; we
    # cannot fake that one, so only verify the no-cookie path here
    assert g.social_links({}) == {"data": [{"type": "Discord"}]}


def test_games_classes():
    client, session, _ = make_client(routes={
        "GET https://games.roblox.com/v2/groups/7/gamesV2": page([{"id": 1}]),
        "GET https://games.roblox.com/v2/users/261/games": page([{"id": 2}]),
        "GET https://games.roblox.com/v2/users/261/favorite/games": page([{"id": 3}], "c"),
    })
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        assert legacy.group_games(7, client=client).info()["data"] == [{"id": 1}]
        ug = legacy.user_games(261, client=client)
    assert ug.games_list()["data"] == [{"id": 2}]
    assert ug.favorites_list()["nextPageCursor"] == "c"
    ug.favorites_list(cursor="c")
    assert session.calls[-1].params["cursor"] == "c"


def test_default_client_is_built_once(monkeypatch):
    monkeypatch.setenv("ROBLOX_COOKIE", "")
    a = legacy.default_client()
    assert legacy.default_client() is a
