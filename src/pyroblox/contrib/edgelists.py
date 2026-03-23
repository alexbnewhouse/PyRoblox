"""Build social-network edgelists from Roblox group and friend data."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyroblox.client import RobloxClient

logger = logging.getLogger(__name__)


def group_edgelist(
    client: RobloxClient,
    group_id: int,
    *,
    depth: int = 2,
) -> dict[str, list[tuple[int, int]]]:
    """Build ally and enemy edgelists for group network analysis.

    Traverses the group relationship graph to the specified depth,
    collecting (source_id, target_id) edges.

    Args:
        client: A RobloxClient instance.
        group_id: Seed group ID.
        depth: Network traversal depth (1 = direct only, 2 = include one hop).

    Returns:
        Dict with ``"allies"`` and ``"enemies"`` keys, each containing
        a list of ``(from_id, to_id)`` tuples.
    """
    ally_edges: list[tuple[int, int]] = []
    enemy_edges: list[tuple[int, int]] = []

    # Depth 1: direct relationships
    allies = client.groups.get_allies(group_id)
    ally_ids = []
    for group in allies:
        ally_ids.append(group.id)
        ally_edges.append((group_id, group.id))

    enemies = client.groups.get_enemies(group_id)
    enemy_ids = []
    for group in enemies:
        enemy_ids.append(group.id)
        enemy_edges.append((group_id, group.id))

    # Depth 2+: traverse further hops
    if depth >= 2:
        for aid in ally_ids:
            try:
                hop_allies = client.groups.get_allies(aid)
                for group in hop_allies:
                    ally_edges.append((aid, group.id))
            except Exception:
                logger.warning("Failed to fetch allies for group %d, skipping", aid)

        for eid in enemy_ids:
            try:
                hop_enemies = client.groups.get_enemies(eid)
                for group in hop_enemies:
                    enemy_edges.append((eid, group.id))
            except Exception:
                logger.warning("Failed to fetch enemies for group %d, skipping", eid)

    return {"allies": ally_edges, "enemies": enemy_edges}


def friend_edgelist(
    client: RobloxClient,
    user_id: int,
    *,
    depth: int = 2,
) -> list[tuple[int, int]]:
    """Build a friend network edgelist.

    Args:
        client: A RobloxClient instance.
        user_id: Seed user ID.
        depth: Network traversal depth (1 = direct only, 2 = include one hop).

    Returns:
        List of ``(from_id, to_id)`` tuples representing friend edges.
    """
    edges: list[tuple[int, int]] = []

    # Depth 1: direct friends
    friends = client.friends.get_friends(user_id)
    friend_ids = []
    for friend in friends:
        friend_ids.append(friend.id)
        edges.append((user_id, friend.id))

    # Depth 2+: friends of friends
    if depth >= 2:
        for fid in friend_ids:
            try:
                hop_friends = client.friends.get_friends(fid)
                for friend in hop_friends:
                    edges.append((fid, friend.id))
            except Exception:
                logger.warning("Failed to fetch friends for user %d, skipping", fid)

    return edges
