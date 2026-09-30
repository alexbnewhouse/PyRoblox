"""Tests for GroupsAPI (groups.roblox.com). No network: every test asserts the
exact URL and params sent to a FakeSession and the typed return value.
Fixture bodies are trimmed copies of real responses recorded in the API probe."""

import pytest
from pydantic import ValidationError

from pyroblox.client import PagedList
from pyroblox.errors import AuthRequiredError, BadRequestError
from pyroblox.groups import GroupsAPI
from pyroblox.models.base import RobloxRecord
from pyroblox.models.groups import (
    Group,
    GroupMember,
    GroupNameHistoryEntry,
    GroupOwner,
    GroupOwnerRef,
    GroupRole,
    GroupSearchResult,
    GroupShout,
    GroupSummary,
    GroupUser,
    SocialLink,
    UserGroupMembership,
)
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

GROUP_5351020 = {
    "id": 5351020, "name": "Republic of Nephistan", "description": "",
    "owner": {"hasVerifiedBadge": False, "userId": 1234983235,
              "username": "DriverNephi_UT", "displayName": "DriverNephi_UT"},
    "shout": None, "memberCount": 97, "isBuildersClubOnly": False,
    "publicEntryAllowed": False, "isLocked": True, "hasVerifiedBadge": False,
    "hasSocialModules": True,
}

SHOUT = {
    "body": "Welcome to the fan club!",
    "poster": {"hasVerifiedBadge": False, "userId": 21557, "username": "Games",
               "displayName": "Games"},
    "created": "2022-09-30T17:18:19.8Z",
    "updated": "2022-09-30T17:18:19.8Z",
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


def _ids(models):
    return [m.id for m in models]


# -- wiring -------------------------------------------------------------------

def test_client_groups_attribute_is_groups_api():
    client, _, _ = make_client(routes={})
    assert isinstance(client.groups, GroupsAPI)
    assert client.groups is client.groups
    assert client.groups.client is client


# -- get_info / get_batch -----------------------------------------------------

def test_get_info_returns_group_model():
    client, session, _ = make_client(routes={f"GET {G}/v1/groups/7": GROUP_7})
    out = client.groups.get_info(7)
    assert isinstance(out, Group)
    assert out.id == 7 and out.name == "Roblox"
    assert out.description == "Official fan club of Roblox!"
    assert isinstance(out.owner, GroupUser)
    assert out.owner.user_id == 21557 and out.owner.username == "Games"
    assert out.shout is None
    assert out.member_count == 13507917
    assert out.is_builders_club_only is False and out.public_entry_allowed is True
    assert out.is_locked is None  # not sent for group 7
    assert out.has_verified_badge is True and out.has_social_modules is True
    assert out.communityTier["currentTier"] == 3  # undeclared field survives
    call = session.calls[0]
    assert call.method == "GET" and call.url == f"{G}/v1/groups/7"
    assert not call.params


def test_get_info_locked_group_exposes_is_locked():
    client, _, _ = make_client(routes={f"GET {G}/v1/groups/5351020": GROUP_5351020})
    out = client.groups.get_info(5351020)
    assert out.is_locked is True and out.member_count == 97


def test_get_batch_joins_ids_and_unwraps_data():
    client, session, _ = make_client(routes={f"GET {G}/v2/groups": {"data": V2_GROUPS}})
    out = client.groups.get_batch([7, 5351020])
    assert isinstance(out, list) and all(isinstance(g, GroupSummary) for g in out)
    assert _ids(out) == [7, 5351020]
    assert out[0].name == "Roblox" and out[0].has_verified_badge is True
    assert isinstance(out[0].owner, GroupOwnerRef)
    assert out[0].owner.id == 21557 and out[0].owner.type == "User"
    assert out[1].created.year == 2019 and out[1].description == ""
    call = session.calls[0]
    assert call.method == "GET" and call.url == f"{G}/v2/groups"
    assert call.params == {"groupIds": "7,5351020"}


def test_get_batch_chunks_150_ids_into_two_calls():
    client, session, _ = make_client(
        [FakeResponse(200, {"data": [{"id": 1, "name": "g1"}]}),
         FakeResponse(200, {"data": [{"id": 101, "name": "g101"}]})])
    out = client.groups.get_batch(range(1, 151))
    assert _ids(out) == [1, 101]
    assert isinstance(out, list)
    assert len(session.calls) == 2
    assert session.calls[0].params["groupIds"] == ",".join(str(i) for i in range(1, 101))
    assert session.calls[1].params["groupIds"] == ",".join(str(i) for i in range(101, 151))


def test_get_batch_no_ids_makes_no_calls():
    client, session, _ = make_client(routes={})
    assert client.groups.get_batch([]) == []
    assert session.calls == []


# -- members / roles ----------------------------------------------------------

def test_get_members_paginates_with_limit_100_asc():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/groups/5351020/users": [page(MEMBERS[:2], "c1"), page(MEMBERS[2:], None)]})
    out = client.groups.get_members(5351020)
    assert isinstance(out, PagedList) and out.truncated is False
    assert all(isinstance(m, GroupMember) for m in out)
    assert [m.user.user_id for m in out] == [1234983235, 64140578, 592340863]
    assert out[0].user.username == "DriverNephi_UT"
    assert out[0].role.id == 35539682 and out[0].role.name == "Supreme DaddyLord"
    assert out[0].role.rank == 255 and out[0].role.member_count is None
    assert out[2].user.display_name == "Quin_TheTigerShark"
    assert session.calls[0].url == f"{G}/v1/groups/5351020/users"
    assert session.calls[0].params == {"limit": 100, "sortOrder": "Asc"}
    assert session.calls[1].params == {"limit": 100, "sortOrder": "Asc", "cursor": "c1"}


def test_get_members_sort_order_and_max_items():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/groups/7/users": page(MEMBERS, "c1")})
    out = client.groups.get_members(7, max_items=2, sort_order="Desc")
    assert [m.user.user_id for m in out] == [1234983235, 64140578]
    assert out.truncated is True
    assert len(session.calls) == 1
    assert session.calls[0].params == {"limit": 100, "sortOrder": "Desc"}


def test_get_roles_unwraps_roles_list():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/groups/5351020/roles": {"groupId": 5351020, "roles": ROLES}})
    out = client.groups.get_roles(5351020)
    assert isinstance(out, list) and all(isinstance(r, GroupRole) for r in out)
    assert _ids(out) == [35539685, 12884901889, 35539684]
    assert out[0].name == "Guest" and out[0].rank == 0 and out[0].member_count == 0
    assert out[0].is_base is None and out[1].is_base is True
    assert out[1].member_count == 97 and out[1].color == 0
    assert session.calls[0].url == f"{G}/v1/groups/5351020/roles"
    assert not session.calls[0].params


def test_get_role_members_paginates_with_limit_100_asc():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/groups/5351020/roles/35539717/users": page(ROLE_MEMBERS, None)})
    out = client.groups.get_role_members(5351020, 35539717)
    assert isinstance(out, PagedList) and len(out) == 1
    assert isinstance(out[0], GroupUser)
    assert out[0].user_id == 1296537893 and out[0].username == "BasedBubb"
    assert out[0].display_name == "BasedBubb" and out[0].has_verified_badge is False
    assert session.calls[0].url == f"{G}/v1/groups/5351020/roles/35539717/users"
    assert session.calls[0].params == {"limit": 100, "sortOrder": "Asc"}


# -- allies / enemies (row pagination) ----------------------------------------

def test_get_allies_walks_start_row_index_across_two_pages():
    first = [_group(i) for i in range(1, 101)]
    second = [_group(101), _group(102)]
    client, session, _ = make_client(
        routes={f"GET {G}/v1/groups/7/relationships/allies": [
            _rows("Allies", first, 102, 100), _rows("Allies", second, 102, 102)]})
    out = client.groups.get_allies(7)
    assert isinstance(out, PagedList) and out.truncated is False
    assert all(isinstance(g, Group) for g in out)
    assert _ids(out) == list(range(1, 103))
    assert out[0].member_count == 10
    assert out[0].owner.user_id == 1001 and out[0].owner.username == "owner1"
    assert len(session.calls) == 2
    assert session.calls[0].url == f"{G}/v1/groups/7/relationships/allies"
    assert session.calls[0].params == {"model.startRowIndex": 0, "model.maxRows": 100}
    assert session.calls[1].params == {"model.startRowIndex": 100, "model.maxRows": 100}


def test_get_allies_empty_group_is_single_call():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/groups/7/relationships/allies": _rows("Allies", [], 0, None)})
    out = client.groups.get_allies(7)
    assert out == [] and out.truncated is False
    assert len(session.calls) == 1


def test_get_allies_max_items_truncates():
    rows = [_group(i) for i in range(1, 4)]
    client, session, _ = make_client(
        routes={f"GET {G}/v1/groups/7/relationships/allies": _rows("Allies", rows, 10, 3)})
    out = client.groups.get_allies(7, max_items=2)
    assert _ids(out) == [1, 2] and out.truncated is True
    assert len(session.calls) == 1


def test_get_enemies_walks_start_row_index_across_two_pages():
    first = [_group(i) for i in range(1, 101)]
    second = [_group(101)]
    client, session, _ = make_client(
        routes={f"GET {G}/v1/groups/7/relationships/enemies": [
            _rows("Enemies", first, 101, 100), _rows("Enemies", second, 101, 101)]})
    out = client.groups.get_enemies(7)
    assert isinstance(out, PagedList) and _ids(out) == list(range(1, 102))
    assert isinstance(out[100], Group) and out[100].name == "Group 101"
    assert len(session.calls) == 2
    assert session.calls[0].url == f"{G}/v1/groups/7/relationships/enemies"
    assert session.calls[0].params == {"model.startRowIndex": 0, "model.maxRows": 100}
    assert session.calls[1].params == {"model.startRowIndex": 100, "model.maxRows": 100}


def test_get_allies_locked_group_raises_bad_request():
    client, _, _ = make_client(
        routes={f"GET {G}/v1/groups/5351020/relationships/allies": LOCKED_400})
    with pytest.raises(BadRequestError) as exc:
        client.groups.get_allies(5351020)
    assert exc.value.roblox_message == "The community is invalid or does not exist."


def test_get_enemies_locked_group_raises_bad_request():
    client, _, _ = make_client(
        routes={f"GET {G}/v1/groups/5351020/relationships/enemies": LOCKED_400})
    with pytest.raises(BadRequestError):
        client.groups.get_enemies(5351020)


# -- social links / name history ----------------------------------------------

def test_get_social_links_sends_cookie_and_unwraps_data():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/groups/7/social-links": {"data": SOCIAL_LINKS}}, cookie="SECRET")
    out = client.groups.get_social_links(7)
    assert isinstance(out, list) and isinstance(out[0], SocialLink)
    assert out[0].id == 1001 and out[0].type == "Discord"
    assert out[0].url == "https://discord.gg/roblox" and out[0].title == "Chat"
    call = session.calls[0]
    assert call.url == f"{G}/v1/groups/7/social-links" and not call.params
    assert call.cookies == {".ROBLOSECURITY": "SECRET"}


def test_get_social_links_without_cookie_raises_auth_required():
    client, _, _ = make_client(routes={f"GET {G}/v1/groups/5351020/social-links": UNAUTH_401})
    with pytest.raises(AuthRequiredError):
        client.groups.get_social_links(5351020)


def test_get_name_history_paginates_with_limit_100_asc():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/groups/7/name-history": page(NAME_HISTORY, None)})
    out = client.groups.get_name_history(7)
    assert isinstance(out, PagedList) and len(out) == 1
    assert isinstance(out[0], GroupNameHistoryEntry)
    assert out[0].name == "Roblox Fan Club" and out[0].created.year == 2009
    assert session.calls[0].url == f"{G}/v1/groups/7/name-history"
    assert session.calls[0].params == {"limit": 100, "sortOrder": "Asc"}


def test_get_name_history_empty():
    client, _, _ = make_client(routes={f"GET {G}/v1/groups/1/name-history": page([], None)})
    assert client.groups.get_name_history(1) == []


# -- user-centric -------------------------------------------------------------

def test_get_user_groups_unwraps_data():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/users/261/groups/roles": {"data": USER_GROUPS}})
    out = client.groups.get_user_groups(261)
    assert isinstance(out, list) and all(isinstance(m, UserGroupMembership) for m in out)
    assert [m.group.id for m in out] == [16945081, 1043971]
    assert isinstance(out[0].group, Group) and out[0].group.member_count == 79
    assert out[0].group.owner.user_id == 763420635
    assert out[0].role.name == "Founding Fathers" and out[0].role.rank == 10
    assert out[0].is_primary_group is None
    assert out[1].is_primary_group is True
    assert out[1].role.name == "Owner" and out[1].role.rank == 255
    assert session.calls[0].url == f"{G}/v1/users/261/groups/roles"
    assert not session.calls[0].params


def test_get_user_primary_group_returns_membership():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/users/261/groups/primary/role": PRIMARY})
    out = client.groups.get_user_primary_group(261)
    assert isinstance(out, UserGroupMembership)
    assert out.group.id == 2814397 and out.group.name == "Shedletsky Studios"
    assert out.group.member_count is None  # primary endpoint omits memberCount
    assert out.group.owner.user_id == 261 and out.group.owner.has_verified_badge is True
    assert out.role.id == 19042935 and out.role.rank == 255
    assert out.is_primary_group is None
    assert session.calls[0].url == f"{G}/v1/users/261/groups/primary/role"


def test_get_user_primary_group_null_body_is_none():
    client, _, _ = make_client(
        routes={f"GET {G}/v1/users/1/groups/primary/role": FakeResponse(200, None)})
    assert client.groups.get_user_primary_group(1) is None


def test_get_user_primary_group_empty_body_is_none():
    client, _, _ = make_client(routes={f"GET {G}/v1/users/1/groups/primary/role": {}})
    assert client.groups.get_user_primary_group(1) is None


# -- search / lookup / permissions --------------------------------------------

def test_search_sends_keyword_and_exact_match_flag():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/groups/search": page(SEARCH, None, keyword="roblox", totalResults=2)})
    out = client.groups.search("roblox")
    assert isinstance(out, PagedList) and _ids(out) == [7, 127081]
    assert all(isinstance(g, GroupSearchResult) for g in out)
    assert out[0].name == "Roblox" and out[0].member_count == 13507917
    assert out[0].previous_name == "" and out[0].public_entry_allowed is True
    assert out[0].created.year == 2009 and out[0].updated.year == 2022
    assert out[0].has_verified_badge is True and out[1].has_verified_badge is False
    assert session.calls[0].url == f"{G}/v1/groups/search"
    assert session.calls[0].params == {"keyword": "roblox", "prioritizeExactMatch": "true",
                                       "limit": 100}


def test_search_can_disable_exact_match_and_cap_items():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/groups/search": page(SEARCH, "c1", keyword="roblox", totalResults=1000)})
    out = client.groups.search("roblox", max_items=1, prioritize_exact_match=False)
    assert _ids(out) == [7] and out.truncated is True
    assert session.calls[0].params["prioritizeExactMatch"] == "false"
    assert len(session.calls) == 1


def test_lookup_sends_group_name_and_unwraps_data():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/groups/search/lookup": {"data": LOOKUP}})
    out = client.groups.lookup("Roblox")
    assert isinstance(out, list) and all(isinstance(g, GroupSearchResult) for g in out)
    assert _ids(out) == [7, 1127093]
    assert out[1].name == "Roblox High School: Fan Club" and out[1].member_count == 7013557
    assert out[0].description is None and out[0].created is None  # lookup is compact
    assert session.calls[0].url == f"{G}/v1/groups/search/lookup"
    assert session.calls[0].params == {"groupName": "Roblox"}


def test_get_guest_permissions_returns_record():
    client, session, _ = make_client(
        routes={f"GET {G}/v1/groups/7/roles/guest/permissions": GUEST_PERMISSIONS})
    out = client.groups.get_guest_permissions(7)
    assert isinstance(out, RobloxRecord)
    assert out.groupId == 7 and out.role["name"] == "Guest"
    assert out.permissions["groupPostsPermissions"]["viewStatus"] is False
    assert out.to_record() == GUEST_PERMISSIONS
    assert session.calls[0].url == f"{G}/v1/groups/7/roles/guest/permissions"
    assert not session.calls[0].params


# -- models -------------------------------------------------------------------

def test_group_user_model_roundtrip():
    raw = dict(GROUP_7["owner"], newFlag=True)
    m = GroupUser.model_validate(raw)
    assert m.user_id == 21557 and m.username == "Games" and m.display_name == "Games"
    assert m.has_verified_badge is False
    assert m.model_extra == {"newFlag": True}
    assert m.to_record() == raw
    assert GroupOwner is GroupUser


def test_group_shout_model_roundtrip():
    raw = dict(SHOUT, pinned=False)
    m = GroupShout.model_validate(raw)
    assert m.body == "Welcome to the fan club!"
    assert isinstance(m.poster, GroupUser) and m.poster.user_id == 21557
    assert m.created.year == 2022 and m.updated.month == 9
    assert m.model_extra == {"pinned": False}
    rec = m.to_record()
    assert rec["poster"]["displayName"] == "Games"
    assert rec["created"].startswith("2022-09-30T17:18:19.8")
    assert rec["pinned"] is False


def test_group_role_model_roundtrip():
    raw = dict(ROLES[1], description="Regular member")
    m = GroupRole.model_validate(raw)
    assert m.id == 12884901889 and m.name == "Member" and m.rank == 1
    assert m.member_count == 97 and m.is_base is True and m.color == 0
    assert m.model_extra == {"description": "Regular member"}
    assert m.to_record() == raw


def test_group_model_roundtrip_with_shout_and_extras():
    raw = dict(GROUP_7, shout=SHOUT)
    m = Group.model_validate(raw)
    assert m.id == 7 and m.member_count == 13507917 and m.public_entry_allowed is True
    assert isinstance(m.shout, GroupShout) and m.shout.poster.username == "Games"
    assert "communityTier" in m.model_extra
    assert m.communityTier["requirements"][0]["satisfied"] is True
    rec = m.to_record()
    assert rec["memberCount"] == 13507917 and rec["hasSocialModules"] is True
    assert rec["owner"] == GROUP_7["owner"]
    assert rec["shout"]["body"] == SHOUT["body"]
    assert rec["communityTier"] == GROUP_7["communityTier"]
    assert "isLocked" not in rec  # declared-but-unsent fields are not emitted


def test_group_summary_model_roundtrip():
    raw = dict(V2_GROUPS[0], memberCount=13507917)
    m = GroupSummary.model_validate(raw)
    assert m.id == 7 and m.name == "Roblox" and m.has_verified_badge is True
    assert isinstance(m.owner, GroupOwnerRef)
    assert m.owner.id == 21557 and m.owner.type == "User"
    assert m.created.year == 2009
    assert m.model_extra == {"memberCount": 13507917}
    rec = m.to_record()
    assert rec["owner"] == {"id": 21557, "type": "User"}
    assert rec["hasVerifiedBadge"] is True and rec["memberCount"] == 13507917
    assert rec["created"].startswith("2009-07-30T05:36:10.417")


def test_group_member_model_roundtrip():
    raw = {"user": dict(MEMBERS[0]["user"]), "role": dict(MEMBERS[0]["role"]),
           "joinedAt": "2024-01-01T00:00:00Z"}
    m = GroupMember.model_validate(raw)
    assert m.user.user_id == 1234983235 and m.role.name == "Supreme DaddyLord"
    assert m.model_extra == {"joinedAt": "2024-01-01T00:00:00Z"}
    rec = m.to_record()
    assert rec["user"]["userId"] == 1234983235 and rec["user"]["displayName"] == "DriverNephi_UT"
    assert "memberCount" not in rec["role"] and rec["role"]["rank"] == 255


def test_social_link_model_roundtrip():
    raw = dict(SOCIAL_LINKS[0], isVerified=True)
    m = SocialLink.model_validate(raw)
    assert m.id == 1001 and m.type == "Discord" and m.title == "Chat"
    assert m.model_extra == {"isVerified": True}
    assert m.to_record() == raw


def test_group_name_history_entry_model_roundtrip():
    raw = dict(NAME_HISTORY[0], changedBy=21557)
    m = GroupNameHistoryEntry.model_validate(raw)
    assert m.name == "Roblox Fan Club" and m.created.year == 2009
    assert m.model_extra == {"changedBy": 21557}
    rec = m.to_record()
    assert rec["name"] == "Roblox Fan Club" and rec["changedBy"] == 21557
    assert rec["created"].startswith("2009-07-30T05:36:10.417")


def test_user_group_membership_model_roundtrip():
    raw = dict(USER_GROUPS[1], isNotificationsEnabled=False)
    m = UserGroupMembership.model_validate(raw)
    assert m.group.id == 1043971 and m.group.owner.username == "Shedletsky"
    assert m.role.rank == 255 and m.is_primary_group is True
    assert m.model_extra == {"isNotificationsEnabled": False}
    rec = m.to_record()
    assert rec["isPrimaryGroup"] is True
    assert rec["group"]["memberCount"] == 2774 and rec["group"]["owner"]["userId"] == 261
    assert rec["role"]["name"] == "Owner"


def test_group_search_result_model_roundtrip():
    raw = dict(SEARCH[1], isPrivate=False)
    m = GroupSearchResult.model_validate(raw)
    assert m.id == 127081 and m.name == "Roblox Wiki" and m.member_count == 3729497
    assert m.previous_name == "" and m.public_entry_allowed is True
    assert m.created.year == 2010 and m.updated.year == 2024
    assert m.has_verified_badge is False
    assert m.model_extra == {"isPrivate": False}
    rec = m.to_record()
    assert rec["memberCount"] == 3729497 and rec["previousName"] == ""
    assert rec["publicEntryAllowed"] is True and rec["isPrivate"] is False
    assert rec["updated"].startswith("2024-06-15T01:39:11.617")


def test_models_accept_snake_case_construction():
    m = GroupRole(id=1, name="Admin", member_count=3)
    assert m.member_count == 3 and m.to_record()["memberCount"] == 3


def test_missing_required_field_raises_validation_error():
    with pytest.raises(ValidationError):
        Group.model_validate({"name": "no id"})
    with pytest.raises(ValidationError):
        GroupUser.model_validate({"username": "no userId"})
    with pytest.raises(ValidationError):
        GroupRole.model_validate({"id": 1})  # name required
    with pytest.raises(ValidationError):
        GroupMember.model_validate({"role": ROLES[0]})  # user required
    with pytest.raises(ValidationError):
        Group.model_validate({"id": "not-an-int", "name": "x"})
