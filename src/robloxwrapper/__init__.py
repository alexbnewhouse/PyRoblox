"""Compatibility package: ``import robloxwrapper`` keeps working.

Everything lives in :mod:`pyroblox` now. This module re-exports its public
surface so scripts written against PyRoblox 1.x or the 2.0 CLI rewrite still
run. New code should ``import pyroblox``.
"""

from pyroblox import *  # noqa: F401,F403
from pyroblox import __all__ as _all
from pyroblox import __version__, legacy  # noqa: F401
from pyroblox.legacy import friends, group_games, groups, user_games  # noqa: F401

__all__ = list(_all) + ["friends", "groups", "group_games", "user_games", "legacy"]
