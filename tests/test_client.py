"""Tests for the core RobloxClient retry and error handling."""

import httpx
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
    httpx_mock.add_response(status_code=401, json={"errors": [{"message": "Unauthorized"}]})
    client = RobloxClient()
    with pytest.raises(AuthenticationError):
        client.get("groups", "/v1/groups/1")
    client.close()


def test_not_found(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=404, json={"errors": [{"message": "Not found"}]})
    client = RobloxClient()
    with pytest.raises(NotFoundError):
        client.get("groups", "/v1/groups/1")
    client.close()


def test_other_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=400, json={"errors": [{"message": "Bad request"}]})
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
