"""Configuration: where the cookie, output folder, and rate limits come from.

Settings are looked up in this order (first one wins):

1. explicit arguments / CLI flags
2. environment variables (``ROBLOX_COOKIE``, ``ROBLOX_OUTPUT_DIR``, ...)
3. a YAML or JSON config file (``--config settings.yaml``)
4. built-in defaults

Every setting has the same name everywhere. ``rate`` in the file is
``ROBLOX_RATE`` in the environment and ``--rate`` on the command line.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, fields, replace
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from .client import RobloxClient

ENV_PREFIX = "ROBLOX_"


@dataclass
class RobloxConfig:
    cookie: Optional[str] = None
    cookie_file: Optional[Path] = None
    output_dir: Path = field(default_factory=lambda: Path("roblox_data"))
    rate: float = 1.0
    burst: int = 5
    max_retries: int = 4
    timeout: float = 30.0
    log_level: str = "INFO"
    log_file: Optional[Path] = None

    # -- construction ---------------------------------------------------------

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any],
                     base: Optional["RobloxConfig"] = None) -> "RobloxConfig":
        """Overlay ``values`` (already using config-key names) onto ``base``."""
        cfg = base or cls()
        updates: Dict[str, Any] = {}
        known = {f.name: f for f in fields(cls)}
        for key, raw in values.items():
            if key not in known or raw is None or raw == "":
                continue
            updates[key] = _coerce(key, raw)
        return replace(cfg, **updates)

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None,
                 base: Optional["RobloxConfig"] = None) -> "RobloxConfig":
        env = os.environ if env is None else env
        values = {}
        for f in fields(cls):
            var = ENV_PREFIX + f.name.upper()
            if var in env:
                values[f.name] = env[var]
        return cls.from_mapping(values, base=base)

    @classmethod
    def from_file(cls, path: os.PathLike, base: Optional["RobloxConfig"] = None) -> "RobloxConfig":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"config file not found: {path}")
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() == ".json":
            data = json.loads(text) if text.strip() else {}
        elif path.suffix.lower() in (".yaml", ".yml"):
            import yaml  # local import keeps yaml optional at import time
            data = yaml.safe_load(text) or {}
        else:
            raise ValueError("config file must end in .yaml, .yml, or .json")
        if not isinstance(data, dict):
            raise ValueError("config file must contain a mapping of settings")
        return cls.from_mapping(data, base=base)

    # -- use ------------------------------------------------------------------

    def resolve_cookie(self) -> Optional[str]:
        """Return the cookie value: ``cookie`` first, then the contents of ``cookie_file``."""
        if self.cookie:
            return self.cookie.strip() or None
        if self.cookie_file:
            path = Path(self.cookie_file).expanduser()
            if not path.exists():
                raise FileNotFoundError(f"cookie file not found: {path}")
            return path.read_text(encoding="utf-8").strip() or None
        return None

    def make_client(self, **overrides: Any) -> RobloxClient:
        """Build a :class:`RobloxClient` from these settings."""
        kwargs: Dict[str, Any] = dict(rate=self.rate, burst=self.burst,
                                      max_retries=self.max_retries, timeout=self.timeout)
        kwargs.update(overrides)
        return RobloxClient(self.resolve_cookie(), **kwargs)

    def setup_logging(self) -> None:
        level = getattr(logging, str(self.log_level).upper(), logging.INFO)
        handlers: list = [logging.StreamHandler()]
        if self.log_file:
            Path(self.log_file).expanduser().parent.mkdir(parents=True, exist_ok=True)
            handlers.append(logging.FileHandler(Path(self.log_file).expanduser()))
        logging.basicConfig(level=level, handlers=handlers,
                            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                            force=True)

    def to_dict(self, redact: bool = True) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for f in fields(self):
            value = getattr(self, f.name)
            if isinstance(value, Path):
                value = str(value)
            if f.name == "cookie" and value and redact:
                value = "***"
            out[f.name] = value
        return out


def _coerce(key: str, raw: Any) -> Any:
    if key in ("cookie_file", "output_dir", "log_file"):
        return Path(str(raw)).expanduser()
    if key in ("rate", "timeout"):
        return float(raw)
    if key in ("burst", "max_retries"):
        return int(raw)
    return str(raw) if not isinstance(raw, str) else raw


def load_config(config_path: Optional[os.PathLike] = None,
                env: Optional[Mapping[str, str]] = None,
                **overrides: Any) -> RobloxConfig:
    """Assemble a config using the precedence documented at the top of this module."""
    cfg = RobloxConfig()
    if config_path:
        cfg = RobloxConfig.from_file(config_path, base=cfg)
    cfg = RobloxConfig.from_env(env, base=cfg)
    cfg = RobloxConfig.from_mapping(overrides, base=cfg)
    return cfg
