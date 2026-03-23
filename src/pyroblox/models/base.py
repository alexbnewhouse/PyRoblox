"""Base model configuration for all Roblox API response models."""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class RobloxModel(BaseModel):
    """Base for all Roblox API response models.

    Uses ``extra="allow"`` so that new fields added by Roblox are captured
    in ``model_extra`` rather than causing validation errors.

    Uses camelCase alias generator since the Roblox API returns camelCase keys.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
        alias_generator=to_camel,
    )
