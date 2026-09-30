"""Turn API records into flat tables and write them to disk.

Roblox responses are nested JSON. Spreadsheet users need one row per record and
one column per value, so :func:`flatten` turns ``{"owner": {"userId": 1}}`` into
``{"owner_userId": 1}``. Lists of scalars become ``;``-joined strings and lists
of objects are kept as JSON text so nothing is silently dropped.

:class:`Snapshot` bundles the tables collected for one entity together with
metadata (when it was captured, what was omitted, what was truncated) and
writes them as ``<entity>_<id>_<table>.csv`` plus a manifest.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

import pandas as pd

RecordList = List[Dict[str, Any]]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def flatten(record: Mapping[str, Any], sep: str = "_", prefix: str = "") -> Dict[str, Any]:
    """Flatten nested dicts into a single-level dict suitable for one CSV row."""
    out: Dict[str, Any] = {}
    for key, value in record.items():
        name = f"{prefix}{sep}{key}" if prefix else str(key)
        if isinstance(value, Mapping):
            if value:
                out.update(flatten(value, sep=sep, prefix=name))
            else:
                out[name] = None
        elif isinstance(value, (list, tuple)):
            if all(not isinstance(v, (Mapping, list, tuple)) for v in value):
                out[name] = ";".join("" if v is None else str(v) for v in value)
            else:
                out[name] = json.dumps(value, ensure_ascii=False, default=str)
        else:
            out[name] = value
    return out


def to_dataframe(records: Iterable[Mapping[str, Any]], sep: str = "_") -> pd.DataFrame:
    """Build a DataFrame with one flattened row per record."""
    rows = [flatten(r, sep=sep) for r in records]
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def write_records(records: Iterable[Mapping[str, Any]], path: Union[str, Path],
                  fmt: str = "csv") -> Path:
    """Write records as CSV (flattened) or JSON (as-is). Returns the path written."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    records = list(records)
    if fmt == "csv":
        to_dataframe(records).to_csv(path, index=False)
    elif fmt == "json":
        write_json(records, path)
    else:
        raise ValueError(f"unknown format {fmt!r}; use 'csv' or 'json'")
    return path


def write_json(obj: Any, path: Union[str, Path]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str),
                   encoding="utf-8")
    tmp.replace(path)
    return path


@dataclass
class Snapshot:
    """Everything collected about one entity, ready to save."""

    entity: str
    entity_id: int
    tables: Dict[str, RecordList] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.meta.setdefault("entity", self.entity)
        self.meta.setdefault("id", self.entity_id)
        self.meta.setdefault("captured_at", utc_now_iso())
        self.meta.setdefault("omitted", {})
        self.meta.setdefault("truncated", {})
        self.meta.setdefault("errors", [])

    # -- building -------------------------------------------------------------

    def add(self, name: str, records: Union[RecordList, Mapping[str, Any], None]) -> None:
        """Add a table. A single dict becomes a one-row table."""
        if records is None:
            records = []
        elif isinstance(records, Mapping):
            records = [dict(records)]
        self.tables[name] = list(records)

    def omit(self, name: str, reason: str) -> None:
        self.meta["omitted"][name] = reason

    def mark_truncated(self, name: str) -> None:
        self.meta["truncated"][name] = True

    def record_error(self, name: str, error: Exception) -> None:
        self.meta["errors"].append({"table": name, "error": type(error).__name__,
                                    "message": str(error)})

    # -- reading --------------------------------------------------------------

    def __getitem__(self, name: str) -> RecordList:
        return self.tables[name]

    def __contains__(self, name: str) -> bool:
        return name in self.tables

    def get(self, name: str, default: Any = None) -> Any:
        return self.tables.get(name, default)

    def counts(self) -> Dict[str, int]:
        return {name: len(rows) for name, rows in self.tables.items()}

    def to_dataframes(self) -> Dict[str, pd.DataFrame]:
        return {name: to_dataframe(rows) for name, rows in self.tables.items()}

    @property
    def prefix(self) -> str:
        return f"{self.entity}_{self.entity_id}"

    # -- writing --------------------------------------------------------------

    def save(self, out_dir: Union[str, Path], fmt: str = "csv",
             prefix: Optional[str] = None) -> List[Path]:
        """Write one file per table plus ``<prefix>_manifest.json``. Returns the paths."""
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        prefix = prefix or self.prefix
        written: List[Path] = []
        for name, rows in self.tables.items():
            path = out_dir / f"{prefix}_{name}.{fmt}"
            write_records(rows, path, fmt=fmt)
            written.append(path)
        manifest = dict(self.meta)
        manifest["counts"] = self.counts()
        manifest["files"] = [p.name for p in written]
        manifest_path = write_json(manifest, out_dir / f"{prefix}_manifest.json")
        written.append(manifest_path)
        return written


# -- network helpers ------------------------------------------------------------

Edge = Union[Tuple[Any, Any], Sequence[Any], Mapping[str, Any]]


def edges_to_dataframe(edges: Iterable[Edge], columns: Tuple[str, str] = ("source", "target")) -> pd.DataFrame:
    rows = []
    for e in edges:
        if isinstance(e, Mapping):
            rows.append(dict(e))
        else:
            rows.append({columns[0]: e[0], columns[1]: e[1]})
    return pd.DataFrame(rows, columns=list(columns) if not rows else None)


def edgelist_to_graphml(edges: Iterable[Edge], path: Union[str, Path],
                        nodes: Optional[Mapping[Any, Mapping[str, Any]]] = None,
                        directed: bool = False) -> Path:
    """Write an edge list (and optional node attributes) as GraphML for Gephi."""
    import networkx as nx

    graph = nx.DiGraph() if directed else nx.Graph()
    for e in edges:
        if isinstance(e, Mapping):
            src, dst = e.get("source"), e.get("target")
            attrs = {k: v for k, v in e.items() if k not in ("source", "target")}
        else:
            src, dst = e[0], e[1]
            attrs = {}
        graph.add_edge(src, dst, **{k: _graphml_safe(v) for k, v in attrs.items()})
    for node_id, attrs in (nodes or {}).items():
        graph.add_node(node_id, **{k: _graphml_safe(v) for k, v in attrs.items()})
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(graph, str(path))
    return path


def _graphml_safe(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return value
    return json.dumps(value, ensure_ascii=False, default=str)
