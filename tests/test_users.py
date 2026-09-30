"""Tests for :mod:`pyroblox.users`. No network: every test uses the
FakeSession from conftest and asserts the exact request that would be sent."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from pyroblox.client import PagedList
from pyroblox.errors import AuthRequiredError, NotFoundError
from pyroblox.models.users import User, UsernameHistoryEntry, UsernameMatch
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


def ids(models):
    return [m.id for m in models]


def roundtrip(models, raws):
    """to_record() also emits declared-but-absent fields as None; compare only
    the keys Roblox actually sent."""
    recs = [m.to_record() for m in models]
    assert len(recs) == len(raws)
    return [{k: v for k, v in rec.items() if k in raw} for rec, raw in zip(recs, raws)]


# -- get_info -----------------------------------------------------------------

def test_get_info_returns_user_model():
    client, session, _ = make_client(routes={f"GET {BASE}/v1/users/261": USER_261})
    out = client.users.get_info(261)
    assert isinstance(out, User)
    assert out.id == 261 and out.name == "Shedletsky" and out.display_name == "Shedletsky"
    assert out.is_banned is False and out.has_verified_badge is True
    assert out.external_app_display_name is None
    assert out.created == datetime(2006, 6, 22, 1, 33, 56, 450000, tzinfo=timezone.utc)
    call = session.calls[0]
    assert call.method == "GET"
    assert call.url == f"{BASE}/v1/users/261"
    assert not call.params


def test_get_info_unknown_id_raises_not_found():
    body = {"errors": [{"code": 3, "message": "The user id is invalid."}]}
    client, _, _ = make_client([FakeResponse(404, body)])
    with pytest.raises(NotFoundError) as exc:
        client.users.get_info(726527401)
    assert exc.value.url == f"{BASE}/v1/users/726527401"


# -- get_batch ----------------------------------------------------------------

def test_get_batch_posts_ids_and_unwraps_data():
    client, session, _ = make_client(
        routes={f"POST {BASE}/v1/users": {"data": [BATCH_1, BATCH_261]}})
    out = client.users.get_batch([1, 261])
    assert all(isinstance(u, User) for u in out)
    assert ids(out) == [1, 261]
    assert out[0].name == "Roblox" and out[1].display_name == "Shedletsky"
    assert roundtrip(out, [BATCH_1, BATCH_261]) == [BATCH_1, BATCH_261]
    call = session.calls[0]
    assert call.method == "POST"
    assert call.url == f"{BASE}/v1/users"
    assert call.json == {"userIds": [1, 261], "excludeBannedUsers": False}


def test_get_batch_exclude_banned_flag():
    client, session, _ = make_client(routes={f"POST {BASE}/v1/users": {"data": []}})
    assert client.users.get_batch([1], exclude_banned=True) == []
    assert session.calls[0].json == {"userIds": [1], "excludeBannedUsers": True}


def test_get_batch_chunks_150_ids_into_two_posts():
    user_ids = list(range(1, 151))
    first = [{"id": i, "name": f"u{i}", "displayName": f"u{i}", "hasVerifiedBadge": False}
             for i in user_ids[:100]]
    second = [{"id": i, "name": f"u{i}", "displayName": f"u{i}", "hasVerifiedBadge": False}
              for i in user_ids[100:]]
    client, session, _ = make_client(
        [FakeResponse(200, {"data": first}), FakeResponse(200, {"data": second})])
    out = client.users.get_batch(iter(user_ids))  # any iterable, not just a list
    assert isinstance(out, list) and ids(out) == user_ids
    assert roundtrip(out, first + second) == first + second
    assert len(session.calls) == 2
    assert session.calls[0].json == {"userIds": user_ids[:100], "excludeBannedUsers": False}
    assert session.calls[1].json == {"userIds": user_ids[100:], "excludeBannedUsers": False}


def test_get_batch_empty_input_sends_nothing():
    client, session, _ = make_client(routes={})
    assert client.users.get_batch([]) == []
    assert session.calls == []


# -- get_by_usernames / resolve -----------------------------------------------

def test_get_by_usernames_posts_names_and_unwraps_data():
    client, session, _ = make_client(
        routes={f"POST {BASE}/v1/usernames/users": {"data": [BY_NAME_1, BY_NAME_261]}})
    out = client.users.get_by_usernames(["Roblox", "Shedletsky"])
    assert all(isinstance(u, UsernameMatch) for u in out)
    assert ids(out) == [1, 261]
    assert [u.requested_username for u in out] == ["Roblox", "Shedletsky"]
    assert roundtrip(out, [BY_NAME_1, BY_NAME_261]) == [BY_NAME_1, BY_NAME_261]
    call = session.calls[0]
    assert call.method == "POST"
    assert call.url == f"{BASE}/v1/usernames/users"
    assert call.json == {"usernames": ["Roblox", "Shedletsky"], "excludeBannedUsers": False}


def test_get_by_usernames_exclude_banned_flag():
    client, session, _ = make_client(
        routes={f"POST {BASE}/v1/usernames/users": {"data": []}})
    client.users.get_by_usernames(["Roblox"], exclude_banned=True)
    assert session.calls[0].json == {"usernames": ["Roblox"], "excludeBannedUsers": True}


def test_get_by_usernames_chunks_150_names_into_two_posts():
    names = [f"user{i}" for i in range(150)]
    first = [{"requestedUsername": n, "id": i, "name": n, "displayName": n,
              "hasVerifiedBadge": False} for i, n in enumerate(names[:100])]
    second = [{"requestedUsername": n, "id": 100 + i, "name": n, "displayName": n,
               "hasVerifiedBadge": False} for i, n in enumerate(names[100:])]
    client, session, _ = make_client(
        [FakeResponse(200, {"data": first}), FakeResponse(200, {"data": second})])
    out = client.users.get_by_usernames(names)
    assert [u.requested_username for u in out] == names
    assert roundtrip(out, first + second) == first + second
    assert len(session.calls) == 2
    assert session.calls[0].json["usernames"] == names[:100]
    assert session.calls[1].json["usernames"] == names[100:]


def test_resolve_returns_single_match():
    client, session, _ = make_client(
        routes={f"POST {BASE}/v1/usernames/users": {"data": [BY_NAME_261]}})
    out = client.users.resolve("Shedletsky")
    assert isinstance(out, UsernameMatch)
    assert out.id == 261 and out.requested_username == "Shedletsky"
    assert roundtrip([out], [BY_NAME_261]) == [BY_NAME_261]
    assert session.calls[0].url == f"{BASE}/v1/usernames/users"
    assert session.calls[0].json == {"usernames": ["Shedletsky"],
                                    "excludeBannedUsers": False}


def test_resolve_unknown_username_raises_not_found():
    client, _, _ = make_client(routes={f"POST {BASE}/v1/usernames/users": {"data": []}})
    with pytest.raises(NotFoundError) as exc:
        client.users.resolve("nobody_here_xyz")
    assert "username 'nobody_here_xyz' not found" in str(exc.value)
    assert exc.value.url == f"{BASE}/v1/usernames/users"


# -- get_username_history -----------------------------------------------------

def test_get_username_history_paginates_with_limit_100_asc():
    client, session, _ = make_client([
        FakeResponse(200, page([{"name": "OldName1"}, {"name": "OldName2"}], "c1")),
        FakeResponse(200, page([{"name": "OldName3"}], None)),
    ])
    out = client.users.get_username_history(261)
    assert isinstance(out, PagedList)
    assert all(isinstance(e, UsernameHistoryEntry) for e in out)
    assert [e.name for e in out] == ["OldName1", "OldName2", "OldName3"]
    assert out.truncated is False
    assert session.calls[0].url == f"{BASE}/v1/users/261/username-history"
    assert session.calls[0].params == {"limit": 100, "sortOrder": "Asc"}
    assert session.calls[1].params == {"limit": 100, "sortOrder": "Asc", "cursor": "c1"}


def test_get_username_history_honours_max_items():
    client, session, _ = make_client(
        [FakeResponse(200, page([{"name": "a"}, {"name": "b"}, {"name": "c"}], "c1"))])
    out = client.users.get_username_history(261, max_items=2)
    assert [e.name for e in out] == ["a", "b"] and out.truncated is True
    assert len(session.calls) == 1


def test_get_username_history_empty():
    client, _, _ = make_client(
        routes={f"GET {BASE}/v1/users/261/username-history": page([], None)})
    out = client.users.get_username_history(261)
    assert out == [] and out.truncated is False


# -- search -------------------------------------------------------------------

def test_search_sends_keyword_and_limit():
    client, session, _ = make_client(
        routes={f"GET {BASE}/v1/users/search": page([SEARCH_261], None)})
    out = client.users.search("shedletsky")
    assert isinstance(out, PagedList) and len(out) == 1
    assert isinstance(out[0], User)
    assert out[0].id == 261 and out[0].previous_usernames == []
    assert roundtrip([out[0]], [SEARCH_261]) == [SEARCH_261]
    assert session.calls[0].url == f"{BASE}/v1/users/search"
    assert session.calls[0].params == {"keyword": "shedletsky", "limit": 100}


def test_search_honours_max_items():
    client, session, _ = make_client(
        [FakeResponse(200, page([SEARCH_261, dict(SEARCH_261, id=262)], "c1"))])
    out = client.users.search("shedletsky", max_items=1)
    assert ids(out) == [261] and out.truncated is True
    assert len(session.calls) == 1


# -- get_authenticated --------------------------------------------------------

def test_get_authenticated_returns_user_with_cookie():
    me = {"id": 261, "name": "Shedletsky", "displayName": "Shedletsky"}
    client, session, _ = make_client(
        routes={f"GET {BASE}/v1/users/authenticated": me}, cookie="SECRET")
    out = client.users.get_authenticated()
    assert isinstance(out, User)
    assert out.id == 261 and out.name == "Shedletsky" and out.display_name == "Shedletsky"
    assert out.has_verified_badge is False  # not sent by this endpoint -> default
    assert session.calls[0].url == f"{BASE}/v1/users/authenticated"
    assert session.calls[0].cookies == {".ROBLOSECURITY": "SECRET"}


def test_get_authenticated_without_cookie_raises_auth_required():
    body = {"errors": [{"code": 9002, "subcode": 0,
                        "message": "Authentication token is missing"}]}
    client, _, _ = make_client([FakeResponse(401, body)])
    with pytest.raises(AuthRequiredError) as exc:
        client.users.get_authenticated()
    assert exc.value.url == f"{BASE}/v1/users/authenticated"


# -- old names are gone -------------------------------------------------------

def test_old_method_names_are_not_kept():
    client, _, _ = make_client(routes={})
    for old in ("get", "batch_get", "by_usernames", "username_history", "authenticated"):
        assert not hasattr(client.users, old), old


# -- models -------------------------------------------------------------------

def test_user_model_validates_probe_payload():
    raw = dict(USER_261, someNewField={"nested": 1})
    user = User.model_validate(raw)
    # snake_case access to camelCase keys
    assert user.display_name == "Shedletsky"
    assert user.is_banned is False
    assert user.has_verified_badge is True
    assert user.external_app_display_name is None
    assert user.description.startswith('"He came like the wind')
    assert user.created == datetime(2006, 6, 22, 1, 33, 56, 450000, tzinfo=timezone.utc)
    assert user.previous_usernames is None
    # undeclared fields survive
    assert user.model_extra == {"someNewField": {"nested": 1}}
    assert user.someNewField == {"nested": 1}
    # to_record gives back Roblox's camelCase keys
    rec = user.to_record()
    assert set(rec) == set(raw)   # only keys Roblox sent come back
    assert rec["displayName"] == "Shedletsky"
    assert rec["isBanned"] is False
    assert rec["hasVerifiedBadge"] is True
    assert rec["externalAppDisplayName"] is None
    assert rec["created"] == "2006-06-22T01:33:56.450000Z"
    assert rec["someNewField"] == {"nested": 1}
    assert "display_name" not in rec and "is_banned" not in rec


def test_user_model_defaults_for_minimal_payload():
    user = User.model_validate(BATCH_1)
    assert user.has_verified_badge is True
    assert user.description is None and user.created is None and user.is_banned is None
    assert User.model_validate({"id": 5, "name": "x"}).has_verified_badge is False


def test_username_match_model_validates_probe_payload():
    raw = dict(BY_NAME_261, extraFlag=True)
    match = UsernameMatch.model_validate(raw)
    assert isinstance(match, User)  # subclass of User
    assert match.requested_username == "Shedletsky"
    assert match.id == 261 and match.display_name == "Shedletsky"
    assert match.model_extra == {"extraFlag": True}
    rec = match.to_record()
    assert rec["requestedUsername"] == "Shedletsky"
    assert rec["extraFlag"] is True
    assert "requested_username" not in rec
    assert {k: v for k, v in rec.items() if k in raw} == raw


def test_username_history_entry_model():
    entry = UsernameHistoryEntry.model_validate({"name": "OldName", "changedAt": "x"})
    assert entry.name == "OldName"
    assert entry.model_extra == {"changedAt": "x"}
    assert entry.to_record() == {"name": "OldName", "changedAt": "x"}


def test_user_missing_required_field_raises_validation_error():
    with pytest.raises(ValidationError):
        User.model_validate({"name": "no id", "displayName": "x"})
    with pytest.raises(ValidationError):
        User.model_validate({"id": 261, "displayName": "no name"})
    with pytest.raises(ValidationError):
        UsernameHistoryEntry.model_validate({})
