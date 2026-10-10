"""Canonical schema shared by the whole team. Do not duplicate or rename fields."""
from datetime import date, datetime
from enum import Enum
from typing import Literal, Optional
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_validator


class BusPreference(str, Enum):
    sleeper = "sleeper"
    seater = "seater"
    any = "any"


class AcPreference(str, Enum):
    required = "required"
    preferred = "preferred"
    non_ac = "non_ac"
    no_preference = "no_preference"


class Priority(str, Enum):
    cheapest = "cheapest"
    fastest = "fastest"
    comfort = "comfort"
    balanced = "balanced"


class ParseTripRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    timezone: str = "Asia/Kolkata"
    reference_date: Optional[date] = None

    @field_validator("message")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("message must not be blank")
        return v

    @field_validator("timezone")
    @classmethod
    def valid_tz(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except Exception:
            raise ValueError("timezone must be a valid IANA name")
        return v


class TripRequest(BaseModel):
    origin: str = Field(min_length=1)
    destination: str = Field(min_length=1)
    departure_date: date
    arrival_deadline: datetime
    timezone: str = "Asia/Kolkata"
    passengers: int = Field(default=1, ge=1, le=10)
    budget_inr: Optional[float] = Field(default=None, gt=0, le=100000)
    bus_preference: BusPreference = BusPreference.any
    ac_preference: AcPreference = AcPreference.no_preference
    has_luggage: bool = False
    priority: Priority = Priority.balanced

    @field_validator("arrival_deadline")
    @classmethod
    def tz_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("arrival_deadline must be timezone-aware")
        return v


class ParseTripResponse(BaseModel):
    status: Literal["ready", "needs_clarification", "error"]
    trip_request: Optional[TripRequest] = None
    partial_trip_request: Optional[dict] = None
    missing_fields: list[str] = []
    clarification_questions: list[str] = []
    error_code: Optional[str] = None
    fallback: Optional[str] = None  # "manual_entry" or "mock_parser"
