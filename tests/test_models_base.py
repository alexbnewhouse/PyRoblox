"""Base-model behaviour every typed response relies on."""

from datetime import datetime, timezone
from typing import Optional

from pydantic import ValidationError
import pytest

from pyroblox.models.base import PascalModel, RobloxModel, RobloxRecord, to_record, to_records


class Thing(RobloxModel):
    id: int
    display_name: Optional[str] = None
    member_count: Optional[int] = None
    created: Optional[datetime] = None


class Legacy(PascalModel):
    asset_id: int
    name: Optional[str] = None


def test_camel_case_aliases_and_snake_case_access():
    t = Thing.model_validate({"id": 7, "displayName": "Roblox", "memberCount": 3})
    assert t.display_name == "Roblox" and t.member_count == 3
    assert Thing(id=1, display_name="x").display_name == "x"      # populate_by_name


def test_extra_fields_are_kept_and_reachable():
    t = Thing.model_validate({"id": 7, "communityTier": {"currentTier": 3}, "isLocked": True})
    assert t.model_extra == {"communityTier": {"currentTier": 3}, "isLocked": True}
    assert t.isLocked is True
    assert t.to_record()["communityTier"] == {"currentTier": 3}


def test_missing_required_field_raises():
    with pytest.raises(ValidationError):
        Thing.model_validate({"displayName": "no id"})


def test_to_record_uses_roblox_keys_and_iso_datetimes():
    raw = {"id": 261, "displayName": "Shed", "created": "2006-06-22T01:33:56.45Z"}
    t = Thing.model_validate(raw)
    assert t.created == datetime(2006, 6, 22, 1, 33, 56, 450000, tzinfo=timezone.utc)
    rec = t.to_record()
    assert rec["displayName"] == "Shed" and rec["created"] == "2006-06-22T01:33:56.450000Z"
    assert "display_name" not in rec


def test_to_record_recurses_and_passes_plain_values_through():
    t = Thing(id=1)
    assert to_record({"a": [t, {"b": t}], "c": 3}) == {"a": [t.to_record(), {"b": t.to_record()}], "c": 3}
    assert to_record(None) is None and to_record("x") == "x"
    assert to_records([t, {"raw": 1}]) == [t.to_record(), {"raw": 1}]
    assert to_records(None) == []


def test_to_record_omits_fields_roblox_did_not_send():
    t = Thing.model_validate({"id": 7, "displayName": "x", "bonus": 1})
    assert t.to_record() == {"id": 7, "displayName": "x", "bonus": 1}
    assert Thing(id=1).to_record() == {"id": 1}
    assert Thing(id=1, member_count=None).to_record() == {"id": 1, "memberCount": None}


def test_from_list_validates_each_item_and_tolerates_none():
    assert [x.id for x in Thing.from_list([{"id": 1}, {"id": 2}])] == [1, 2]
    assert Thing.from_list(None) == []


def test_pascal_model_for_economy_endpoints():
    m = Legacy.model_validate({"AssetId": 1028606, "Name": "Fedora", "PriceInRobux": 10})
    assert m.asset_id == 1028606 and m.name == "Fedora" and m.PriceInRobux == 10
    assert m.to_record()["AssetId"] == 1028606


def test_roblox_record_is_fully_dynamic():
    r = RobloxRecord.model_validate({"assetTypeId": 1, "approved": True})
    assert r.assetTypeId == 1 and r.to_record() == {"assetTypeId": 1, "approved": True}
