"""Badges: the badges a user has earned, the badges an experience awards, and
single badge lookups, all from ``badges.roblox.com``. Universe badges and single
badge lookups are public; a user's badge list and awarded dates now require a
``.ROBLOSECURITY`` cookie (Roblox began answering 401/403 unauthenticated in
2026-09).
"""

from __future__ import annotations

from typing import Iterable, List, Optional

from .client import PagedList, RobloxClient, chunked


class BadgesAPI:
    """Read-only access to badges.roblox.com."""

    BASE = "https://badges.roblox.com"

    def __init__(self, client: RobloxClient):
        self.client = client

    def user_badges(self, user_id: int, max_items: Optional[int] = None) -> PagedList:
        """Badges ``user_id`` has earned (oldest first). Requires a cookie."""
        url = f"{self.BASE}/v1/users/{user_id}/badges"
        return self.client.fetch_all(url, limit=100, max_items=max_items, sort_order="Asc")

    def awarded_dates(self, user_id: int, badge_ids: Iterable[int]) -> list:
        """When ``user_id`` earned each of ``badge_ids`` (``badgeId``, ``awardedDate``);
        badges the user lacks are omitted. Requires a cookie. Roblox allows about
        10 calls per minute."""
        url = f"{self.BASE}/v1/users/{user_id}/badges/awarded-dates"
        out: List[dict] = []
        for chunk in chunked(badge_ids, 100):
            body = self.client.get(url, {"badgeIds": ",".join(str(i) for i in chunk)})
            out.extend(body.get("data") or [])
        return out

    def universe_badges(self, universe_id: int, max_items: Optional[int] = None) -> PagedList:
        """Badges an experience (universe) awards, with award statistics."""
        url = f"{self.BASE}/v1/universes/{universe_id}/badges"
        return self.client.fetch_all(url, limit=100, max_items=max_items, sort_order="Asc")

    def get(self, badge_id: int) -> dict:
        """One badge: id, name, description, enabled, statistics, awardingUniverse."""
        return self.client.get(f"{self.BASE}/v1/badges/{badge_id}")
