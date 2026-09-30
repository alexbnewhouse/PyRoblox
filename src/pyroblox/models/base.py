"""Base classes for typed Roblox API responses.

Every API method returns an instance of a :class:`RobloxModel` subclass (or a
:class:`~pyroblox.client.PagedList` of them). Two rules make the models safe
against Roblox changing its responses:

* ``extra="allow"``: fields the model does not declare are kept, not rejected.
  They are reachable as attributes (``group.communityTier``) and via
  ``model.model_extra``.
* camelCase aliases: Roblox sends ``memberCount``; you read ``group.member_count``.
  Both spellings work when constructing a model.

:func:`to_record` turns any model (or nested structure of models) back into
plain JSON-compatible dicts with Roblox's original key names, which is what
the CSV exporter and the manifest use. Only fields Roblox sent are included.
Datetimes are rendered as ISO 8601 UTC strings (``2006-06-22T01:33:56.450000Z``),
which may differ textually from Roblox's own rendering but not in value.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Optional, TypeVar

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel, to_pascal

T = TypeVar("T", bound="RobloxModel")


class RobloxModel(BaseModel):
    """Base for camelCase Roblox responses (almost every endpoint)."""

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
        alias_generator=to_camel,
        ser_json_timedelta="iso8601",
    )

    def to_record(self) -> dict[str, Any]:
        """Plain dict with Roblox's own key names and JSON-compatible values.

        Only fields Roblox actually sent (plus any extras) are included, so a
        record has the same keys as the raw response and CSV headers do not
        grow empty columns for fields a given endpoint never returns.
        """
        return self.model_dump(by_alias=True, mode="json", exclude_unset=True)

    @classmethod
    def from_list(cls: type[T], items: Optional[Iterable[Any]]) -> list[T]:
        """Validate every item of an API ``data`` list."""
        return [cls.model_validate(item) for item in (items or [])]


class PascalModel(RobloxModel):
    """Base for the few legacy endpoints that answer in PascalCase
    (``economy.roblox.com`` asset details: ``AssetId``, ``Name``...)."""

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
        alias_generator=to_pascal,
    )


class RobloxRecord(RobloxModel):
    """A model with no declared fields: every key Roblox sends is an extra.

    Used for endpoints whose shape is loosely specified or rarely needed in
    typed form (guest permissions, media entries, place details). Attribute
    access uses Roblox's spelling: ``record.assetTypeId``.
    """


def to_record(value: Any) -> Any:
    """Convert models (and lists/dicts containing them) into plain JSON values.

    Plain dicts, lists, and scalars pass through unchanged, so callers can
    accept either raw JSON or models without caring which they got.
    """
    if isinstance(value, BaseModel):
        return value.model_dump(by_alias=True, mode="json", exclude_unset=True)
    if isinstance(value, dict):
        return {k: to_record(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_record(v) for v in value]
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def to_records(values: Optional[Iterable[Any]]) -> list[dict[str, Any]]:
    """Convert an iterable of models/dicts into a list of plain dicts."""
    return [to_record(v) for v in (values or [])]
