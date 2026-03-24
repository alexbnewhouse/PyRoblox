"""Core HTTP client for Roblox API calls with retry and rate-limit handling."""

from __future__ import annotations

import logging
import random
import time
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from pyroblox.api.avatar import AvatarAPI
    from pyroblox.api.badges import BadgesAPI
    from pyroblox.api.catalog import CatalogAPI
    from pyroblox.api.friends import FriendsAPI
    from pyroblox.api.games import GamesAPI
    from pyroblox.api.groups import GroupsAPI
    from pyroblox.api.inventory import InventoryAPI
    from pyroblox.api.thumbnails import ThumbnailsAPI
    from pyroblox.api.users import UsersAPI

from pyroblox.exceptions import (
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    RobloxAPIError,
)

logger = logging.getLogger(__name__)

DEFAULT_BASE_URLS: dict[str, str] = {
    "groups": "https://groups.roblox.com",
    "friends": "https://friends.roblox.com",
    "users": "https://users.roblox.com",
    "games": "https://games.roblox.com",
    "economy": "https://economy.roblox.com",
    "inventory": "https://inventory.roblox.com",
    "thumbnails": "https://thumbnails.roblox.com",
    "presence": "https://presence.roblox.com",
    "badges": "https://badges.roblox.com",
    "catalog": "https://catalog.roblox.com",
    "avatar": "https://avatar.roblox.com",
}


class RobloxClient:
    """Central HTTP client for all Roblox API interactions.

    Handles authentication, rate limiting with exponential backoff,
    and automatic retries on transient errors.

    Usage::

        with RobloxClient(cookie="your_cookie") as client:
            group = client.groups.get_info(5351020)
            print(group.name)
    """

    def __init__(
        self,
        cookie: str | None = None,
        *,
        max_retries: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 120.0,
        timeout: float = 30.0,
        base_urls: dict[str, str] | None = None,
    ) -> None:
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._base_urls = {**DEFAULT_BASE_URLS, **(base_urls or {})}

        headers = {"Accept": "application/json"}
        cookies = httpx.Cookies()
        if cookie:
            cookies.set(".ROBLOSECURITY", cookie, domain=".roblox.com")

        self._http = httpx.Client(
            timeout=timeout,
            headers=headers,
            cookies=cookies,
            follow_redirects=True,
        )

        # Lazy-initialized API resources
        self._groups_api: GroupsAPI | None = None
        self._users_api: UsersAPI | None = None
        self._friends_api: FriendsAPI | None = None
        self._games_api: GamesAPI | None = None
        self._badges_api: BadgesAPI | None = None
        self._inventory_api: InventoryAPI | None = None
        self._catalog_api: CatalogAPI | None = None
        self._avatar_api: AvatarAPI | None = None
        self._thumbnails_api: ThumbnailsAPI | None = None

    def __enter__(self) -> RobloxClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._http.close()

    def request(
        self, method: str, domain: str, path: str, **kwargs: Any
    ) -> httpx.Response:
        """Make an API request with automatic rate-limit handling and retry.

        Args:
            method: HTTP method (GET, POST, etc.).
            domain: Key into base_urls (e.g., "groups", "users").
            path: URL path (e.g., "/v1/groups/123").
            **kwargs: Passed through to httpx.

        Returns:
            The successful HTTP response.

        Raises:
            RateLimitError: If rate limited after exhausting retries.
            AuthenticationError: On 401/403 responses.
            NotFoundError: On 404 responses.
            RobloxAPIError: On other error responses.
        """
        url = f"{self._base_urls[domain]}{path}"

        for attempt in range(self._max_retries + 1):
            try:
                response = self._http.request(method, url, **kwargs)
            except httpx.TransportError as exc:
                if attempt < self._max_retries:
                    delay = self._exponential_delay(attempt)
                    logger.warning(
                        "Transport error on %s (attempt %d), retrying in %.1fs: %s",
                        url, attempt + 1, delay, exc,
                    )
                    time.sleep(delay)
                    continue
                raise RobloxAPIError(0, [{"message": str(exc)}], url) from exc

            if response.status_code == 200:
                return response

            errors = self._parse_errors(response)

            if response.status_code == 429:
                retry_after = self._parse_retry_after(response)
                if attempt < self._max_retries:
                    if retry_after:
                        delay = min(retry_after, self._max_delay)
                    else:
                        delay = self._exponential_delay(attempt)
                    logger.warning(
                        "Rate limited on %s (attempt %d), retrying in %.1fs",
                        url, attempt + 1, delay,
                    )
                    time.sleep(delay)
                    continue
                raise RateLimitError(errors, url, retry_after)

            if response.status_code in (401, 403):
                raise AuthenticationError(response.status_code, errors, url)

            if response.status_code == 404:
                raise NotFoundError(404, errors, url)

            if response.status_code >= 500 and attempt < self._max_retries:
                delay = self._exponential_delay(attempt)
                logger.warning(
                    "Server error %d on %s (attempt %d), retrying in %.1fs",
                    response.status_code, url, attempt + 1, delay,
                )
                time.sleep(delay)
                continue

            raise RobloxAPIError(response.status_code, errors, url)

        # Should not be reached, but satisfy type checker
        raise RobloxAPIError(0, [], url)  # pragma: no cover

    def get(self, domain: str, path: str, **kwargs: Any) -> httpx.Response:
        """Convenience method for GET requests."""
        return self.request("GET", domain, path, **kwargs)

    def post(self, domain: str, path: str, **kwargs: Any) -> httpx.Response:
        """Convenience method for POST requests."""
        return self.request("POST", domain, path, **kwargs)

    def _exponential_delay(self, attempt: int) -> float:
        """Exponential backoff with jitter."""
        delay = min(self._base_delay * (2**attempt), self._max_delay)
        return delay * (0.5 + random.random() * 0.5)  # noqa: S311

    @staticmethod
    def _parse_retry_after(response: httpx.Response) -> float | None:
        header = response.headers.get("retry-after")
        if header:
            try:
                return float(header)
            except ValueError:
                return None
        return None

    @staticmethod
    def _parse_errors(response: httpx.Response) -> list[dict[str, object]]:
        try:
            body = response.json()
            return body.get("errors", [])  # type: ignore[no-any-return]
        except Exception:
            return []

    # --- Resource accessors ---

    @property
    def groups(self) -> GroupsAPI:
        if self._groups_api is None:
            from pyroblox.api.groups import GroupsAPI

            self._groups_api = GroupsAPI(self)
        return self._groups_api

    @property
    def users(self) -> UsersAPI:
        if self._users_api is None:
            from pyroblox.api.users import UsersAPI

            self._users_api = UsersAPI(self)
        return self._users_api

    @property
    def friends(self) -> FriendsAPI:
        if self._friends_api is None:
            from pyroblox.api.friends import FriendsAPI

            self._friends_api = FriendsAPI(self)
        return self._friends_api

    @property
    def games(self) -> GamesAPI:
        if self._games_api is None:
            from pyroblox.api.games import GamesAPI

            self._games_api = GamesAPI(self)
        return self._games_api

    @property
    def badges(self) -> BadgesAPI:
        if self._badges_api is None:
            from pyroblox.api.badges import BadgesAPI

            self._badges_api = BadgesAPI(self)
        return self._badges_api

    @property
    def inventory(self) -> InventoryAPI:
        if self._inventory_api is None:
            from pyroblox.api.inventory import InventoryAPI

            self._inventory_api = InventoryAPI(self)
        return self._inventory_api

    @property
    def catalog(self) -> CatalogAPI:
        if self._catalog_api is None:
            from pyroblox.api.catalog import CatalogAPI

            self._catalog_api = CatalogAPI(self)
        return self._catalog_api

    @property
    def avatar(self) -> AvatarAPI:
        if self._avatar_api is None:
            from pyroblox.api.avatar import AvatarAPI

            self._avatar_api = AvatarAPI(self)
        return self._avatar_api

    @property
    def thumbnails(self) -> ThumbnailsAPI:
        if self._thumbnails_api is None:
            from pyroblox.api.thumbnails import ThumbnailsAPI

            self._thumbnails_api = ThumbnailsAPI(self)
        return self._thumbnails_api
