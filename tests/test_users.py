"""Tests for :mod:`robloxwrapper.users`. No network: every test uses the
FakeSession from conftest and asserts the exact request that would be sent."""

import pytest

from robloxwrapper.client import PagedList
from robloxwrapper.errors import AuthRequiredError, NotFoundError
from tests.conftest import FakeResponse, make_client, page

BASE = "https://users.roblox.com"

# Real shapes copied from the API probe (GET /v1/users/261 etc.).
USER_261 = {
    "description": '"He came like the wind, like the wind touched everything, '
                   'and like the wind was gone."',
    "created": "2006-06-22T01:33:56.45Z",
    "isBanned": False,
    "externalAppDisplayName": None,
    "hasVerifiedBadge": True,
    "id": 261,
    "name": "Shedletsky",
    "displayName": "Shedletsky",
}
BATCH_1 = {"hasVerifiedBadge": True, "id": 1, "name": "Roblox", "displayName": "Roblox"}
BATCH_261 = {"hasVerifiedBadge": True, "id": 261, "name": "Shedletsky",
             "displayName": "Shedletsky"}
BY_NAME_1 = {"requestedUsername": "Roblox", "hasVerifiedBadge": True, "id": 1,
             "name": "Roblox", "displayName": "Roblox"}
BY_NAME_261 = {"requestedUsername": "Shedletsky", "hasVerifiedBadge": True, "id": 261,
               "name": "Shedletsky", "displayName": "Shedletsky"}
SEARCH_261 = {"previousUsernames": [], "hasVerifiedBadge": True, "id": 261,
              "name": "Shedletsky", "displayName": "Shedletsky"}


# -- get ----------------------------------------------------------------------

def test_get_returns_user_object():
    client, session, _ = make_client(routes={f"GET {BASE}/v1/users/261": USER_261})
    assert client.users.get(261) == USER_261
    call = session.calls[0]
    assert call.method == "GET"
    assert call.url == f"{BASE}/v1/users/261"
    assert not call.params


def test_get_unknown_id_raises_not_found():
    body = {"errors": [{"code": 3, "message": "The user id is invalid."}]}
    client, _, _ = make_client([FakeResponse(404, body)])
    with pytest.raises(NotFoundError) as exc:
        client.users.get(726527401)
    assert exc.value.url == f"{BASE}/v1/users/726527401"


# -- batch_get ----------------------------------------------------------------

def test_batch_get_posts_ids_and_unwraps_data():
    client, session, _ = make_client(
        routes={f"POST {BASE}/v1/users": {"data": [BATCH_1, BATCH_261]}})
    assert client.users.batch_get([1, 261]) == [BATCH_1, BATCH_261]
    call = session.calls[0]
    assert call.method == "POST"
    assert call.url == f"{BASE}/v1/users"
    assert call.json == {"userIds": [1, 261], "excludeBannedUsers": False}


def test_batch_get_exclude_banned_flag():
    client, session, _ = make_client(routes={f"POST {BASE}/v1/users": {"data": []}})
    assert client.users.batch_get([1], exclude_banned=True) == []
    assert session.calls[0].json == {"userIds": [1], "excludeBannedUsers": True}


def test_batch_get_chunks_150_ids_into_two_posts():
    ids = list(range(1, 151))
    first = [{"id": i, "name": f"u{i}", "displayName": f"u{i}", "hasVerifiedBadge": False}
             for i in ids[:100]]
    second = [{"id": i, "name": f"u{i}", "displayName": f"u{i}", "hasVerifiedBadge": False}
              for i in ids[100:]]
    client, session, _ = make_client(
        [FakeResponse(200, {"data": first}), FakeResponse(200, {"data": second})])
    out = client.users.batch_get(iter(ids))  # any iterable, not just a list
    assert isinstance(out, list) and out == first + second
    assert len(session.calls) == 2
    assert session.calls[0].json == {"userIds": ids[:100], "excludeBannedUsers": False}
    assert session.calls[1].json == {"userIds": ids[100:], "excludeBannedUsers": False}


def test_batch_get_empty_input_sends_nothing():
    client, session, _ = make_client(routes={})
    assert client.users.batch_get([]) == []
    assert session.calls == []


# -- by_usernames / resolve ---------------------------------------------------

def test_by_usernames_posts_names_and_unwraps_data():
    client, session, _ = make_client(
        routes={f"POST {BASE}/v1/usernames/users": {"data": [BY_NAME_1, BY_NAME_261]}})
    assert client.users.by_usernames(["Roblox", "Shedletsky"]) == [BY_NAME_1, BY_NAME_261]
    call = session.calls[0]
    assert call.method == "POST"
    assert call.url == f"{BASE}/v1/usernames/users"
    assert call.json == {"usernames": ["Roblox", "Shedletsky"], "excludeBannedUsers": False}


def test_by_usernames_exclude_banned_flag():
    client, session, _ = make_client(
        routes={f"POST {BASE}/v1/usernames/users": {"data": []}})
    client.users.by_usernames(["Roblox"], exclude_banned=True)
    assert session.calls[0].json == {"usernames": ["Roblox"], "excludeBannedUsers": True}


def test_by_usernames_chunks_150_names_into_two_posts():
    names = [f"user{i}" for i in range(150)]
    first = [{"requestedUsername": n, "id": i, "name": n, "displayName": n,
              "hasVerifiedBadge": False} for i, n in enumerate(names[:100])]
    second = [{"requestedUsername": n, "id": 100 + i, "name": n, "displayName": n,
               "hasVerifiedBadge": False} for i, n in enumerate(names[100:])]
    client, session, _ = make_client(
        [FakeResponse(200, {"data": first}), FakeResponse(200, {"data": second})])
    assert client.users.by_usernames(names) == first + second
    assert len(session.calls) == 2
    assert session.calls[0].json["usernames"] == names[:100]
    assert session.calls[1].json["usernames"] == names[100:]


def test_resolve_returns_single_match():
    client, session, _ = make_client(
        routes={f"POST {BASE}/v1/usernames/users": {"data": [BY_NAME_261]}})
    assert client.users.resolve("Shedletsky") == BY_NAME_261
    assert session.calls[0].url == f"{BASE}/v1/usernames/users"
    assert session.calls[0].json == {"usernames": ["Shedletsky"],
                                    "excludeBannedUsers": False}


def test_resolve_unknown_username_raises_not_found():
    client, _, _ = make_client(routes={f"POST {BASE}/v1/usernames/users": {"data": []}})
    with pytest.raises(NotFoundError) as exc:
        client.users.resolve("nobody_here_xyz")
    assert "username 'nobody_here_xyz' not found" in str(exc.value)
    assert exc.value.url == f"{BASE}/v1/usernames/users"


# -- username_history ---------------------------------------------------------

def test_username_history_paginates_with_limit_100_asc():
    client, session, _ = make_client([
        FakeResponse(200, page([{"name": "OldName1"}, {"name": "OldName2"}], "c1")),
        FakeResponse(200, page([{"name": "OldName3"}], None)),
    ])
    out = client.users.username_history(261)
    assert isinstance(out, PagedList)
    assert out == [{"name": "OldName1"}, {"name": "OldName2"}, {"name": "OldName3"}]
    assert out.truncated is False
    assert session.calls[0].url == f"{BASE}/v1/users/261/username-history"
    assert session.calls[0].params == {"limit": 100, "sortOrder": "Asc"}
    assert session.calls[1].params == {"limit": 100, "sortOrder": "Asc", "cursor": "c1"}


def test_username_history_honours_max_items():
    client, session, _ = make_client(
        [FakeResponse(200, page([{"name": "a"}, {"name": "b"}, {"name": "c"}], "c1"))])
    out = client.users.username_history(261, max_items=2)
    assert out == [{"name": "a"}, {"name": "b"}] and out.truncated is True
    assert len(session.calls) == 1


def test_username_history_empty():
    client, _, _ = make_client(
        routes={f"GET {BASE}/v1/users/261/username-history": page([], None)})
    out = client.users.username_history(261)
    assert out == [] and out.truncated is False


# -- search -------------------------------------------------------------------

def test_search_sends_keyword_and_limit():
    client, session, _ = make_client(
        routes={f"GET {BASE}/v1/users/search": page([SEARCH_261], None)})
    out = client.users.search("shedletsky")
    assert isinstance(out, PagedList) and out == [SEARCH_261]
    assert session.calls[0].url == f"{BASE}/v1/users/search"
    assert session.calls[0].params == {"keyword": "shedletsky", "limit": 100}


def test_search_honours_max_items():
    client, session, _ = make_client(
        [FakeResponse(200, page([SEARCH_261, dict(SEARCH_261, id=262)], "c1"))])
    out = client.users.search("shedletsky", max_items=1)
    assert out == [SEARCH_261] and out.truncated is True
    assert len(session.calls) == 1


# -- authenticated ------------------------------------------------------------

def test_authenticated_returns_object_with_cookie():
    me = {"id": 261, "name": "Shedletsky", "displayName": "Shedletsky"}
    client, session, _ = make_client(
        routes={f"GET {BASE}/v1/users/authenticated": me}, cookie="SECRET")
    assert client.users.authenticated() == me
    assert session.calls[0].url == f"{BASE}/v1/users/authenticated"
    assert session.calls[0].cookies == {".ROBLOSECURITY": "SECRET"}


def test_authenticated_without_cookie_raises_auth_required():
    body = {"errors": [{"code": 9002, "subcode": 0,
                        "message": "Authentication token is missing"}]}
    client, _, _ = make_client([FakeResponse(401, body)])
    with pytest.raises(AuthRequiredError) as exc:
        client.users.authenticated()
    assert exc.value.url == f"{BASE}/v1/users/authenticated"
