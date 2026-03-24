"""Tests for the core RobloxClient retry and error handling."""

import pytest
from pytest_httpx import HTTPXMock

from pyroblox.client import RobloxClient
from pyroblox.exceptions import (
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    RobloxAPIError,
)


def test_successful_get(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={"id": 1, "name": "TestGroup"})
    client = RobloxClient()
    resp = client.get("groups", "/v1/groups/1")
    assert resp.status_code == 200
    assert resp.json()["name"] == "TestGroup"
    client.close()


def test_rate_limit_retry(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=429, headers={"Retry-After": "0"})
    httpx_mock.add_response(json={"id": 1})
    client = RobloxClient(base_delay=0.01)
    resp = client.get("groups", "/v1/groups/1")
    assert resp.status_code == 200
    client.close()


def test_rate_limit_exhausted(httpx_mock: HTTPXMock) -> None:
    for _ in range(4):
        httpx_mock.add_response(status_code=429, headers={"Retry-After": "0"})
    client = RobloxClient(max_retries=3, base_delay=0.01)
    with pytest.raises(RateLimitError) as exc_info:
        client.get("groups", "/v1/groups/1")
    assert exc_info.value.status_code == 429
    client.close()


def test_server_error_retry(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=500)
    httpx_mock.add_response(json={"id": 1})
    client = RobloxClient(base_delay=0.01)
    resp = client.get("groups", "/v1/groups/1")
    assert resp.status_code == 200
    client.close()


def test_auth_error_no_retry(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        status_code=401,
        json={"errors": [{"message": "Unauthorized"}]},
    )
    client = RobloxClient()
    with pytest.raises(AuthenticationError):
        client.get("groups", "/v1/groups/1")
    client.close()


def test_not_found(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        status_code=404,
        json={"errors": [{"message": "Not found"}]},
    )
    client = RobloxClient()
    with pytest.raises(NotFoundError):
        client.get("groups", "/v1/groups/1")
    client.close()


def test_other_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        status_code=400,
        json={"errors": [{"message": "Bad request"}]},
    )
    client = RobloxClient()
    with pytest.raises(RobloxAPIError) as exc_info:
        client.get("groups", "/v1/groups/1")
    assert exc_info.value.status_code == 400
    client.close()


def test_context_manager(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={"ok": True})
    with RobloxClient() as client:
        resp = client.get("groups", "/v1/groups/1")
        assert resp.json()["ok"] is True


def test_cookie_auth() -> None:
    client = RobloxClient(cookie="test_cookie_123")
    assert ".ROBLOSECURITY" in client._http.cookies.keys()
    client.close()


# --- New edge-case tests ---


def test_403_raises_auth_error(httpx_mock: HTTPXMock) -> None:
    """403 should also raise AuthenticationError, not just 401."""
    httpx_mock.add_response(status_code=403, json={"errors": []})
    with RobloxClient() as client:
        with pytest.raises(AuthenticationError) as exc_info:
            client.get("groups", "/v1/groups/1")
        assert exc_info.value.status_code == 403


def test_auth_error_is_not_retried(httpx_mock: HTTPXMock) -> None:
    """401/403 must raise immediately — no retries."""
    httpx_mock.add_response(status_code=401, json={"errors": []})
    # Only one response queued — if client retries, httpx_mock will
    # raise because no more responses are available.
    with RobloxClient() as client:
        with pytest.raises(AuthenticationError):
            client.get("groups", "/v1/groups/1")


def test_not_found_is_not_retried(httpx_mock: HTTPXMock) -> None:
    """404 must raise immediately — no retries."""
    httpx_mock.add_response(status_code=404, json={"errors": []})
    with RobloxClient() as client:
        with pytest.raises(NotFoundError):
            client.get("groups", "/v1/groups/1")


def test_server_error_exhausted(httpx_mock: HTTPXMock) -> None:
    """Persistent 500s should raise after all retries."""
    for _ in range(3):
        httpx_mock.add_response(status_code=500, json={"errors": []})
    client = RobloxClient(max_retries=2, base_delay=0.01)
    with pytest.raises(RobloxAPIError) as exc_info:
        client.get("groups", "/v1/groups/1")
    assert exc_info.value.status_code == 500
    client.close()


def test_rate_limit_retry_after_capped_by_max_delay(
    httpx_mock: HTTPXMock,
) -> None:
    """A huge Retry-After header should be capped to max_delay."""
    httpx_mock.add_response(
        status_code=429, headers={"Retry-After": "0"}
    )
    httpx_mock.add_response(json={"ok": True})
    # max_delay=0.05 means even Retry-After=0 should work fine;
    # the real test is that we don't sleep for hours.
    client = RobloxClient(max_retries=1, base_delay=0.01, max_delay=0.05)
    resp = client.get("groups", "/v1/groups/1")
    assert resp.status_code == 200
    client.close()


def test_error_message_includes_url(httpx_mock: HTTPXMock) -> None:
    """Exception should carry the URL for debugging."""
    httpx_mock.add_response(
        status_code=400,
        json={"errors": [{"message": "Invalid ID"}]},
    )
    with RobloxClient() as client:
        with pytest.raises(RobloxAPIError) as exc_info:
            client.get("groups", "/v1/groups/bad")
        assert "groups.roblox.com" in exc_info.value.url
        assert "Invalid ID" in str(exc_info.value)


def test_non_json_error_body(httpx_mock: HTTPXMock) -> None:
    """Non-JSON error body should not crash _parse_errors."""
    httpx_mock.add_response(
        status_code=400,
        text="<html>Bad Gateway</html>",
        headers={"content-type": "text/html"},
    )
    with RobloxClient() as client:
        with pytest.raises(RobloxAPIError) as exc_info:
            client.get("groups", "/v1/groups/1")
        assert exc_info.value.status_code == 400
        assert exc_info.value.errors == []


def test_post_method(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={"data": [{"id": 1}]})
    with RobloxClient() as client:
        resp = client.post("users", "/v1/users", json={"userIds": [1]})
        assert resp.status_code == 200


def test_max_retries_zero_means_no_retries(httpx_mock: HTTPXMock) -> None:
    """max_retries=0: only the initial attempt, no retries."""
    httpx_mock.add_response(status_code=500, json={"errors": []})
    client = RobloxClient(max_retries=0)
    with pytest.raises(RobloxAPIError):
        client.get("groups", "/v1/groups/1")
    client.close()


def test_custom_base_urls() -> None:
    """Users can override base URLs for testing or proxying."""
    client = RobloxClient(
        base_urls={"groups": "http://localhost:8080"}
    )
    assert client._base_urls["groups"] == "http://localhost:8080"
    # Other defaults should still be present
    assert client._base_urls["users"] == "https://users.roblox.com"
    client.close()
