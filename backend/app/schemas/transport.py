"""Transport stop / option schemas (the shape of a single leg in the dataset)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TransportMode = Literal["bus", "train", "metro", "flight", "cab"]
LegStatus = Literal["available_in_demo", "available", "cancelled", "sold_out"]
SeatType = Literal["sleeper", "seater"]

# Only these statuses may be used in a journey. Everything else is excluded.
AVAILABLE_STATUSES = frozenset({"available_in_demo", "available"})

# Used when a record has no reliability information.
DEFAULT_RELIABILITY = 0.90


class Stop(BaseModel):
    """A place where legs start/end. `stop_id` is what connects legs together."""

    model_config = ConfigDict(extra="ignore")

    stop_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    city: Optional[str] = None
    aliases: list[str] = Field(default_factory=list)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    data_source: str = Field(min_length=1)

    @field_validator("aliases", mode="before")
    @classmethod
    def _none_to_empty(cls, v):
        return [] if v is None else v


class TransportOption(BaseModel):
    """One bookable leg. Timestamps MUST be timezone-aware."""

    model_config = ConfigDict(extra="ignore")

    option_id: str = Field(min_length=1)
    origin_stop_id: str = Field(min_length=1)
    destination_stop_id: str = Field(min_length=1)
    mode: TransportMode
    departure_at: datetime
    arrival_at: datetime
    fare_inr: int = Field(ge=0, description="Fare for ONE passenger, in INR")
    luggage_fee_inr: int = Field(
        default=0, ge=0, description="Extra per-passenger fee charged when the traveller has luggage"
    )
    status: LegStatus
    data_source: str = Field(min_length=1, description="e.g. SIMULATED")

    operator: Optional[str] = None
    seat_type: Optional[SeatType] = None
    ac: Optional[bool] = None
    reliability_score: float = Field(default=DEFAULT_RELIABILITY, ge=0.0, le=1.0)

    origin_lat: Optional[float] = None
    origin_lng: Optional[float] = None
    destination_lat: Optional[float] = None
    destination_lng: Optional[float] = None

    @model_validator(mode="after")
    def _validate_times(self) -> "TransportOption":
        for name in ("departure_at", "arrival_at"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware (e.g. +05:30)")
        if self.arrival_at <= self.departure_at:
            raise ValueError("arrival_at must be after departure_at")
        if self.origin_stop_id == self.destination_stop_id:
            raise ValueError("origin_stop_id and destination_stop_id must differ")
        return self

    @property
    def duration_minutes(self) -> int:
        return int((self.arrival_at - self.departure_at).total_seconds() // 60)
