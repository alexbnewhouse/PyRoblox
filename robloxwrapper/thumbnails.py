"""Thumbnail image URLs for users, groups, games, places, assets, badges and
bundles from ``thumbnails.roblox.com``, plus helpers to download the images from
the ``rbxcdn.com`` CDN and save them to disk. No call here needs a cookie.
"""

from __future__ import annotations

import hashlib
import logging
import os
from typing import Dict, Iterable, List, Tuple

from .client import RobloxClient, chunked
from .errors import NotFoundError, PrivateError

log = logging.getLogger(__name__)

#: kind -> (path under /v1/, query parameter that carries the ids)
KINDS: Dict[str, Tuple[str, str]] = {
    "user-headshot": ("users/avatar-headshot", "userIds"),
    "user-avatar": ("users/avatar", "userIds"),
    "user-bust": ("users/avatar-bust", "userIds"),
    "group-icon": ("groups/icons", "groupIds"),
    "game-icon": ("games/icons", "universeIds"),
    "game-thumbnail": ("games/multiget/thumbnails", "universeIds"),
    "place-icon": ("places/gameicons", "placeIds"),
    "asset": ("assets", "assetIds"),
    "badge-icon": ("badges/icons", "badgeIds"),
    "bundle": ("bundles/thumbnails", "bundleIds"),
}


class ThumbnailsAPI:
    """Batch thumbnail lookups and downloads."""

    BASE = "https://thumbnails.roblox.com"

    def __init__(self, client: RobloxClient):
        self.client = client

    def get(self, kind: str, ids: Iterable[int], size: str = "420x420",
            fmt: str = "Png") -> list:
        """Thumbnail records (targetId, state, imageUrl) for ``ids`` of ``kind``
        (a key of ``KINDS``); ``imageUrl`` is null unless ``state`` is Completed."""
        if kind not in KINDS:
            raise ValueError(f"unknown thumbnail kind {kind!r}; valid kinds: "
                             + ", ".join(sorted(KINDS)))
        path, key = KINDS[kind]
        url = f"{self.BASE}/v1/{path}"
        out: List[dict] = []
        for chunk in chunked(ids, 100):
            params = {key: ",".join(str(i) for i in chunk), "size": size, "format": fmt}
            data = self.client.get(url, params).get("data") or []
            if kind == "game-thumbnail":
                out.extend(_flatten_game_thumbnails(data))
            else:
                out.extend(data)
        return out

    # -- convenience wrappers -------------------------------------------------

    def user_headshots(self, ids: Iterable[int], size: str = "150x150") -> list:
        """Avatar headshots for user ids."""
        return self.get("user-headshot", ids, size=size)

    def user_avatars(self, ids: Iterable[int], size: str = "420x420") -> list:
        """Full-body avatar renders for user ids."""
        return self.get("user-avatar", ids, size=size)

    def group_icons(self, ids: Iterable[int], size: str = "150x150") -> list:
        """Group icons for group ids."""
        return self.get("group-icon", ids, size=size)

    def game_icons(self, ids: Iterable[int], size: str = "150x150") -> list:
        """Experience icons for universe ids."""
        return self.get("game-icon", ids, size=size)

    def asset_thumbnails(self, ids: Iterable[int], size: str = "150x150") -> list:
        """Thumbnails for asset ids."""
        return self.get("asset", ids, size=size)

    def badge_icons(self, ids: Iterable[int], size: str = "150x150") -> list:
        """Badge icons for badge ids."""
        return self.get("badge-icon", ids, size=size)

    # -- downloads ------------------------------------------------------------

    def download(self, url: str) -> bytes:
        """The image bytes behind a thumbnail ``imageUrl``."""
        return self.client.download(url)

    def save(self, kind: str, ids: Iterable[int], out_dir, size: str = "420x420") -> list:
        """Download every Completed thumbnail to ``<out_dir>/<kind>_<targetId>.png``
        and return records (kind, targetId, url, path, sha256). Files that already
        exist are not re-downloaded; images Roblox answers 404/403 for are logged and skipped."""
        out_dir = os.fspath(out_dir)
        os.makedirs(out_dir, exist_ok=True)
        records: List[dict] = []
        for rec in self.get(kind, ids, size=size):
            url = rec.get("imageUrl")
            if rec.get("state") != "Completed" or not url:
                continue
            target_id = rec.get("targetId")
            path = os.path.join(out_dir, f"{kind}_{target_id}.png")
            if os.path.exists(path):
                with open(path, "rb") as fh:
                    digest = hashlib.sha256(fh.read()).hexdigest()
            else:
                try:
                    content = self.download(url)
                except (NotFoundError, PrivateError) as exc:
                    log.info("skipping %s %s: %s (%s)", kind, target_id, url, exc)
                    continue
                tmp = path + ".tmp"
                with open(tmp, "wb") as fh:
                    fh.write(content)
                os.replace(tmp, path)
                digest = hashlib.sha256(content).hexdigest()
            records.append({"kind": kind, "targetId": target_id, "url": url,
                            "path": path, "sha256": digest})
        return records


def _flatten_game_thumbnails(data: list) -> List[dict]:
    """One record per thumbnail, keyed on the universe rather than the image.

    The multiget endpoint nests ``thumbnails`` under each universe; the image's
    own id is kept as ``thumbnailTargetId`` so nothing is lost.
    """
    out: List[dict] = []
    for entry in data:
        universe_id = entry.get("universeId")
        for thumb in entry.get("thumbnails") or []:
            record = dict(thumb)
            if "targetId" in record:
                record["thumbnailTargetId"] = record["targetId"]
            record["universeId"] = universe_id
            record["targetId"] = universe_id
            out.append(record)
    return out
