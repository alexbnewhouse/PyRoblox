import json
from pathlib import Path

import pytest

from robloxwrapper.config import RobloxConfig, load_config


def test_defaults():
    cfg = RobloxConfig()
    assert cfg.cookie is None
    assert cfg.output_dir == Path("roblox_data")
    assert cfg.rate == 1.0 and cfg.burst == 5
    assert cfg.resolve_cookie() is None


def test_from_env_coerces_types(tmp_path):
    env = {
        "ROBLOX_COOKIE": "abc",
        "ROBLOX_OUTPUT_DIR": str(tmp_path / "out"),
        "ROBLOX_RATE": "0.5",
        "ROBLOX_BURST": "2",
        "ROBLOX_MAX_RETRIES": "1",
        "ROBLOX_TIMEOUT": "9",
        "ROBLOX_LOG_LEVEL": "debug",
        "UNRELATED": "x",
    }
    cfg = RobloxConfig.from_env(env)
    assert cfg.cookie == "abc"
    assert cfg.output_dir == tmp_path / "out"
    assert cfg.rate == 0.5 and cfg.burst == 2 and cfg.max_retries == 1
    assert cfg.timeout == 9.0
    assert cfg.log_level == "debug"


def test_from_yaml_and_json_files(tmp_path):
    yaml_path = tmp_path / "c.yaml"
    yaml_path.write_text("rate: 2\noutput_dir: data\ncookie: fromyaml\n")
    cfg = RobloxConfig.from_file(yaml_path)
    assert cfg.rate == 2.0 and cfg.output_dir == Path("data") and cfg.cookie == "fromyaml"

    json_path = tmp_path / "c.json"
    json_path.write_text(json.dumps({"burst": 9}))
    cfg = RobloxConfig.from_file(json_path)
    assert cfg.burst == 9 and cfg.rate == 1.0


def test_from_file_errors(tmp_path):
    with pytest.raises(FileNotFoundError):
        RobloxConfig.from_file(tmp_path / "missing.yaml")
    bad = tmp_path / "c.txt"
    bad.write_text("rate: 1")
    with pytest.raises(ValueError):
        RobloxConfig.from_file(bad)
    lst = tmp_path / "l.json"
    lst.write_text("[1,2]")
    with pytest.raises(ValueError):
        RobloxConfig.from_file(lst)


def test_precedence_flag_over_env_over_file(tmp_path):
    f = tmp_path / "c.yaml"
    f.write_text("rate: 3\nburst: 7\nlog_level: WARNING\n")
    env = {"ROBLOX_RATE": "2", "ROBLOX_BURST": "6"}
    cfg = load_config(f, env=env, rate=1.5)
    assert cfg.rate == 1.5        # flag wins
    assert cfg.burst == 6         # env beats file
    assert cfg.log_level == "WARNING"  # file beats default


def test_none_and_empty_overrides_are_ignored():
    cfg = load_config(env={}, rate=None, cookie="")
    assert cfg.rate == 1.0 and cfg.cookie is None


def test_cookie_file(tmp_path):
    cookie_path = tmp_path / "cookie.txt"
    cookie_path.write_text("  SECRETVALUE \n")
    cfg = RobloxConfig(cookie_file=cookie_path)
    assert cfg.resolve_cookie() == "SECRETVALUE"
    cfg = RobloxConfig(cookie="direct", cookie_file=cookie_path)
    assert cfg.resolve_cookie() == "direct"
    with pytest.raises(FileNotFoundError):
        RobloxConfig(cookie_file=tmp_path / "nope").resolve_cookie()


def test_make_client_passes_settings():
    cfg = RobloxConfig(cookie="c", rate=0.25, burst=3, max_retries=1, timeout=5)
    client = cfg.make_client(session=object())
    assert client.has_cookie
    assert client._max_retries == 1 and client._timeout == 5
    assert client._throttle._rate == 0.25 and client._throttle._burst == 3


def test_to_dict_redacts_cookie():
    cfg = RobloxConfig(cookie="secret", output_dir=Path("x"))
    d = cfg.to_dict()
    assert d["cookie"] == "***" and d["output_dir"] == "x"
    assert cfg.to_dict(redact=False)["cookie"] == "secret"
