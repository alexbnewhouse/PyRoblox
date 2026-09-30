import json

import pandas as pd
import pytest

from robloxwrapper.export import (
    Snapshot, edgelist_to_graphml, edges_to_dataframe, flatten, to_dataframe,
    write_records,
)


def test_flatten_nested_dicts_and_lists():
    rec = {
        "id": 7,
        "owner": {"userId": 1, "username": "Roblox", "meta": {"x": True}},
        "shout": None,
        "tags": ["a", "b", None],
        "roles": [{"id": 1}, {"id": 2}],
        "empty": {},
    }
    flat = flatten(rec)
    assert flat == {
        "id": 7,
        "owner_userId": 1,
        "owner_username": "Roblox",
        "owner_meta_x": True,
        "shout": None,
        "tags": "a;b;",
        "roles": '[{"id": 1}, {"id": 2}]',
        "empty": None,
    }


def test_to_dataframe_unions_columns_and_handles_empty():
    df = to_dataframe([{"a": 1}, {"a": 2, "b": {"c": 3}}])
    assert list(df.columns) == ["a", "b_c"]
    assert df.shape == (2, 2)
    assert to_dataframe([]).empty


def test_write_records_csv_and_json(tmp_path):
    recs = [{"id": 1, "o": {"k": "v"}}]
    p = write_records(recs, tmp_path / "sub" / "x.csv")
    df = pd.read_csv(p)
    assert list(df.columns) == ["id", "o_k"] and df.iloc[0]["o_k"] == "v"
    p = write_records(recs, tmp_path / "x.json", fmt="json")
    assert json.loads(p.read_text()) == recs
    with pytest.raises(ValueError):
        write_records(recs, tmp_path / "x.parquet", fmt="parquet")


def test_snapshot_add_omit_truncate_and_save(tmp_path):
    snap = Snapshot("user", 261)
    snap.add("profile", {"id": 261, "name": "Shedletsky"})
    snap.add("friends", [{"id": 1}, {"id": 2}])
    snap.add("badges", None)
    snap.omit("inventory", "private")
    snap.mark_truncated("friends")
    snap.record_error("groups", RuntimeError("boom"))

    assert snap["profile"] == [{"id": 261, "name": "Shedletsky"}]
    assert "friends" in snap and snap.get("nope") is None
    assert snap.counts() == {"profile": 1, "friends": 2, "badges": 0}
    assert snap.to_dataframes()["friends"].shape == (2, 1)

    paths = snap.save(tmp_path)
    names = sorted(p.name for p in paths)
    assert names == sorted([
        "user_261_profile.csv", "user_261_friends.csv", "user_261_badges.csv",
        "user_261_manifest.json",
    ])
    manifest = json.loads((tmp_path / "user_261_manifest.json").read_text())
    assert manifest["entity"] == "user" and manifest["id"] == 261
    assert manifest["omitted"] == {"inventory": "private"}
    assert manifest["truncated"] == {"friends": True}
    assert manifest["errors"][0]["error"] == "RuntimeError"
    assert manifest["counts"]["friends"] == 2
    assert "captured_at" in manifest
    # empty table still produces a (header-less) file rather than crashing
    assert (tmp_path / "user_261_badges.csv").exists()


def test_snapshot_save_json_and_custom_prefix(tmp_path):
    snap = Snapshot("group", 7)
    snap.add("profile", {"id": 7})
    paths = snap.save(tmp_path, fmt="json", prefix="g7")
    assert {p.name for p in paths} == {"g7_profile.json", "g7_manifest.json"}


def test_edges_to_dataframe_tuples_and_dicts():
    df = edges_to_dataframe([(1, 2), (2, 3)])
    assert list(df.columns) == ["source", "target"] and len(df) == 2
    df = edges_to_dataframe([{"source": 1, "target": 2, "kind": "ally"}])
    assert list(df.columns) == ["source", "target", "kind"]
    assert list(edges_to_dataframe([]).columns) == ["source", "target"]


def test_edgelist_to_graphml(tmp_path):
    import networkx as nx
    p = edgelist_to_graphml([(1, 2), {"source": 2, "target": 3, "kind": "ally"}],
                            tmp_path / "g.graphml",
                            nodes={1: {"name": "a", "tags": [1, 2]}, 2: {"name": None}})
    g = nx.read_graphml(p)
    assert set(g.nodes) == {"1", "2", "3"}
    assert g.edges["2", "3"]["kind"] == "ally"
    assert g.nodes["1"]["tags"] == "[1, 2]"
