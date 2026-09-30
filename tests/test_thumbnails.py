"""Tests for pyroblox.thumbnails (thumbnails.roblox.com + rbxcdn downloads).
No network."""

import hashlib
import logging
import os

import pytest
from pydantic import ValidationError

from pyroblox.models.thumbnails import SavedThumbnail, Thumbnail
from pyroblox.thumbnails import KINDS, ThumbnailsAPI
from tests.conftest import FakeResponse, make_client

BASE = "https://thumbnails.roblox.com"
CDN = "https://tr.rbxcdn.com"

HEADSHOT = {
    "targetId": 261, "state": "Completed",
    "imageUrl": f"{CDN}/30DAY-AvatarHeadshot-3B3B81F4602EE5424673376A726F427E-Png/150/150/AvatarHeadshot/Png/noFilter",
    "version": "TN3",
}
GROUP_ICON = {
    "targetId": 7, "state": "Completed",
    "imageUrl": f"{CDN}/180DAY-dd8f9bac6a0aea7a85478428ab845d87/150/150/Image/Png/noFilter",
    "version": "TN3",
}


def test_client_exposes_thumbnails_api():
    client, _, _ = make_client(routes={})
    assert isinstance(client.thumbnails, ThumbnailsAPI)
    assert client.thumbnails.client is client
    assert ThumbnailsAPI.BASE == BASE


def test_kinds_table():
    assert KINDS == {
        "user-headshot": ("users/avatar-headshot", "userIds"),
        "user-avatar": ("users/avatar", "userIds"),
        "user-bust": ("users/avatar-bust", "userIds"),
        "group-icon": ("groups/icons", "groupIds"),
        "game-icon": ("games/icons", "universeIds"),
        "game-thumbnail": ("games/multiget/thumbnails", "universeIds"),
        "place-icon": ("places/gameicons", "placeIds"),
        "asset": ("assets", "assetIds"),
        "badge-icon": ("badges/icons", "badgeIds"),
        "bundle": ("bundles/thumbnails", "bundleIds"),
    }


# -- models -------------------------------------------------------------------

def test_thumbnail_model_validates_probe_payload():
    raw = dict(HEADSHOT, cdnHint="edge-1")          # an undeclared field Roblox might add
    thumb = Thumbnail.model_validate(raw)
    assert thumb.target_id == 261
    assert thumb.state == "Completed"
    assert thumb.image_url == HEADSHOT["imageUrl"]
    assert thumb.version == "TN3"
    assert thumb.universe_id is None and thumb.thumbnail_target_id is None
    assert thumb.model_extra == {"cdnHint": "edge-1"}
    assert thumb.cdnHint == "edge-1"
    rec = thumb.to_record()
    assert rec["targetId"] == 261 and rec["imageUrl"] == HEADSHOT["imageUrl"]
    assert rec["cdnHint"] == "edge-1"
    assert "target_id" not in rec and "image_url" not in rec


def test_thumbnail_model_accepts_pending_state_with_null_url():
    thumb = Thumbnail.model_validate({"targetId": 12, "state": "Pending",
                                      "imageUrl": None, "version": "TN3"})
    assert thumb.state == "Pending" and thumb.image_url is None


def test_saved_thumbnail_model_round_trips_camel_case():
    rec = SavedThumbnail(kind="user-headshot", target_id=261, url=f"{CDN}/a.png",
                         path="/tmp/user-headshot_261.png", sha256="ab" * 32)
    assert rec.target_id == 261 and rec.kind == "user-headshot"
    assert rec.to_record() == {"kind": "user-headshot", "targetId": 261, "url": f"{CDN}/a.png",
                               "path": "/tmp/user-headshot_261.png", "sha256": "ab" * 32}
    assert SavedThumbnail.model_validate(rec.to_record()) == rec


def test_saved_thumbnail_missing_required_field_raises_validation_error():
    with pytest.raises(ValidationError):
        SavedThumbnail(target_id=261, url=f"{CDN}/a.png", path="/tmp/x.png")   # no kind/sha256


# -- get_thumbnails -----------------------------------------------------------

def test_get_thumbnails_sends_ids_size_format_and_unwraps_data():
    client, session, _ = make_client(routes={
        f"GET {BASE}/v1/users/avatar-headshot": {"data": [HEADSHOT]},
    })
    out = client.thumbnails.get_thumbnails("user-headshot", [261])
    assert type(out) is list and len(out) == 1
    assert isinstance(out[0], Thumbnail)
    assert out[0].target_id == 261 and out[0].state == "Completed"
    assert out[0].image_url == HEADSHOT["imageUrl"] and out[0].version == "TN3"
    call = session.calls[0]
    assert call.method == "GET"
    assert call.params == {"userIds": "261", "size": "420x420", "format": "Png"}


def test_get_thumbnails_joins_ids_and_passes_size_and_format():
    client, session, _ = make_client(routes={
        f"GET {BASE}/v1/groups/icons": {"data": [GROUP_ICON, dict(GROUP_ICON, targetId=8)]},
    })
    out = client.thumbnails.get_thumbnails("group-icon", [7, 8], size="150x150", fmt="Webp")
    assert [r.target_id for r in out] == [7, 8]
    assert session.calls[0].params == {"groupIds": "7,8", "size": "150x150", "format": "Webp"}


@pytest.mark.parametrize("kind,path,key", [(k, v[0], v[1]) for k, v in KINDS.items()
                                           if k != "game-thumbnail"])
def test_get_thumbnails_maps_every_kind_to_its_path_and_id_key(kind, path, key):
    client, session, _ = make_client(routes={
        f"GET {BASE}/v1/{path}": {"data": [{"targetId": 5, "state": "Completed",
                                            "imageUrl": f"{CDN}/x", "version": "TN3"}]},
    })
    out = client.thumbnails.get_thumbnails(kind, [5])
    assert out[0].target_id == 5
    assert session.calls[0].url == f"{BASE}/v1/{path}"
    assert session.calls[0].params[key] == "5"


def test_get_thumbnails_chunks_150_ids_into_two_calls():
    ids = list(range(1, 151))
    client, session, _ = make_client([
        FakeResponse(200, {"data": [dict(HEADSHOT, targetId=i) for i in ids[:100]]}),
        FakeResponse(200, {"data": [dict(HEADSHOT, targetId=i) for i in ids[100:]]}),
    ])
    out = client.thumbnails.get_thumbnails("user-headshot", ids)
    assert len(session.calls) == 2
    assert session.calls[0].url == f"{BASE}/v1/users/avatar-headshot"
    assert session.calls[0].params["userIds"] == ",".join(map(str, ids[:100]))
    assert session.calls[1].params["userIds"] == ",".join(map(str, ids[100:]))
    assert [r.target_id for r in out] == ids


def test_get_thumbnails_with_no_ids_makes_no_request():
    client, session, _ = make_client(routes={})
    assert client.thumbnails.get_thumbnails("user-headshot", []) == []
    assert session.calls == []


def test_get_thumbnails_game_thumbnail_flattens_one_record_per_thumbnail():
    body = {"data": [
        {"universeId": 994732206, "error": None, "thumbnails": [
            {"targetId": 10, "state": "Completed", "imageUrl": f"{CDN}/a", "version": "TN3"},
            {"targetId": 11, "state": "Completed", "imageUrl": f"{CDN}/b", "version": "TN3"},
        ]},
        {"universeId": 13058, "error": None, "thumbnails": [
            {"targetId": 12, "state": "Pending", "imageUrl": None, "version": "TN3"},
        ]},
        {"universeId": 999, "error": {"code": 1, "message": "bad"}, "thumbnails": None},
    ]}
    client, session, _ = make_client(routes={f"GET {BASE}/v1/games/multiget/thumbnails": body})
    out = client.thumbnails.get_thumbnails("game-thumbnail", [994732206, 13058, 999])
    assert session.calls[0].params == {"universeIds": "994732206,13058,999",
                                       "size": "420x420", "format": "Png"}
    assert [(r.target_id, r.state, r.image_url) for r in out] == [
        (994732206, "Completed", f"{CDN}/a"),
        (994732206, "Completed", f"{CDN}/b"),
        (13058, "Pending", None),
    ]
    assert all(r.universe_id == r.target_id for r in out)
    # the thumbnail's own id is preserved rather than silently dropped
    assert [r.thumbnail_target_id for r in out] == [10, 11, 12]
    rec = out[0].to_record()
    assert rec["universeId"] == 994732206 and rec["thumbnailTargetId"] == 10


def test_get_thumbnails_unknown_kind_raises_value_error_listing_kinds():
    client, session, _ = make_client(routes={})
    with pytest.raises(ValueError) as exc:
        client.thumbnails.get_thumbnails("user-face", [261])
    msg = str(exc.value)
    assert "user-face" in msg
    for kind in KINDS:
        assert kind in msg
    assert session.calls == []


def test_old_method_names_are_gone():
    for name in ("get", "user_headshots", "user_avatars", "group_icons", "game_icons",
                 "asset_thumbnails", "badge_icons"):
        assert not hasattr(ThumbnailsAPI, name)


# -- convenience wrappers -----------------------------------------------------

@pytest.mark.parametrize("method,kind,default_size", [
    ("get_user_headshots", "user-headshot", "150x150"),
    ("get_user_avatars", "user-avatar", "420x420"),
    ("get_group_icons", "group-icon", "150x150"),
    ("get_game_icons", "game-icon", "150x150"),
    ("get_asset_thumbnails", "asset", "150x150"),
    ("get_badge_icons", "badge-icon", "150x150"),
])
def test_wrappers_call_get_thumbnails_with_kind_and_default_size(method, kind, default_size):
    path, key = KINDS[kind]
    client, session, _ = make_client(routes={
        f"GET {BASE}/v1/{path}": {"data": [{"targetId": 1, "state": "Completed",
                                            "imageUrl": f"{CDN}/x", "version": "TN3"}]},
    })
    out = getattr(client.thumbnails, method)([1])
    assert len(out) == 1 and isinstance(out[0], Thumbnail)
    assert (out[0].target_id, out[0].state, out[0].image_url, out[0].version) == \
        (1, "Completed", f"{CDN}/x", "TN3")
    assert session.calls[0].params == {key: "1", "size": default_size, "format": "Png"}
    getattr(client.thumbnails, method)([1], size="720x720")
    assert session.calls[1].params["size"] == "720x720"


# -- download -----------------------------------------------------------------

def test_download_returns_bytes_via_client():
    client, session, _ = make_client([FakeResponse(200, content=b"\x89PNG")])
    assert client.thumbnails.download(f"{CDN}/img.png") == b"\x89PNG"
    call = session.calls[0]
    assert call.method == "GET" and call.url == f"{CDN}/img.png"
    assert "Accept" not in call.headers


# -- save ---------------------------------------------------------------------

def _thumb(target_id, state="Completed", url=None):
    return {"targetId": target_id, "state": state, "imageUrl": url, "version": "TN3"}


def test_save_downloads_completed_thumbnails_and_writes_png_files(tmp_path):
    out_dir = tmp_path / "thumbs"          # does not exist yet; save must create it
    client, session, _ = make_client(routes={
        f"GET {BASE}/v1/users/avatar-headshot":
            {"data": [_thumb(261, url=f"{CDN}/a.png"), _thumb(1, url=f"{CDN}/b.png")]},
        f"GET {CDN}/a.png": FakeResponse(200, content=b"PNG-A"),
        f"GET {CDN}/b.png": FakeResponse(200, content=b"PNG-B"),
    })
    records = client.thumbnails.save("user-headshot", [261, 1], out_dir)
    assert session.calls[0].params == {"userIds": "261,1", "size": "420x420", "format": "Png"}
    assert [c.url for c in session.calls[1:]] == [f"{CDN}/a.png", f"{CDN}/b.png"]
    assert all(isinstance(r, SavedThumbnail) for r in records)
    assert records[0].kind == "user-headshot" and records[0].target_id == 261
    assert records[0].path == str(out_dir / "user-headshot_261.png")
    assert [r.to_record() for r in records] == [
        {"kind": "user-headshot", "targetId": 261, "url": f"{CDN}/a.png",
         "path": str(out_dir / "user-headshot_261.png"),
         "sha256": hashlib.sha256(b"PNG-A").hexdigest()},
        {"kind": "user-headshot", "targetId": 1, "url": f"{CDN}/b.png",
         "path": str(out_dir / "user-headshot_1.png"),
         "sha256": hashlib.sha256(b"PNG-B").hexdigest()},
    ]
    assert (out_dir / "user-headshot_261.png").read_bytes() == b"PNG-A"
    assert (out_dir / "user-headshot_1.png").read_bytes() == b"PNG-B"
    assert sorted(os.listdir(out_dir)) == ["user-headshot_1.png", "user-headshot_261.png"]


def test_save_passes_size_through_to_get_thumbnails(tmp_path):
    client, session, _ = make_client(routes={
        f"GET {BASE}/v1/groups/icons": {"data": []},
    })
    assert client.thumbnails.save("group-icon", [7], tmp_path, size="150x150") == []
    assert session.calls[0].params == {"groupIds": "7", "size": "150x150", "format": "Png"}


def test_save_skips_non_completed_states(tmp_path):
    client, session, _ = make_client(routes={
        f"GET {BASE}/v1/users/avatar-headshot": {"data": [
            _thumb(1, state="Pending"), _thumb(2, state="Blocked"),
            _thumb(3, url=f"{CDN}/c.png"),
        ]},
        f"GET {CDN}/c.png": FakeResponse(200, content=b"C"),
    })
    records = client.thumbnails.save("user-headshot", [1, 2, 3], tmp_path)
    assert [r.target_id for r in records] == [3]
    assert [c.url for c in session.calls[1:]] == [f"{CDN}/c.png"]
    assert sorted(os.listdir(tmp_path)) == ["user-headshot_3.png"]


def test_save_skips_files_that_already_exist(tmp_path):
    existing = tmp_path / "user-headshot_261.png"
    existing.write_bytes(b"OLD")
    client, session, _ = make_client(routes={
        f"GET {BASE}/v1/users/avatar-headshot":
            {"data": [_thumb(261, url=f"{CDN}/a.png"), _thumb(1, url=f"{CDN}/b.png")]},
        f"GET {CDN}/b.png": FakeResponse(200, content=b"B"),
    })
    records = client.thumbnails.save("user-headshot", [261, 1], tmp_path)
    assert [c.url for c in session.calls[1:]] == [f"{CDN}/b.png"]   # a.png never fetched
    assert existing.read_bytes() == b"OLD"
    assert [r.target_id for r in records] == [261, 1]
    assert records[0].path == str(existing)
    assert records[0].sha256 == hashlib.sha256(b"OLD").hexdigest()


def test_save_swallows_not_found_and_private_on_download(tmp_path, caplog):
    client, session, _ = make_client(routes={
        f"GET {BASE}/v1/users/avatar-headshot": {"data": [
            _thumb(1, url=f"{CDN}/gone.png"), _thumb(2, url=f"{CDN}/hidden.png"),
            _thumb(3, url=f"{CDN}/ok.png"),
        ]},
        f"GET {CDN}/gone.png": FakeResponse(404),
        f"GET {CDN}/hidden.png": FakeResponse(403),
        f"GET {CDN}/ok.png": FakeResponse(200, content=b"OK"),
    })
    with caplog.at_level(logging.INFO, logger="pyroblox"):
        records = client.thumbnails.save("user-headshot", [1, 2, 3], tmp_path)
    assert [r.target_id for r in records] == [3]
    assert sorted(os.listdir(tmp_path)) == ["user-headshot_3.png"]
    infos = [r for r in caplog.records if r.levelno == logging.INFO]
    assert len(infos) == 2
    assert any("gone.png" in r.getMessage() for r in infos)
    assert any("hidden.png" in r.getMessage() for r in infos)


def test_save_leaves_no_tmp_files_behind(tmp_path):
    client, _, _ = make_client(routes={
        f"GET {BASE}/v1/users/avatar-headshot": {"data": [_thumb(1, url=f"{CDN}/a.png")]},
        f"GET {CDN}/a.png": FakeResponse(200, content=b"A"),
    })
    client.thumbnails.save("user-headshot", [1], str(tmp_path))
    assert os.listdir(tmp_path) == ["user-headshot_1.png"]
