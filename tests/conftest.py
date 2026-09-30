"""Shared test fixtures. No test in this directory touches the network.

``FakeSession`` replaces ``requests.Session``. Two styles are supported:

* ordered: ``FakeSession([resp1, resp2])`` hands responses back in order.
* routed:  ``FakeSession(routes={"GET https://users.roblox.com/v1/users/1": {...}})``
  matches on ``"METHOD url"`` (query string stripped) and returns 200 with that
  JSON body. A route value may also be a ``FakeResponse`` or a list of responses
  to return in turn.
"""

from __future__ import annotations

import json as _json
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, urlsplit

import pytest
from requests.structures import CaseInsensitiveDict

from pyroblox.client import RobloxClient


class FakeResponse:
    def __init__(self, status_code: int, payload: Any = None,
                 headers: Optional[dict] = None, content: bytes = b""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.headers = CaseInsensitiveDict(headers or {})
        self.content = content
        self.ok = status_code < 400

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class Call:
    def __init__(self, method, url, params, json, cookies, headers):
        self.method = method
        self.url = url
        self.params = params
        self.json = json
        self.cookies = cookies
        self.headers = headers

    # keep tuple-style unpacking working for ported tests
    def __iter__(self):
        return iter((self.method, self.url, self.params, self.json, self.cookies))

    def __getitem__(self, i):
        return (self.method, self.url, self.params, self.json, self.cookies)[i]

    @property
    def full_url(self) -> str:
        if self.params:
            return f"{self.url}?{urlencode(self.params, doseq=True)}"
        return self.url


class FakeSession:
    """Returns canned responses; records every request made."""

    def __init__(self, responses: Optional[List[FakeResponse]] = None, *,
                 routes: Optional[Dict[str, Any]] = None):
        self._responses = list(responses or [])
        self._routes = dict(routes or {})
        self.calls: List[Call] = []

    def add_route(self, method: str, url: str, payload: Any, status: int = 200):
        self._routes[f"{method} {url}"] = FakeResponse(status, payload)

    def request(self, method, url, params=None, json=None, cookies=None,
                headers=None, timeout=None):
        self.calls.append(Call(method, url, params, json, dict(cookies or {}),
                               dict(headers or {})))
        if self._responses:
            return self._responses.pop(0)
        key = f"{method} {url}"
        if key not in self._routes:
            # allow routes keyed with a query string to match exact params
            full = f"{method} {url}?{urlencode(params or {}, doseq=True)}"
            if full in self._routes:
                key = full
        if key in self._routes:
            value = self._routes[key]
            if isinstance(value, list):
                value = value.pop(0) if len(value) > 1 else value[0]
            if isinstance(value, FakeResponse):
                return value
            return FakeResponse(200, value)
        raise AssertionError(f"unexpected request: {method} {url} params={params}")

    @property
    def urls(self) -> List[str]:
        return [c.url for c in self.calls]


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps: List[float] = []

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def make_client(responses=None, cookie=None, *, routes=None, **kw):
    """Build a client wired to a FakeSession and FakeClock.

    Returns ``(client, session, clock)``.
    """
    fake = FakeClock()
    session = FakeSession(responses, routes=routes)
    kw.setdefault("burst", 10_000)  # tests should not sleep unless they test the throttle
    kw.setdefault("jitter", False)  # deterministic backoff in tests
    client = RobloxClient(cookie, session=session, clock=fake.clock,
                          sleep=fake.sleep, **kw)
    return client, session, fake


def page(items, cursor=None, **extra):
    """A Roblox-style paginated page body."""
    body = {"previousPageCursor": None, "nextPageCursor": cursor, "data": items}
    body.update(extra)
    return body


@pytest.fixture
def fake_client():
    """A ``(client, session, clock)`` triple with an empty routed FakeSession."""
    return make_client(routes={})
