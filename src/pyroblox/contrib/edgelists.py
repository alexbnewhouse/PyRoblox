"""Edge lists with the ``(client, id, depth=...)`` signatures of the 2.0 pre-release."""

from __future__ import annotations

from ..client import RobloxClient
from ..collect import friend_network, group_network


def group_edgelist(client: RobloxClient, group_id: int, *, depth: int = 2
                   ) -> dict[str, list[tuple[int, int]]]:
    """Ally and enemy edges as ``(from_id, to_id)`` tuples.

    ``depth=1`` returns only the seed group's relationships; ``depth=2`` (the
    default, matching the pre-release) also expands each related group.
    """
    snap = group_network(client, group_id, include_members=False,
                         max_groups=0 if depth < 2 else None)
    return {
        "allies": [(e["source"], e["target"]) for e in snap["allies"]],
        "enemies": [(e["source"], e["target"]) for e in snap["enemies"]],
    }


def friend_edgelist(client: RobloxClient, user_id: int, *, depth: int = 2
                    ) -> list[tuple[int, int]]:
    """Friend edges as ``(from_id, to_id)`` tuples, out to ``depth`` hops."""
    snap = friend_network(client, user_id, depth=depth, hydrate_names=False)
    return [(e["source"], e["target"]) for e in snap["edges"]]
