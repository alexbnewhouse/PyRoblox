"""Tests for GroupsAPI (groups.roblox.com). No network: every test asserts the
exact URL and params sent to a FakeSession and the unwrapped return value.
Fixture bodies are trimmed copies of real responses recorded in the API probe."""

import pytest

from robloxwrapper.client import PagedList
from robloxwrapper.errors import AuthRequiredError, BadRequestError
from robloxwrapper.groups import GroupsAPI
from tests.conftest import FakeResponse, make_client, page

G = "https://groups.roblox.com"

GROUP_7 = {
    "id": 7,
    "name": "Roblox",
    "description": "Official fan club of Roblox!",
    "owner": {"hasVerifiedBadge": False, "userId": 21557, "username": "Games",
              "displayName": "Games"},
    "shout": None,
    "memberCount": 13507917,
    "isBuildersClubOnly": False,
    "publicEntryAllowed": True,
    "hasVerifiedBadge": True,
    "hasSocialModules": True,
    "communityTier": {"groupId": 7, "currentTier": 3, "previousTier": None,
                      "tierUpdatedTime": None,
                      "lastEvaluatedTime": "2026-08-19T22:50:20.864Z",
                      "requirements": [{"key": 1, "satisfied": True}]},
}

V2_GROUPS = [
    {"id": 7, "name": "Roblox", "description": "Official fan club of Roblox!",
     "owner": {"id": 21557, "type": "User"}, "created": "2009-07-30T05:36:10.417Z",
     "hasVerifiedBadge": True},
    {"id": 5351020, "name": "Republic of Nephistan", "description": "",
     "owner": {"id": 1234983235, "type": "User"},
     "created": "2019-12-18T04:05:23.83Z", "hasVerifiedBadge": False},
]

MEMBERS = [
    {"user": {"hasVerifiedBadge": False, "userId": 1234983235,
              "username": "DriverNephi_UT", "displayName": "DriverNephi_UT"},
     "role": {"id": 35539682, "name": "Supreme DaddyLord", "rank": 255, "color": 0}},
    {"user": {"hasVerifiedBadge": False, "userId": 64140578,
              "username": "b_ubb333", "displayName": "ellis"},
     "role": {"id": 35539732, "name": "Centurion", "rank": 10, "color": 0}},
    {"user": {"hasVerifiedBadge": False, "userId": 592340863,
              "username": "Quin_LeRequinTigre", "displayName": "Quin_TheTigerShark"},
     "role": {"id": 35539732, "name": "Centurion", "rank": 10, "color": 0}},
]

ROLES = [
    {"id": 35539685, "name": "Guest", "rank": 0, "memberCount": 0, "color": 0},
    {"id": 12884901889, "name": "Member", "rank": 1, "memberCount": 97,
     "isBase": True, "color": 0},
    {"id": 35539684, "name": "Legionnaire", "rank": 1, "memberCount": 74, "color": 0},
]

ROLE_MEMBERS = [
    {"hasVerifiedBadge": False, "userId": 1296537893, "username": "BasedBubb",
     "displayName": "BasedBubb"},
]

SOCIAL_LINKS = [
    {"id": 1001, "type": "Discord", "url": "https://discord.gg/roblox", "title": "Chat"},
]

NAME_HISTORY = [
    {"name": "Roblox Fan Club", "created": "2009-07-30T05:36:10.417Z"},
]

USER_GROUPS = [
    {"group": {"id": 16945081, "name": "Legacy Champions",
               "description": "Legacy Champions stands as a testament ...",
               "owner": {"hasVerifiedBadge": False, "userId": 763420635,
                         "username": "supertornado134", "displayName": "7angelofdrums7"},
               "shout": None, "memberCount": 79, "isBuildersClubOnly": False,
               "publicEntryAllowed": False, "hasVerifiedBadge": False,
               "hasSocialModules": True},
     "role": {"id": 403600039, "name": "Founding Fathers", "rank": 10, "color": 4}},
    {"group": {"id": 1043971, "name": "[ Content Deleted 1043971 ]",
               "description": "[ Content Deleted ]",
               "owner": {"hasVerifiedBadge": True, "userId": 261,
                         "username": "Shedletsky", "displayName": "Shedletsky"},
               "shout": None, "memberCount": 2774, "isBuildersClubOnly": False,
               "publicEntryAllowed": False, "hasVerifiedBadge": False,
               "hasSocialModules": True},
     "role": {"id": 6702990, "name": "Owner", "rank": 255, "color": 0},
     "isPrimaryGroup": True},
]

PRIMARY = {
    "group": {"id": 2814397, "name": "Shedletsky Studios",
              "description": "Join to get updates about my new games in your ROBLOX feed!",
              "owner": {"hasVerifiedBadge": True, "userId": 261,
                        "username": "Shedletsky", "displayName": "Shedletsky"},
              "shout": None, "isBuildersClubOnly": False, "publicEntryAllowed": True,
              "hasVerifiedBadge": False, "hasSocialModules": True},
    "role": {"id": 19042935, "name": "Owner", "rank": 255, "color": 0},
}

SEARCH = [
    {"id": 7, "name": "Roblox", "description": "Official fan club of Roblox!",
     "memberCount": 13507917, "previousName": "", "publicEntryAllowed": True,
     "created": "2009-07-30T05:36:10.417Z", "updated": "2022-09-30T17:18:19.8Z",
     "hasVerifiedBadge": True},
    {"id": 127081, "name": "Roblox Wiki", "description": "[ Content Deleted ]",
     "memberCount": 3729497, "previousName": "", "publicEntryAllowed": True,
     "created": "2010-06-18T20:11:48.747Z", "updated": "2024-06-15T01:39:11.617Z",
     "hasVerifiedBadge": False},
]

LOOKUP = [
    {"id": 7, "name": "Roblox", "memberCount": 13507917, "hasVerifiedBadge": True},
    {"id": 1127093, "name": "Roblox High School: Fan Club", "memberCount": 7013557,
     "hasVerifiedBadge": True},
]

GUEST_PERMISSIONS = {
    "groupId": 7,
    "role": {"id": 260, "name": "Guest", "rank": 0, "color": 0},
    "permissions": {
        "groupPostsPermissions": {"viewStatus": False, "postToStatus": False},
        "groupMembershipPermissions": {"changeRank": False, "inviteMembers": False,
                                       "removeMembers": False, "banMembers": False},
    },
}

LOCKED_400 = FakeResponse(400, {"errors": [{
    "code": 1, "message": "Group is invalid or does not exist.",
    "userFacingMessage": "The community is invalid or does not exist."}]})

UNAUTH_401 = FakeResponse(401, {"errors": [{
    "code": 9002, "subcode": 0, "message": "Authentication token is missing"}]})


def _group(i):
    """A full group object as found in relatedGroups."""
    return {"id": i, "name": f"Group {i}", "description": "",
            "owner": {"hasVerifiedBadge": False, "userId": 1000 + i,
                      "username": f"owner{i}", "displayName": f"owner{i}"},
            "shout": None, "memberCount": 10 * i, "isBuildersClubOnly": False,
            "publicEntryAllowed": True, "hasVerifiedBadge": False}


def _rows(kind, rows, total, next_index):
    """A relationships page body in the model.startRowIndex style."""
    return {"groupId": 7, "relationshipType": kind, "totalGroupCount": total,
            "relatedGroups": rows, "nextRowIndex": next_index}


# -- wiring -------------------------------------------------------------------

def test_client_groups_attribute_is_groups_api():
    client, _, _ = make_client(routes={})
    assert isinstance(client.groups, GroupsAPI)
    assert client.groups is client.groups
    assert client.groups.client is client


# -- get / batch_get ----------------------------------------------------------

def test_get_returns_group_object():
    client, session, _ = make_client(routes={f"GET {G}/v1/groups/7": GROUP_7})
    assert client.groups.get(7) == GROUP_7
    call = session.calls[0]
    assert call.method == "GET" and call.url == f"{G}/v1/groups/7"
    assert not call.params


def test_batch_get_joins_ids_and_unwraps_data():
    client, session, _ = make_client(routes={f"GET {G}/v2/groups": {"data": V2_GROUPS}})
    assert client.groups.batch_get([7, 5351020]) == V2_GROUPS
    call = session.calls[0]
    assert call.method == "GET" and call.url == f"{G}/v2/groups"
    assert call.params == {"groupIds": "7,5351020"}


def test_batch_get_chunks_150_ids_into_two_calls():
    client, session, _ = make_client(
        [FakeResponse(200, {"data": [{"id": 1}]}), FakeResponse(200, {"data": [{"id": 101}]})])
    out = client.groups.batch_get(range(1, 151))
    assert out == [{"id": 1}, {"id": 101}]
    assert isinstance(out, list)
    assert len(session.calls) == 2
    assert session.calls[0].params["groupIds"] == ",".join(str(i) for i in range(1, 101))
    assert session.calls[1].params["groupIds"] == ",".join(str(i) for i in range(101, 151))


def test_batch_get_no_ids_makes_no_calls():
    client, session, _ = make_client(routes={})
    assert client.groups.batch_get([]) == []
    assert session.calls == []


# -- members / roles ----------------------------------------------------------

def test_members_paginates_with_limit_100_asc():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/groups/5351020/users": [page(MEMBERS[:2], "c1"), page(MEMBERS[2:], None)]})
    out = client.groups.members(5351020)
    assert isinstance(out, PagedList) and out.truncated is False
    assert out == MEMBERS
    assert session.calls[0].url == f"{G}/v1/groups/5351020/users"
    assert session.calls[0].params == {"limit": 100, "sortOrder": "Asc"}
    assert session.calls[1].params == {"limit": 100, "sortOrder": "Asc", "cursor": "c1"}


def test_members_sort_order_and_max_items():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/groups/7/users": page(MEMBERS, "c1")})
    out = client.groups.members(7, max_items=2, sort_order="Desc")
    assert out == MEMBERS[:2] and out.truncated is True
    assert len(session.calls) == 1
    assert session.calls[0].params == {"limit": 100, "sortOrder": "Desc"}


def test_roles_unwraps_roles_list():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/groups/5351020/roles": {"groupId": 5351020, "roles": ROLES}})
    assert client.groups.roles(5351020) == ROLES
    assert session.calls[0].url == f"{G}/v1/groups/5351020/roles"
    assert not session.calls[0].params


def test_role_members_paginates_with_limit_100_asc():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/groups/5351020/roles/35539717/users": page(ROLE_MEMBERS, None)})
    out = client.groups.role_members(5351020, 35539717)
    assert isinstance(out, PagedList) and out == ROLE_MEMBERS
    assert session.calls[0].url == f"{G}/v1/groups/5351020/roles/35539717/users"
    assert session.calls[0].params == {"limit": 100, "sortOrder": "Asc"}


# -- allies / enemies (row pagination) ----------------------------------------

def test_allies_walks_start_row_index_across_two_pages():
    first = [_group(i) for i in range(1, 101)]
    second = [_group(101), _group(102)]
    client, session, _ = make_client(
        routes={f"GET {G}/v1/groups/7/relationships/allies": [
            _rows("Allies", first, 102, 100), _rows("Allies", second, 102, 102)]})
    out = client.groups.allies(7)
    assert isinstance(out, PagedList) and out.truncated is False
    assert out == first + second
    assert out[0]["memberCount"] == 10
    assert len(session.calls) == 2
    assert session.calls[0].url == f"{G}/v1/groups/7/relationships/allies"
    assert session.calls[0].params == {"model.startRowIndex": 0, "model.maxRows": 100}
    assert session.calls[1].params == {"model.startRowIndex": 100, "model.maxRows": 100}


def test_allies_empty_group_is_single_call():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/groups/7/relationships/allies": _rows("Allies", [], 0, None)})
    out = client.groups.allies(7)
    assert out == [] and out.truncated is False
    assert len(session.calls) == 1


def test_allies_max_items_truncates():
    rows = [_group(i) for i in range(1, 4)]
    client, session, _ = make_client(
        routes={f"GET {G}/v1/groups/7/relationships/allies": _rows("Allies", rows, 10, 3)})
    out = client.groups.allies(7, max_items=2)
    assert out == rows[:2] and out.truncated is True
    assert len(session.calls) == 1


def test_enemies_walks_start_row_index_across_two_pages():
    first = [_group(i) for i in range(1, 101)]
    second = [_group(101)]
    client, session, _ = make_client(
        routes={f"GET {G}/v1/groups/7/relationships/enemies": [
            _rows("Enemies", first, 101, 100), _rows("Enemies", second, 101, 101)]})
    out = client.groups.enemies(7)
    assert isinstance(out, PagedList) and out == first + second
    assert len(session.calls) == 2
    assert session.calls[0].url == f"{G}/v1/groups/7/relationships/enemies"
    assert session.calls[0].params == {"model.startRowIndex": 0, "model.maxRows": 100}
    assert session.calls[1].params == {"model.startRowIndex": 100, "model.maxRows": 100}


def test_allies_locked_group_raises_bad_request():
    client, _, _ = make_client(
        routes={f"GET {G}/v1/groups/5351020/relationships/allies": LOCKED_400})
    with pytest.raises(BadRequestError) as exc:
        client.groups.allies(5351020)
    assert exc.value.roblox_message == "The community is invalid or does not exist."


def test_enemies_locked_group_raises_bad_request():
    client, _, _ = make_client(
        routes={f"GET {G}/v1/groups/5351020/relationships/enemies": LOCKED_400})
    with pytest.raises(BadRequestError):
        client.groups.enemies(5351020)


# -- social links / name history ----------------------------------------------

def test_social_links_sends_cookie_and_unwraps_data():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/groups/7/social-links": {"data": SOCIAL_LINKS}}, cookie="SECRET")
    assert client.groups.social_links(7) == SOCIAL_LINKS
    call = session.calls[0]
    assert call.url == f"{G}/v1/groups/7/social-links" and not call.params
    assert call.cookies == {".ROBLOSECURITY": "SECRET"}


def test_social_links_without_cookie_raises_auth_required():
    client, _, _ = make_client(routes={f"GET {G}/v1/groups/5351020/social-links": UNAUTH_401})
    with pytest.raises(AuthRequiredError):
        client.groups.social_links(5351020)


def test_name_history_paginates_with_limit_100_asc():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/groups/7/name-history": page(NAME_HISTORY, None)})
    out = client.groups.name_history(7)
    assert isinstance(out, PagedList) and out == NAME_HISTORY
    assert session.calls[0].url == f"{G}/v1/groups/7/name-history"
    assert session.calls[0].params == {"limit": 100, "sortOrder": "Asc"}


def test_name_history_empty():
    client, _, _ = make_client(routes={f"GET {G}/v1/groups/1/name-history": page([], None)})
    assert client.groups.name_history(1) == []


# -- user-centric -------------------------------------------------------------

def test_user_groups_unwraps_data():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/users/261/groups/roles": {"data": USER_GROUPS}})
    out = client.groups.user_groups(261)
    assert out == USER_GROUPS
    assert out[1]["isPrimaryGroup"] is True
    assert session.calls[0].url == f"{G}/v1/users/261/groups/roles"
    assert not session.calls[0].params


def test_user_primary_group_returns_object():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/users/261/groups/primary/role": PRIMARY})
    assert client.groups.user_primary_group(261) == PRIMARY
    assert session.calls[0].url == f"{G}/v1/users/261/groups/primary/role"


def test_user_primary_group_null_body_is_none():
    client, _, _ = make_client(
        routes={f"GET {G}/v1/users/1/groups/primary/role": FakeResponse(200, None)})
    assert client.groups.user_primary_group(1) is None


def test_user_primary_group_empty_body_is_none():
    client, _, _ = make_client(routes={f"GET {G}/v1/users/1/groups/primary/role": {}})
    assert client.groups.user_primary_group(1) is None


# -- search / lookup / permissions --------------------------------------------

def test_search_sends_keyword_and_exact_match_flag():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/groups/search": page(SEARCH, None, keyword="roblox", totalResults=2)})
    out = client.groups.search("roblox")
    assert isinstance(out, PagedList) and out == SEARCH
    assert session.calls[0].url == f"{G}/v1/groups/search"
    assert session.calls[0].params == {"keyword": "roblox", "prioritizeExactMatch": "true",
                                       "limit": 100}


def test_search_can_disable_exact_match_and_cap_items():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/groups/search": page(SEARCH, "c1", keyword="roblox", totalResults=1000)})
    out = client.groups.search("roblox", max_items=1, prioritize_exact_match=False)
    assert out == SEARCH[:1] and out.truncated is True
    assert session.calls[0].params["prioritizeExactMatch"] == "false"
    assert len(session.calls) == 1


def test_lookup_sends_group_name_and_unwraps_data():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/groups/search/lookup": {"data": LOOKUP}})
    assert client.groups.lookup("Roblox") == LOOKUP
    assert session.calls[0].url == f"{G}/v1/groups/search/lookup"
    assert session.calls[0].params == {"groupName": "Roblox"}


def test_guest_permissions_returns_object():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/groups/7/roles/guest/permissions": GUEST_PERMISSIONS})
    assert client.groups.guest_permissions(7) == GUEST_PERMISSIONS
    assert session.calls[0].url == f"{G}/v1/groups/7/roles/guest/permissions"
    assert not session.calls[0].params
