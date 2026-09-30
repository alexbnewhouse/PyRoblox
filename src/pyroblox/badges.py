"""Badges: the badges a user has earned, the badges an experience awards, and
single badge lookups, all from ``badges.roblox.com``. Universe badges and single
badge lookups are public; a user's badge list and awarded dates now require a
``.ROBLOSECURITY`` cookie (Roblox began answering 401/403 unauthenticated in
2026-09).
"""

from __future__ import annotations

from typing import Iterable, List, Optional

from .client import PagedList, RobloxClient, chunked
from .models.badges import Badge, BadgeAwardDate


class BadgesAPI:
    """Read-only access to badges.roblox.com."""

    BASE = "https://badges.roblox.com"

    def __init__(self, client: RobloxClient):
        self.client = client

    def get_user_badges(self, user_id: int,
                        max_items: Optional[int] = None) -> PagedList[Badge]:
        """Return the :class:`Badge` list ``user_id`` has earned (oldest first).
        Requires a cookie."""
        url = f"{self.BASE}/v1/users/{user_id}/badges"
        return self.client.fetch_all(url, limit=100, max_items=max_items,
                                     sort_order="Asc", model=Badge)

    def get_awarded_dates(self, user_id: int,
                          badge_ids: Iterable[int]) -> list[BadgeAwardDate]:
        """Return a :class:`BadgeAwardDate` for each of ``badge_ids`` that
        ``user_id`` has earned; badges the user lacks are omitted. Requires a
        cookie. Roblox allows about 10 calls per minute."""
        url = f"{self.BASE}/v1/users/{user_id}/badges/awarded-dates"
        out: List[dict] = []
        for chunk in chunked(badge_ids, 100):
            body = self.client.get(url, {"badgeIds": ",".join(str(i) for i in chunk)})
            out.extend(body.get("data") or [])
        return BadgeAwardDate.from_list(out)

    def get_universe_badges(self, universe_id: int,
                            max_items: Optional[int] = None) -> PagedList[Badge]:
        """Return the :class:`Badge` list an experience (universe) awards, with
        award statistics."""
        url = f"{self.BASE}/v1/universes/{universe_id}/badges"
        return self.client.fetch_all(url, limit=100, max_items=max_items,
                                     sort_order="Asc", model=Badge)

    def get_info(self, badge_id: int) -> Badge:
        """Return the :class:`Badge` for ``badge_id``: name, description, enabled,
        statistics, awarding universe."""
        return Badge.model_validate(self.client.get(f"{self.BASE}/v1/badges/{badge_id}"))
