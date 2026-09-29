"""Request schema, generated to match the model card's contract. Rejects, never extrapolates."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Event(BaseModel):
    model_config = ConfigDict(extra="forbid")  # CONTROL: unknown fields are rejected, not ignored
    hour_of_day: int = Field(ge=0, le=23)
    failed_attempts_24h: int = Field(ge=0)
    distinct_ips_24h: int = Field(ge=1)
    country_changed: int = Field(ge=0, le=1)
    is_vpn_exit: int = Field(ge=0, le=1)
    device_is_new: int = Field(ge=0, le=1)
    mfa_used: int = Field(ge=0, le=1)
    session_minutes: int = Field(ge=1)
    privileged_action: int = Field(ge=0, le=1)
    bytes_downloaded_mb: float = Field(ge=0)
    department: Literal["finance", "engineering", "support", "sales", "hr", "operations"]


FEATURES = list(Event.model_fields.keys())
