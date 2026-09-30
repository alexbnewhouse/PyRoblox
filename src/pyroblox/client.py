"""Low-level HTTP client for Roblox's public web APIs.

:class:`RobloxClient` is the one object you create. It owns the HTTP session,
the optional ``.ROBLOSECURITY`` cookie, a per-host rate limiter, retry logic,
and pagination helpers. The domain APIs hang off it as attributes::

    from pyroblox import RobloxClient

    client = RobloxClient()                 # public data only
    client = RobloxClient(cookie="...")     # also unlocks cookie-only endpoints

    client.users.get_info(261)
    client.groups.get_members(7)
    client.games.get_info(13058)

All methods return typed models (see :mod:`pyroblox.models`) that keep every
field Roblox sends, so nothing is lost when Roblox adds one.

Design notes
------------
* Rate limiting is a token bucket per hostname (``rate`` requests/second with a
  ``burst`` allowance). Roblox's limits differ per subdomain, so buckets are
  per host.
* 429 and 5xx responses are retried with exponential backoff, honouring
  ``Retry-After``. After ``max_retries`` the typed error is raised.
* The cookie is only ever sent to ``roblox.com`` hosts, never to the
  ``rbxcdn.com`` image CDN. If Roblox rejects the cookie (401) the client logs a
  warning once, drops the cookie, and continues unauthenticated.
* Authenticated POSTs need an ``X-CSRF-TOKEN``. The client learns it from the
  first 403 and resends once.
"""

from __future__ import annotations

import logging
import random
import re
import threading
import time
from functools import cached_property
from typing import (Any, Callable, Dict, Generic, Iterable, Iterator, List, Optional,
                    Tuple, Type, TypeVar)
from urllib.parse import urlsplit

import requests

from .errors import (
    AuthRequiredError,
    BadRequestError,
    NotFoundError,
    PrivateError,
    RateLimitedError,
    RobloxError,
    ServerError,
)

log = logging.getLogger("pyroblox")

MAX_RETRY_AFTER = 120.0
DEFAULT_USER_AGENT = "PyRoblox/2.0 (+https://github.com/CTEC-MIIS/PyRoblox)"
DEFAULT_PAGE_SIZE = 100

T = TypeVar("T")


class PagedList(list, Generic[T]):
    """A list of records plus a ``truncated`` flag.

    ``truncated`` is True when a ``max_items`` / ``max_pages`` cap stopped
    pagination while Roblox still had more to give.
    """

    def __init__(self, items: Iterable[T] = (), truncated: bool = False):
        super().__init__(items)
        self.truncated = truncated


def _roblox_errors(resp: Any) -> List[dict]:
    """Roblox's ``errors`` array from an error body, or an empty list."""
    try:
        body = resp.json()
    except Exception:  # noqa: BLE001
        return []
    if isinstance(body, dict) and isinstance(body.get("errors"), list):
        return [e for e in body["errors"] if isinstance(e, dict)]
    return []


def _is_roblox_host(host: str) -> bool:
    return host == "roblox.com" or host.endswith(".roblox.com")


def _roblox_message(resp: Any) -> Optional[str]:
    """Extract Roblox's human-readable error message from a response, if any."""
    try:
        body = resp.json()
    except Exception:  # noqa: BLE001 - any parse failure means "no message"
        return None
    if isinstance(body, str) and body.strip():
        # Some endpoints answer 400 with a bare JSON string, e.g.
        # "Ascending sort order is not supported for user's favorite games."
        return body.strip()
    if isinstance(body, dict):
        errors = body.get("errors")
        if isinstance(errors, list) and errors:
            first = errors[0]
            if isinstance(first, dict):
                msg = first.get("userFacingMessage") or first.get("message")
                if msg:
                    return str(msg)
        if body.get("message"):
            return str(body["message"])
    return None


_DIGITS_SEGMENT = re.compile(r"^\d+$")


def endpoint_key(url: str) -> str:
    """Normalise a URL to ``host/path`` with numeric segments replaced by ``{id}``.

    Roblox rate limits are per endpoint, so ``users.roblox.com/v1/users/261`` and
    ``users.roblox.com/v1/users/1`` share a bucket while ``.../users/261/friends``
    does not.
    """
    parts = urlsplit(url)
    segments = [("{id}" if _DIGITS_SEGMENT.match(seg) else seg)
                for seg in parts.path.split("/") if seg]
    return parts.netloc + "/" + "/".join(segments)


def _header_float(resp: Any, name: str) -> Optional[float]:
    value = resp.headers.get(name)
    if value is None:
        return None
    try:
        return float(str(value).split(",")[0].strip())
    except ValueError:
        return None


class HostThrottle:
    """Token bucket per hostname: ``burst`` capacity, refilled at ``rate``/sec."""

    def __init__(self, rate: float, burst: float,
                 clock: Callable[[], float], sleep: Callable[[float], None]):
        self._rate = rate
        self._burst = burst
        self._clock = clock
        self._sleep = sleep
        self._buckets: Dict[str, Tuple[float, float]] = {}
        self._lock = threading.Lock()

    def acquire(self, host: str) -> None:
        with self._lock:
            now = self._clock()
            tokens, stamp = self._buckets.get(host, (self._burst, now))
            tokens = min(self._burst, tokens + (now - stamp) * self._rate)
            if tokens < 1.0:
                wait = (1.0 - tokens) / self._rate
                self._sleep(wait)
                now += wait
                tokens = 1.0
            self._buckets[host] = (tokens - 1.0, now)


class RobloxClient:
    """Synchronous, read-only client for Roblox's public web APIs."""

    def __init__(self, cookie: Optional[str] = None, *, rate: float = 1.0,
                 burst: float = 5, max_retries: int = 4, timeout: float = 30,
                 jitter: bool = True, session: Any = None,
                 clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep,
                 rng: Callable[[], float] = random.random,
                 user_agent: str = DEFAULT_USER_AGENT):
        self._cookie = cookie or None
        self._auth_failed = False
        self._csrf_token: Optional[str] = None
        self._max_retries = max_retries
        self._timeout = timeout
        self._jitter = jitter
        self._rng = rng
        self._owns_session = session is None
        self._session = session or requests.Session()
        self._sleep = sleep
        self._clock = clock
        self._user_agent = user_agent
        self._throttle = HostThrottle(rate, burst, clock, sleep)
        # endpoint key -> monotonic time before which Roblox's own headers say
        # the per-endpoint quota is exhausted
        self._not_before: Dict[str, float] = {}

    # -- lifecycle ------------------------------------------------------------

    def __enter__(self) -> "RobloxClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP session (only if this client created it)."""
        if self._owns_session and hasattr(self._session, "close"):
            self._session.close()

    # -- state ----------------------------------------------------------------

    @property
    def has_cookie(self) -> bool:
        """True when a cookie was supplied and Roblox has not rejected it."""
        return bool(self._cookie) and not self._auth_failed

    @property
    def cookie_rejected(self) -> bool:
        """True when a cookie was supplied but Roblox answered 401 to it."""
        return bool(self._cookie) and self._auth_failed

    # -- core -----------------------------------------------------------------

    def get(self, url: str, params: Optional[dict] = None) -> Any:
        """GET ``url`` and return the parsed JSON body."""
        return self.request("GET", url, params=params)

    def post(self, url: str, json: Optional[dict] = None,
             params: Optional[dict] = None) -> Any:
        """POST ``json`` to ``url`` and return the parsed JSON body."""
        return self.request("POST", url, params=params, json=json)

    def download(self, url: str) -> bytes:
        """Binary GET (thumbnail CDN URLs) with the same throttle and retries."""
        return self.request("GET", url, binary=True)

    def request(self, method: str, url: str, *, params: Optional[dict] = None,
                json: Optional[dict] = None, binary: bool = False) -> Any:
        host = urlsplit(url).netloc
        key = endpoint_key(url)
        backoff = 1.0
        csrf_retried = False
        for attempt in range(self._max_retries + 1):
            self._wait_for_quota(key)
            self._throttle.acquire(host)
            cookies: Dict[str, str] = {}
            if self._cookie and not self._auth_failed and _is_roblox_host(host):
                cookies[".ROBLOSECURITY"] = self._cookie
            headers = {"User-Agent": self._user_agent}
            if not binary:
                headers["Accept"] = "application/json"
            if method != "GET" and self._csrf_token:
                headers["X-CSRF-TOKEN"] = self._csrf_token

            resp = self._session.request(method, url, params=params, json=json,
                                         cookies=cookies, headers=headers,
                                         timeout=self._timeout)
            status = resp.status_code
            self._learn_quota(key, resp)

            if status == 401 and cookies:
                self._auth_failed = True
                log.warning("Roblox rejected the .ROBLOSECURITY cookie (expired or "
                            "rotated?). Continuing without it; cookie-only endpoints "
                            "will fail until you supply a fresh cookie.")
                return self.request(method, url, params=params, json=json, binary=binary)

            if (status == 403 and method != "GET" and not csrf_retried
                    and resp.headers.get("x-csrf-token")):
                # Roblox answers the first POST with 403 + a CSRF token, even
                # unauthenticated. Store it and resend once.
                self._csrf_token = resp.headers["x-csrf-token"]
                csrf_retried = True
                continue

            if status == 404:
                raise NotFoundError("Not found", status=404, url=url,
                                    roblox_message=_roblox_message(resp),
                    errors=_roblox_errors(resp))
            if status == 403:
                raise PrivateError("Forbidden (private or hidden)", status=403, url=url,
                                   roblox_message=_roblox_message(resp),
                    errors=_roblox_errors(resp))
            if status == 401:
                raise AuthRequiredError("Login cookie required", status=401, url=url,
                                        roblox_message=_roblox_message(resp),
                    errors=_roblox_errors(resp))
            if status == 400:
                raise BadRequestError("Bad request", status=400, url=url,
                                      roblox_message=_roblox_message(resp),
                    errors=_roblox_errors(resp))
            if status == 429 or status >= 500:
                if attempt == self._max_retries:
                    if status == 429:
                        raise RateLimitedError("Rate limited by Roblox after retries",
                                               status=429, url=url)
                    raise ServerError(f"Roblox server error {status} after retries",
                                      status=status, url=url)
                wait = self._retry_wait(resp, backoff)
                if self._jitter and not resp.headers.get("Retry-After") \
                        and _header_float(resp, "x-ratelimit-reset") is None:
                    wait *= 0.5 + self._rng() * 0.5   # spread out retries from many clients
                log.debug("%s %s -> %s; sleeping %.1fs (attempt %d)",
                          method, url, status, wait, attempt + 1)
                self._sleep(wait)
                backoff *= 2
                continue
            if not resp.ok:
                raise RobloxError(f"Unexpected HTTP {status}", status=status, url=url,
                                  roblox_message=_roblox_message(resp),
                                  errors=_roblox_errors(resp))
            return resp.content if binary else resp.json()
        raise RobloxError(f"retries exhausted: {url}", url=url)  # pragma: no cover

    # -- rate-limit bookkeeping -----------------------------------------------

    def _wait_for_quota(self, key: str) -> None:
        """Sleep until Roblox's advertised per-endpoint quota window has reset."""
        until = self._not_before.get(key)
        if until is None:
            return
        now = self._clock()
        if now < until:
            wait = until - now
            log.info("Roblox quota for %s exhausted; waiting %.0fs for the window to reset",
                     key, wait)
            self._sleep(wait)
        self._not_before.pop(key, None)

    def _learn_quota(self, key: str, resp: Any) -> None:
        """Record when the per-endpoint quota resets if this response used the last call."""
        remaining = _header_float(resp, "x-ratelimit-remaining")
        reset = _header_float(resp, "x-ratelimit-reset")
        if remaining is None or reset is None:
            return
        if remaining <= 0 and reset > 0:
            self._not_before[key] = self._clock() + min(reset, MAX_RETRY_AFTER) + 0.5

    @staticmethod
    def _retry_wait(resp: Any, backoff: float) -> float:
        """How long to sleep after a 429/5xx: the longer of Retry-After and the
        advertised reset, capped, else exponential backoff."""
        candidates = [v for v in (_header_float(resp, "Retry-After"),
                                  _header_float(resp, "x-ratelimit-reset")) if v is not None]
        if candidates:
            return min(max(candidates), MAX_RETRY_AFTER)
        return backoff

    # -- pagination -----------------------------------------------------------

    def paginate(self, url: str, params: Optional[dict] = None, *,
                 limit: int = DEFAULT_PAGE_SIZE, max_pages: Optional[int] = None,
                 max_items: Optional[int] = None, sort_order: Optional[str] = None,
                 model: Optional[Type[Any]] = None) -> Iterator[Any]:
        """Yield items across Roblox ``nextPageCursor`` pagination, lazily.

        Stops early when ``max_pages`` or ``max_items`` is reached. With
        ``model`` each item is validated into that model class.
        """
        base = dict(params or {})
        base["limit"] = limit
        if sort_order:
            base["sortOrder"] = sort_order
        cursor: Optional[str] = None
        seen: set = set()
        pages = 0
        yielded = 0
        while True:
            page_params = dict(base)
            if cursor:
                page_params["cursor"] = cursor
            data = self.get(url, page_params)
            for item in data.get("data") or []:
                yield model.model_validate(item) if model is not None else item
                yielded += 1
                if max_items is not None and yielded >= max_items:
                    return
            cursor = data.get("nextPageCursor")
            pages += 1
            if not cursor or (max_pages is not None and pages >= max_pages):
                return
            if cursor in seen:
                log.warning("Roblox returned a repeating page cursor for %s; stopping", url)
                return
            seen.add(cursor)

    def fetch_all(self, url: str, params: Optional[dict] = None, *,
                  limit: int = DEFAULT_PAGE_SIZE, max_pages: Optional[int] = None,
                  max_items: Optional[int] = None, sort_order: Optional[str] = None,
                  model: Optional[Type[Any]] = None) -> PagedList:
        """Like :meth:`paginate` but eager: returns a :class:`PagedList`.

        Its ``truncated`` flag is True when a cap stopped the walk while more
        pages remained. With ``model`` each item is validated into that class.
        """
        base = dict(params or {})
        base["limit"] = limit
        if sort_order:
            base["sortOrder"] = sort_order
        items: List[dict] = []
        cursor: Optional[str] = None
        seen: set = set()
        pages = 0
        while True:
            page_params = dict(base)
            if cursor:
                page_params["cursor"] = cursor
            data = self.get(url, page_params)
            page_items = data.get("data") or []
            if model is not None:
                page_items = [model.model_validate(i) for i in page_items]
            items.extend(page_items)
            cursor = data.get("nextPageCursor")
            pages += 1
            if max_items is not None and len(items) >= max_items:
                more = bool(cursor) or len(items) > max_items
                return PagedList(items[:max_items], more)
            if not cursor:
                return PagedList(items, False)
            if max_pages is not None and pages >= max_pages:
                return PagedList(items, True)
            if cursor in seen:
                log.warning("Roblox returned a repeating page cursor for %s; stopping", url)
                return PagedList(items, True)
            seen.add(cursor)

    def fetch_rows(self, url: str, params: Optional[dict] = None, *,
                   key: str = "relatedGroups", page_size: int = DEFAULT_PAGE_SIZE,
                   max_items: Optional[int] = None,
                   model: Optional[Type[Any]] = None) -> PagedList:
        """Walk the ``model.startRowIndex`` / ``nextRowIndex`` pagination style.

        Used by the group allies/enemies endpoints. Returns a :class:`PagedList`.
        With ``model`` each row is validated into that class.
        """
        base = dict(params or {})
        items: List[dict] = []
        start = 0
        while True:
            page_params = dict(base)
            page_params["model.startRowIndex"] = start
            page_params["model.maxRows"] = page_size
            data = self.get(url, page_params)
            rows = data.get(key) or []
            items.extend([model.model_validate(r) for r in rows] if model is not None else rows)
            total = data.get("totalGroupCount")
            next_index = data.get("nextRowIndex")
            if max_items is not None and len(items) >= max_items:
                more = (total is not None and total > len(items)) or len(items) > max_items
                return PagedList(items[:max_items], more)
            if not rows:
                return PagedList(items, False)
            if next_index is None or next_index <= start:
                next_index = start + len(rows)
            if total is not None and next_index >= total:
                return PagedList(items, False)
            if len(rows) < page_size and total is None:
                return PagedList(items, False)
            start = next_index

    # -- domain APIs ----------------------------------------------------------
    # Imported lazily so the modules can type-hint RobloxClient without cycles.

    @cached_property
    def users(self):
        from .users import UsersAPI
        return UsersAPI(self)

    @cached_property
    def friends(self):
        from .friends import FriendsAPI
        return FriendsAPI(self)

    @cached_property
    def groups(self):
        from .groups import GroupsAPI
        return GroupsAPI(self)

    @cached_property
    def games(self):
        from .games import GamesAPI
        return GamesAPI(self)

    @cached_property
    def badges(self):
        from .badges import BadgesAPI
        return BadgesAPI(self)

    @cached_property
    def avatar(self):
        from .avatar import AvatarAPI
        return AvatarAPI(self)

    @cached_property
    def inventory(self):
        from .avatar import InventoryAPI
        return InventoryAPI(self)

    @cached_property
    def account(self):
        from .avatar import AccountAPI
        return AccountAPI(self)

    @cached_property
    def presence(self):
        from .avatar import PresenceAPI
        return PresenceAPI(self)

    @cached_property
    def thumbnails(self):
        from .thumbnails import ThumbnailsAPI
        return ThumbnailsAPI(self)

    @cached_property
    def catalog(self):
        from .catalog import CatalogAPI
        return CatalogAPI(self)

    @property
    def assets(self):
        """Alias of :attr:`catalog` (name used by the 2.0 pre-release)."""
        return self.catalog


def chunked(values: Iterable[Any], size: int) -> Iterator[List[Any]]:
    """Yield ``values`` in lists of at most ``size`` items."""
    batch: List[Any] = []
    for value in values:
        batch.append(value)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch
