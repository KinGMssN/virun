"""TripRequest — the planner's input.

!! Align this file with the team's canonical TripRequest (Hour 0-1 contract). !!
Unknown fields (for example a `total_fare_inr` sent by the frontend) are IGNORED.
"""
from __future__ import annotations

from datetime import date, datetime, time
from typing import Literal, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Priority = Literal["cheapest", "fastest", "lowest_risk", "balanced"]
_PRIORITY_SYNONYMS = {
    "cheap": "cheapest",
    "lowest_cost": "cheapest",
    "fast": "fastest",
    "quickest": "fastest",
    "safest": "lowest_risk",
    "safe": "lowest_risk",
    "lowest-risk": "lowest_risk",
    "lowest risk": "lowest_risk",
}


class TripRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    origin: str = Field(min_length=1, max_length=120)
    destination: str = Field(min_length=1, max_length=120)
    departure_date: date
    arrival_deadline: datetime
    timezone: str = "Asia/Kolkata"
    passengers: int = Field(default=1, ge=1, le=6)
    budget_inr: Optional[int] = Field(
        default=None, ge=0, description="HARD limit on the TOTAL fare for all passengers"
    )
    bus_preference: Literal["sleeper", "seater", "any"] = "any"
    ac_preference: Literal["required", "preferred", "none"] = "none"
    has_luggage: bool = False
    priority: Priority = "balanced"

    @field_validator("origin", "destination", mode="before")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("priority", mode="before")
    @classmethod
    def _normalise_priority(cls, v):
        if isinstance(v, str):
            key = v.strip().lower()
            return _PRIORITY_SYNONYMS.get(key, key)
        return v

    @field_validator("timezone")
    @classmethod
    def _valid_timezone(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"unknown timezone '{v}'") from exc
        return v

    @field_validator("arrival_deadline")
    @classmethod
    def _deadline_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.utcoffset() is None:
            raise ValueError("arrival_deadline must include a UTC offset, e.g. +05:30")
        return v

    @model_validator(mode="after")
    def _deadline_after_departure_day(self) -> "TripRequest":
        if self.arrival_deadline <= self.earliest_departure:
            raise ValueError("arrival_deadline must be after the start of departure_date")
        return self

    @property
    def tzinfo(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    @property
    def earliest_departure(self) -> datetime:
        """00:00 of departure_date in the request timezone. The first leg may not depart earlier."""
        return datetime.combine(self.departure_date, time.min, tzinfo=self.tzinfo)
