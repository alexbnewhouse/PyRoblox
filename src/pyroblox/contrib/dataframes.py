"""Build comprehensive social-network DataFrames from Roblox data."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pyroblox.contrib.edgelists import group_edgelist
from pyroblox.exceptions import PyRobloxError

if TYPE_CHECKING:
    import pandas as pd

    from pyroblox.client import RobloxClient

logger = logging.getLogger(__name__)


def _require_pandas() -> Any:
    try:
        import pandas

        return pandas
    except ImportError:
        raise ImportError(
            "pandas is required for DataFrame operations. "
            "Install it with: pip install pyroblox[analysis]"
        ) from None


def build_network_dataframes(
    client: RobloxClient,
    group_id: int,
    *,
    output_dir: str | Path | None = None,
) -> dict[str, pd.DataFrame]:
    """Build a complete social network dataset from a seed group.

    Collects group relationships, membership, user info, and game
    favorites into a set of DataFrames. Optionally writes CSVs.

    Args:
        client: An authenticated RobloxClient.
        group_id: Seed group ID.
        output_dir: If provided, write CSVs to this directory.

    Returns:
        Dict of DataFrames keyed by name: ``allies``, ``enemies``,
        ``group_info``, ``membership``, ``user_info``, ``favorites``,
        ``game_info``.
    """
    pd = _require_pandas()
    result: dict[str, pd.DataFrame] = {}

    # --- Group relationship edgelists ---
    logger.info("Building group edgelists for group %d", group_id)
    el = group_edgelist(client, group_id)
    result["allies"] = pd.DataFrame(el["allies"], columns=["From", "To"])
    result["enemies"] = pd.DataFrame(el["enemies"], columns=["From", "To"])

    # --- Group info ---
    all_group_ids = set()
    for col in ("From", "To"):
        all_group_ids.update(result["allies"][col].tolist())
        all_group_ids.update(result["enemies"][col].tolist())

    logger.info("Collecting info for %d groups", len(all_group_ids))
    group_rows = []
    for gid in all_group_ids:
        try:
            info = client.groups.get_info(gid)
            group_rows.append(info.model_dump())
        except PyRobloxError:
            logger.warning("Failed to get info for group %d", gid)
    result["group_info"] = pd.DataFrame(group_rows)

    # --- Group membership ---
    logger.info("Collecting membership for group %d", group_id)
    member_edges = []
    for member in client.groups.get_members(group_id):
        member_edges.append((group_id, member.user.user_id))
    result["membership"] = pd.DataFrame(member_edges, columns=["Group", "User"])

    # --- User info ---
    user_ids = set(result["membership"]["User"].tolist())
    logger.info("Collecting info for %d users", len(user_ids))
    user_rows = []
    # Batch fetch where possible
    user_id_list = list(user_ids)
    for i in range(0, len(user_id_list), 100):
        batch = user_id_list[i : i + 100]
        try:
            users = client.users.get_batch(batch)
            for u in users:
                user_rows.append(u.model_dump())
        except PyRobloxError:
            logger.warning("Failed to batch-fetch users, falling back to individual")
            for uid in batch:
                try:
                    u = client.users.get_info(uid)
                    user_rows.append(u.model_dump())
                except PyRobloxError:
                    logger.warning("Failed to get info for user %d", uid)
    result["user_info"] = pd.DataFrame(user_rows)

    # --- User favorites ---
    logger.info("Collecting game favorites for %d users", len(user_ids))
    fav_edges = []
    game_info: dict[int, dict[str, Any]] = {}
    for uid in user_ids:
        try:
            for game in client.games.get_user_favorites(uid, max_pages=5):
                fav_edges.append((uid, game.id))
                if game.id not in game_info:
                    game_info[game.id] = game.model_dump()
        except PyRobloxError:
            logger.warning("Failed to get favorites for user %d", uid)
    result["favorites"] = pd.DataFrame(fav_edges, columns=["User", "FavoritedGame"])
    result["game_info"] = pd.DataFrame(list(game_info.values()))

    # --- Write CSVs ---
    if output_dir is not None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        for name, df in result.items():
            path = out / f"{name}_{group_id}.csv"
            df.to_csv(path, index=False)
            logger.info("Wrote %s", path)

    return result
