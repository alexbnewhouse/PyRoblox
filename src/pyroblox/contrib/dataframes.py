"""``build_network_dataframes`` with the signature of the 2.0 pre-release."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..client import RobloxClient
from ..collect import group_network
from ..export import to_dataframe


def build_network_dataframes(client: RobloxClient, group_id: int, *,
                             output_dir: str | Path | None = None,
                             include_favorites: bool = True) -> dict[str, Any]:
    """Group network as DataFrames keyed ``allies``, ``enemies``, ``group_info``,
    ``membership``, ``user_info``, ``favorites``, ``game_info``.

    Unlike the pre-release, membership covers every group in the ally/enemy
    neighbourhood (not only the seed group) and profiles come from the batch
    endpoint. With ``output_dir`` each frame is written as ``<name>_<id>.csv``.
    """
    import pandas as pd

    snap = group_network(client, group_id, include_members=True,
                         include_member_profiles=False,
                         include_favorites=include_favorites)
    frames: dict[str, Any] = {
        "allies": pd.DataFrame([(e["source"], e["target"]) for e in snap["allies"]],
                               columns=["From", "To"]),
        "enemies": pd.DataFrame([(e["source"], e["target"]) for e in snap["enemies"]],
                                columns=["From", "To"]),
        "group_info": to_dataframe(snap["groups"]),
        "membership": pd.DataFrame([(m["groupId"], (m.get("user") or {}).get("userId"))
                                    for m in snap["membership"]], columns=["Group", "User"]),
        "user_info": to_dataframe(snap["members"]),
        "favorites": pd.DataFrame([(e["userId"], e["universeId"])
                                   for e in snap.get("favorite_games", [])],
                                  columns=["User", "FavoritedGame"]),
        "game_info": to_dataframe(snap.get("games", [])),
    }
    if output_dir is not None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        for name, df in frames.items():
            df.to_csv(out / f"{name}_{group_id}.csv", index=False)
    frames["snapshot"] = snap
    return frames
