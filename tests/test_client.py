"""Tests for the HTTP core: throttle, retries, error mapping, cookie scoping,
CSRF handling, and the two pagination styles."""

import pytest

from pyroblox.client import PagedList, RobloxClient, chunked, endpoint_key
from pyroblox.errors import (
    AuthenticationError, AuthRequiredError, BadRequestError, NotFoundError, PrivateError,
    PyRobloxError, RateLimitError, RateLimitedError, RobloxAPIError, RobloxError, ServerError,
)
from tests.conftest import FakeResponse, make_client, page


# -- basics -------------------------------------------------------------------

def test_get_returns_json_and_sets_headers():
    client, session, _ = make_client([FakeResponse(200, {"id": 1})])
    assert client.get("https://users.roblox.com/v1/users/1") == {"id": 1}
    call = session.calls[0]
    assert call.method == "GET" and call.cookies == {}
    assert call.headers["User-Agent"].startswith("PyRoblox/")
    assert call.headers["Accept"] == "application/json"


def test_post_sends_json_body():
    client, session, _ = make_client([FakeResponse(200, {"done": 1})])
    out = client.post("https://presence.roblox.com/v1/presence/users", {"userIds": [261]})
    assert out == {"done": 1}
    call = session.calls[0]
    assert call.method == "POST" and call.json == {"userIds": [261]}


def test_download_returns_bytes_without_accept_json():
    client, session, _ = make_client([FakeResponse(200, content=b"\x89PNG...")])
    assert client.download("https://tr.rbxcdn.com/img.png") == b"\x89PNG..."
    assert "Accept" not in session.calls[0].headers


# -- cookie handling ----------------------------------------------------------

def test_cookie_attached_to_roblox_hosts_only():
    client, session, _ = make_client(
        [FakeResponse(200, {}), FakeResponse(200, content=b"png")], cookie="SECRET")
    client.get("https://users.roblox.com/v1/users/1")
    client.download("https://t0.rbxcdn.com/img.png")
    assert session.calls[0].cookies == {".ROBLOSECURITY": "SECRET"}
    assert session.calls[1].cookies == {}
    assert client.has_cookie and not client.cookie_rejected


def test_empty_cookie_means_no_cookie():
    client, session, _ = make_client([FakeResponse(200, {})], cookie="")
    client.get("https://users.roblox.com/v1/users/1")
    assert session.calls[0].cookies == {}
    assert not client.has_cookie


def test_401_with_cookie_falls_back_unauthenticated():
    client, session, _ = make_client(
        [FakeResponse(401), FakeResponse(200, {"ok": True}), FakeResponse(200, {"ok": True})],
        cookie="SECRET")
    assert client.get("https://users.roblox.com/v1/users/1") == {"ok": True}
    assert session.calls[0].cookies == {".ROBLOSECURITY": "SECRET"}
    assert session.calls[1].cookies == {}
    client.get("https://users.roblox.com/v1/users/2")
    assert session.calls[2].cookies == {}
    assert client.cookie_rejected and not client.has_cookie


def test_401_without_cookie_raises_auth_required():
    client, _, _ = make_client([FakeResponse(401, {"errors": [{"message": "Authorization has been denied for this request."}]})])
    with pytest.raises(AuthRequiredError) as exc:
        client.get("https://groups.roblox.com/v1/groups/7/social-links")
    assert exc.value.status == 401
    assert "Authorization has been denied" in str(exc.value)


def test_csrf_dance_also_happens_without_cookie():
    client, session, _ = make_client(
        [FakeResponse(403, headers={"x-csrf-token": "TOK"}), FakeResponse(200, {"data": []})])
    assert client.post("https://catalog.roblox.com/v1/catalog/items/details", {"items": []}) == {"data": []}
    assert session.calls[1].headers["X-CSRF-TOKEN"] == "TOK"
    assert session.calls[1].cookies == {}


def test_csrf_token_learned_and_resent_on_authenticated_post():
    client, session, _ = make_client(
        [FakeResponse(403, headers={"x-csrf-token": "TOK"}), FakeResponse(200, {"ok": 1}),
         FakeResponse(200, {"ok": 2})],
        cookie="SECRET")
    assert client.post("https://presence.roblox.com/v1/presence/users", {"userIds": [1]}) == {"ok": 1}
    assert "X-CSRF-TOKEN" not in session.calls[0].headers
    assert session.calls[1].headers["X-CSRF-TOKEN"] == "TOK"
    client.post("https://presence.roblox.com/v1/presence/users", {"userIds": [2]})
    assert session.calls[2].headers["X-CSRF-TOKEN"] == "TOK"


def test_csrf_403_only_retried_once():
    client, _, _ = make_client(
        [FakeResponse(403, headers={"x-csrf-token": "TOK"}),
         FakeResponse(403, headers={"x-csrf-token": "TOK"})],
        cookie="SECRET")
    with pytest.raises(PrivateError):
        client.post("https://presence.roblox.com/v1/presence/users", {"userIds": [1]})


# -- error mapping ------------------------------------------------------------

def test_404_raises_not_found():
    client, _, _ = make_client([FakeResponse(404)])
    with pytest.raises(NotFoundError) as exc:
        client.get("https://users.roblox.com/v1/users/1")
    assert exc.value.status == 404
    assert exc.value.url == "https://users.roblox.com/v1/users/1"


def test_403_raises_private():
    client, _, _ = make_client([FakeResponse(403)])
    with pytest.raises(PrivateError):
        client.get("https://inventory.roblox.com/v2/users/1/inventory/2")


def test_400_raises_bad_request_with_roblox_message():
    body = {"errors": [{"code": 3, "message": "The user is invalid."}]}
    client, _, _ = make_client([FakeResponse(400, body)])
    with pytest.raises(BadRequestError) as exc:
        client.get("https://users.roblox.com/v1/users/5")
    assert exc.value.roblox_message == "The user is invalid."
    assert "The user is invalid." in str(exc.value)


def test_400_with_bare_string_body_keeps_the_message():
    client, _, _ = make_client([FakeResponse(400, "Ascending sort order is not supported.")])
    with pytest.raises(BadRequestError) as exc:
        client.get("https://games.roblox.com/v2/users/1/favorite/games")
    assert exc.value.roblox_message == "Ascending sort order is not supported."


def test_error_carries_roblox_errors_list_and_march_aliases():
    body = {"errors": [{"code": 3, "message": "The user is invalid."}]}
    client, _, _ = make_client([FakeResponse(400, body)])
    with pytest.raises(RobloxAPIError) as exc:      # alias of RobloxError
        client.get("https://users.roblox.com/v1/users/5")
    assert exc.value.errors == body["errors"] and exc.value.status_code == 400
    assert PyRobloxError is RobloxError and RateLimitError is RateLimitedError
    client, _, _ = make_client([FakeResponse(403)])
    with pytest.raises(AuthenticationError):
        client.get("https://x.roblox.com/y")
    client, _, _ = make_client([FakeResponse(401)])
    with pytest.raises(AuthenticationError):
        client.get("https://x.roblox.com/y")


def test_jitter_spreads_backoff_but_not_server_directed_waits():
    client, _, fake = make_client([FakeResponse(429), FakeResponse(200, {})],
                                  jitter=True, rng=lambda: 0.0)
    client.get("https://games.roblox.com/v1/games")
    assert fake.sleeps == [0.5]                     # 1.0 * (0.5 + 0.0 * 0.5)
    client, _, fake = make_client([FakeResponse(429, headers={"Retry-After": "7"}), FakeResponse(200, {})],
                                  jitter=True, rng=lambda: 0.0)
    client.get("https://games.roblox.com/v1/games")
    assert fake.sleeps == [7.0]                     # Roblox said 7; no jitter applied


def test_context_manager_closes_only_owned_session():
    closed = []
    class S:
        def close(self): closed.append(True)
    with RobloxClient(session=S()) as c:
        pass
    assert closed == []                              # injected session is left alone
    c = RobloxClient(); c._session = S(); c._owns_session = True
    c.close(); assert closed == [True]


def test_fetch_all_and_fetch_rows_validate_into_model():
    from pyroblox.models.base import RobloxModel
    class M(RobloxModel):
        id: int
    client, _, _ = make_client([FakeResponse(200, page([{"id": 1, "x": 2}], None))])
    out = client.fetch_all("https://x.roblox.com/v1/list", model=M)
    assert out[0].id == 1 and out[0].x == 2 and out.truncated is False
    client, _, _ = make_client([FakeResponse(200, {"relatedGroups": [{"id": 9}], "totalGroupCount": 1, "nextRowIndex": 1})])
    assert client.fetch_rows("https://g/x", model=M)[0].id == 9
    client, _, _ = make_client([FakeResponse(200, page([{"id": 3}], None))])
    assert [m.id for m in client.paginate("https://x.roblox.com/v1/list", model=M)] == [3]


def test_other_4xx_raises_roblox_error():
    client, _, _ = make_client([FakeResponse(418)])
    with pytest.raises(RobloxError):
        client.get("https://economy.roblox.com/v1/assets/1/resale-data")


def test_unparseable_error_body_is_tolerated():
    client, _, _ = make_client([FakeResponse(400, ValueError("no json"))])
    with pytest.raises(BadRequestError) as exc:
        client.get("https://users.roblox.com/v1/users/5")
    assert exc.value.roblox_message is None


# -- retries ------------------------------------------------------------------

def test_429_backs_off_then_succeeds():
    client, session, fake = make_client(
        [FakeResponse(429), FakeResponse(429), FakeResponse(200, {"ok": 1})])
    assert client.get("https://games.roblox.com/v1/games") == {"ok": 1}
    assert len(session.calls) == 3
    assert fake.sleeps == [1.0, 2.0]


def test_429_honors_retry_after_capped():
    client, _, fake = make_client(
        [FakeResponse(429, headers={"Retry-After": "7"}),
         FakeResponse(429, headers={"Retry-After": "9999"}),
         FakeResponse(200, {})])
    client.get("https://games.roblox.com/v1/games")
    assert fake.sleeps == [7.0, 120.0]


def test_429_uses_ratelimit_reset_when_longer_than_retry_after():
    client, _, fake = make_client(
        [FakeResponse(429, headers={"Retry-After": "5", "x-ratelimit-reset": "47"}),
         FakeResponse(200, {})])
    client.get("https://users.roblox.com/v1/users/261/username-history")
    assert fake.sleeps == [47.0]


def test_bad_retry_after_falls_back_to_backoff():
    client, _, fake = make_client(
        [FakeResponse(429, headers={"Retry-After": "soon"}), FakeResponse(200, {})])
    client.get("https://games.roblox.com/v1/games")
    assert fake.sleeps == [1.0]


def test_429_exhausted_raises_rate_limited():
    client, _, _ = make_client([FakeResponse(429)] * 3, max_retries=2)
    with pytest.raises(RateLimitedError):
        client.get("https://games.roblox.com/v1/games")


def test_5xx_exhausted_raises_server_error():
    client, _, _ = make_client([FakeResponse(503)] * 3, max_retries=2)
    with pytest.raises(ServerError) as exc:
        client.get("https://games.roblox.com/v1/games")
    assert exc.value.status == 503


def test_download_retries_transient_errors():
    client, _, fake = make_client([FakeResponse(429), FakeResponse(200, content=b"x")])
    assert client.download("https://tr.rbxcdn.com/img.png") == b"x"
    assert fake.sleeps == [1.0]


# -- throttle -----------------------------------------------------------------

def test_throttle_sleeps_after_burst_per_host():
    client, _, fake = make_client([FakeResponse(200, {})] * 4, rate=1.0, burst=2)
    for _ in range(3):
        client.get("https://users.roblox.com/v1/users/1")
    assert len(fake.sleeps) == 1 and fake.sleeps[0] == pytest.approx(1.0)
    client.get("https://groups.roblox.com/v1/groups/1")
    assert len(fake.sleeps) == 1


def test_throttle_refills_over_time():
    client, _, fake = make_client([FakeResponse(200, {})] * 3, rate=2.0, burst=1)
    client.get("https://users.roblox.com/v1/users/1")
    fake.now += 10
    client.get("https://users.roblox.com/v1/users/1")
    assert fake.sleeps == []
    client.get("https://users.roblox.com/v1/users/1")
    assert fake.sleeps == [pytest.approx(0.5)]


# -- adaptive quota from Roblox headers ---------------------------------------

def test_endpoint_key_normalises_ids_and_drops_query():
    assert endpoint_key("https://users.roblox.com/v1/users/261?x=1") == "users.roblox.com/v1/users/{id}"
    assert endpoint_key("https://groups.roblox.com/v1/groups/7/roles/12/users") == \
        "groups.roblox.com/v1/groups/{id}/roles/{id}/users"
    assert endpoint_key("https://games.roblox.com/v1/games") == "games.roblox.com/v1/games"


def test_exhausted_quota_header_delays_next_call_to_same_endpoint_only():
    exhausted = {"x-ratelimit-limit": "1, 1;w=60", "x-ratelimit-remaining": "0",
                 "x-ratelimit-reset": "40"}
    client, session, fake = make_client(
        [FakeResponse(200, {"data": []}, headers=exhausted),
         FakeResponse(200, {"id": 1}),
         FakeResponse(200, {"data": []})])
    client.get("https://users.roblox.com/v1/users/261/username-history")
    client.get("https://users.roblox.com/v1/users/261")          # different endpoint: no wait
    assert fake.sleeps == []
    client.get("https://users.roblox.com/v1/users/5/username-history")  # same endpoint key
    assert fake.sleeps == [pytest.approx(40.5)]
    assert len(session.calls) == 3


def test_quota_wait_is_skipped_once_window_has_passed():
    exhausted = {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "10"}
    client, _, fake = make_client(
        [FakeResponse(200, {}, headers=exhausted), FakeResponse(200, {})])
    client.get("https://users.roblox.com/v1/users/search")
    fake.now += 30
    client.get("https://users.roblox.com/v1/users/search")
    assert fake.sleeps == []


def test_remaining_quota_does_not_delay():
    ok = {"x-ratelimit-remaining": "29", "x-ratelimit-reset": "57"}
    client, _, fake = make_client([FakeResponse(200, {}, headers=ok), FakeResponse(200, {})])
    client.get("https://users.roblox.com/v1/users/1")
    client.get("https://users.roblox.com/v1/users/2")
    assert fake.sleeps == []


# -- cursor pagination --------------------------------------------------------

def test_paginate_follows_cursor_until_done():
    client, session, _ = make_client(
        [FakeResponse(200, page([1, 2], "c1")), FakeResponse(200, page([3], None))])
    assert list(client.paginate("https://x.roblox.com/v1/list")) == [1, 2, 3]
    assert session.calls[0].params == {"limit": 100}
    assert session.calls[1].params == {"limit": 100, "cursor": "c1"}


def test_paginate_passes_limit_sort_and_extra_params():
    client, session, _ = make_client([FakeResponse(200, page([], None))])
    list(client.paginate("https://x.roblox.com/v1/list", {"a": 1}, limit=10, sort_order="Desc"))
    assert session.calls[0].params == {"a": 1, "limit": 10, "sortOrder": "Desc"}


def test_paginate_stops_at_max_items_without_fetching_more():
    client, session, _ = make_client([FakeResponse(200, page([1, 2, 3], "c1"))])
    assert list(client.paginate("https://x.roblox.com/v1/list", max_items=2)) == [1, 2]
    assert len(session.calls) == 1


def test_paginate_tolerates_null_data():
    client, _, _ = make_client([FakeResponse(200, {"data": None, "nextPageCursor": None})])
    assert list(client.paginate("https://x.roblox.com/v1/list")) == []


def test_repeating_cursor_stops_instead_of_looping_forever():
    client, session, _ = make_client(
        [FakeResponse(200, page([1], "same")), FakeResponse(200, page([2], "same")),
         FakeResponse(200, page([3], "same"))])
    items = client.fetch_all("https://x.roblox.com/v1/list")
    assert items == [1, 2] and items.truncated is True
    assert len(session.calls) == 2
    client, session, _ = make_client(
        [FakeResponse(200, page([1], "same")), FakeResponse(200, page([2], "same"))])
    assert list(client.paginate("https://x.roblox.com/v1/list")) == [1, 2]
    assert len(session.calls) == 2


def test_fetch_all_reports_truncation_by_pages():
    client, _, _ = make_client(
        [FakeResponse(200, page([1], "c1")), FakeResponse(200, page([2], "c2")),
         FakeResponse(200, page([3], "c3"))])
    items = client.fetch_all("https://x.roblox.com/v1/list", max_pages=3)
    assert isinstance(items, PagedList)
    assert items == [1, 2, 3] and items.truncated is True


def test_fetch_all_reports_truncation_by_items():
    client, session, _ = make_client([FakeResponse(200, page([1, 2, 3], "c1"))])
    items = client.fetch_all("https://x.roblox.com/v1/list", max_items=2)
    assert items == [1, 2] and items.truncated is True
    assert len(session.calls) == 1


def test_fetch_all_complete_is_not_truncated():
    client, _, _ = make_client(
        [FakeResponse(200, page([1, 2], "c1")), FakeResponse(200, page([3], None))])
    items = client.fetch_all("https://x.roblox.com/v1/list")
    assert items == [1, 2, 3] and items.truncated is False


def test_fetch_all_exact_max_items_with_no_more_pages_is_not_truncated():
    client, _, _ = make_client([FakeResponse(200, page([1, 2], None))])
    items = client.fetch_all("https://x.roblox.com/v1/list", max_items=2)
    assert items == [1, 2] and items.truncated is False


# -- row pagination (allies / enemies) ----------------------------------------

def _rows(rows, start, total):
    return FakeResponse(200, {"groupId": 7, "relationshipType": "Allies",
                              "totalGroupCount": total, "relatedGroups": rows,
                              "nextRowIndex": start + len(rows)})


def test_fetch_rows_walks_start_row_index():
    client, session, _ = make_client(
        [_rows([{"id": 1}, {"id": 2}], 0, 3), _rows([{"id": 3}], 2, 3)])
    items = client.fetch_rows(
        "https://groups.roblox.com/v1/groups/7/relationships/allies", page_size=2)
    assert [i["id"] for i in items] == [1, 2, 3] and items.truncated is False
    assert session.calls[0].params == {"model.startRowIndex": 0, "model.maxRows": 2}
    assert session.calls[1].params == {"model.startRowIndex": 2, "model.maxRows": 2}


def test_fetch_rows_single_page():
    client, session, _ = make_client([_rows([{"id": 1}], 0, 1)])
    items = client.fetch_rows("https://g/x")
    assert items == [{"id": 1}] and items.truncated is False
    assert len(session.calls) == 1


def test_fetch_rows_empty():
    client, _, _ = make_client([_rows([], 0, 0)])
    items = client.fetch_rows("https://g/x")
    assert items == [] and items.truncated is False


def test_fetch_rows_max_items_truncates():
    client, session, _ = make_client([_rows([{"id": 1}, {"id": 2}, {"id": 3}], 0, 10)])
    items = client.fetch_rows("https://g/x", max_items=2)
    assert [i["id"] for i in items] == [1, 2] and items.truncated is True
    assert len(session.calls) == 1


def test_fetch_rows_does_not_loop_when_server_omits_next_index():
    client, session, _ = make_client([
        FakeResponse(200, {"relatedGroups": [{"id": 1}, {"id": 2}]}),
        FakeResponse(200, {"relatedGroups": []}),
    ])
    items = client.fetch_rows("https://g/x", page_size=2)
    assert [i["id"] for i in items] == [1, 2] and items.truncated is False
    assert session.calls[1].params["model.startRowIndex"] == 2


# -- helpers ------------------------------------------------------------------

def test_paged_list_behaves_like_list():
    pl = PagedList([1, 2], truncated=True)
    assert pl == [1, 2] and len(pl) == 2 and pl.truncated
    assert PagedList().truncated is False


def test_chunked():
    assert list(chunked([1, 2, 3, 4, 5], 2)) == [[1, 2], [3, 4], [5]]
    assert list(chunked([], 3)) == []


def test_domain_apis_are_cached_attributes():
    client = RobloxClient(session=object())
    for name in ("users", "friends", "groups", "games", "badges", "avatar",
                 "inventory", "account", "presence", "thumbnails", "catalog"):
        api = getattr(client, name)
        assert getattr(client, name) is api
        assert api.client is client
    assert client.assets is client.catalog
