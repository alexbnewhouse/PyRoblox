"""Turn Roblox URLs and shorthand strings into (entity type, numeric id) pairs.

Researchers usually have a link copied from a browser, not an id. This module
accepts the common link shapes and the ``type:id`` shorthand::

    >>> parse_roblox_url("https://www.roblox.com/users/261/profile")
    ('user', 261)
    >>> parse_roblox_url("https://www.roblox.com/games/1818/Classic-Crossroads?x=1")
    ('game', 1818)
    >>> parse_roblox_url("group:7")
    ('group', 7)

Note that a ``game`` link carries a *place* id, not a universe id. Use
``client.games.place_to_universe`` to convert it before calling game endpoints.
"""

from __future__ import annotations

import re
from typing import Tuple

ENTITY_TYPES = ("user", "group", "game", "asset", "badge", "bundle")

_SHORTHAND = re.compile(r"(%s):(\d+)$" % "|".join(ENTITY_TYPES), re.IGNORECASE)
_HOST = re.compile(r"^(?:https?://)?(?:www\.|web\.|m\.)?roblox\.com/", re.IGNORECASE)
_PATHS = [
    (re.compile(r"^users/(\d+)(?:[/?#]|$)"), "user"),
    (re.compile(r"^(?:groups|communities)/(\d+)(?:[/?#]|$)"), "group"),
    (re.compile(r"^games/(\d+)(?:[/?#]|$)"), "game"),
    (re.compile(r"^(?:catalog|library)/(\d+)(?:[/?#]|$)"), "asset"),
    (re.compile(r"^badges/(\d+)(?:[/?#]|$)"), "badge"),
    (re.compile(r"^bundles/(\d+)(?:[/?#]|$)"), "bundle"),
]
_DIGITS = re.compile(r"^\d+$")


def parse_roblox_url(raw: str) -> Tuple[str, int]:
    """Return ``(entity_type, id)`` for a Roblox URL or ``type:id`` string.

    Raises :class:`ValueError` when the string is not recognised.
    """
    s = raw.strip()
    if not s:
        raise ValueError("empty Roblox identifier")
    m = _SHORTHAND.fullmatch(s)
    if m:
        return m.group(1).lower(), int(m.group(2))
    if _HOST.match(s):
        path = _HOST.sub("", s)
        for pattern, entity_type in _PATHS:
            m = pattern.match(path)
            if m:
                return entity_type, int(m.group(1))
    raise ValueError(f"unrecognized Roblox URL: {raw!r}")


def looks_like_id(value: str) -> bool:
    """True when ``value`` is a bare positive integer such as ``"261"``."""
    return bool(_DIGITS.match(value.strip()))
