"""Interface to badges.roblox.com endpoints."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from pyroblox import _endpoints as ep
from pyroblox.models.badges import Badge, BadgeAwardDate
from pyroblox.pagination import paginate_endpoint

if TYPE_CHECKING:
    from pyroblox.client import RobloxClient


class BadgesAPI:
    """Methods for the Roblox Badges API."""

    def __init__(self, client: RobloxClient) -> None:
        self._client = client

    def get_info(self, badge_id: int) -> Badge:
        """Get information about a single badge."""
        path = ep.BADGE_INFO.format(badge_id=badge_id)
        resp = self._client.get("badges", path)
        return Badge.model_validate(resp.json())

    def get_universe_badges(
        self, universe_id: int, *, limit: int = 100, max_pages: int | None = None
    ) -> Iterator[Badge]:
        """Lazily iterate all badges for a game/universe."""
        path = ep.UNIVERSE_BADGES.format(universe_id=universe_id)
        return paginate_endpoint(
            self._client, "badges", path, Badge,
            limit=limit, max_pages=max_pages,
            extra_params={"sortOrder": "Asc"},
        )

    def get_user_badges(
        self, user_id: int, *, limit: int = 100, max_pages: int | None = None
    ) -> Iterator[Badge]:
        """Lazily iterate badges earned by a user."""
        path = ep.USER_BADGES.format(user_id=user_id)
        return paginate_endpoint(
            self._client, "badges", path, Badge,
            limit=limit, max_pages=max_pages,
            extra_params={"sortOrder": "Asc"},
        )

    def get_awarded_dates(
        self, user_id: int, badge_ids: list[int]
    ) -> list[BadgeAwardDate]:
        """Get when a user earned specific badges.

        Args:
            user_id: The user to check.
            badge_ids: List of badge IDs to look up.
        """
        path = ep.USER_BADGE_AWARDED_DATES.format(user_id=user_id)
        resp = self._client.get(
            "badges", path,
            params={"badgeIds": ",".join(str(bid) for bid in badge_ids)},
        )
        data = resp.json()
        return [BadgeAwardDate.model_validate(d) for d in data.get("data", [])]
