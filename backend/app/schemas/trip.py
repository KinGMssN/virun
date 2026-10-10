"""Canonical schema shared by the whole team. Do not duplicate or rename fields."""
from datetime import date, datetime
from enum import Enum
from typing import Literal, Optional
from uuid import UUID
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
    message: str = Field(min_length=1, max_length=1020)
    duration_days: Optional[int] = Field(default=None, ge=1, le=15)
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
    duration_days: int = Field(ge=1, le=15)
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


class ItineraryGenerationRequest(BaseModel):
    destination: str = Field(min_length=1, max_length=120)
    duration_days: int = Field(ge=1, le=15)
    duration_nights: Optional[int] = Field(default=None, ge=0, le=30)
    budget_inr: Optional[float] = Field(default=None, gt=0, le=10000000)
    preferences: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("destination")
    @classmethod
    def strip_destination(cls, value: str) -> str:
        return value.strip()


class DayPlan(BaseModel):
    day: int = Field(ge=1, le=15)
    title: str = Field(min_length=1, max_length=120)
    morning: str = Field(min_length=1, max_length=500)
    afternoon: str = Field(min_length=1, max_length=500)
    evening: str = Field(min_length=1, max_length=500)


class GeneratedItinerary(BaseModel):
    destination: str
    duration_days: int = Field(ge=1, le=15)
    days: list[DayPlan]
    itinerary_id: UUID | None = None
    saved_to_database: bool = False
    save_error: str | None = None

    @field_validator("days")
    @classmethod
    def validate_day_count(cls, days: list[DayPlan], info):
        expected = info.data.get("duration_days")
        if expected is not None and [day.day for day in days] != list(range(1, expected + 1)):
            raise ValueError("days must cover the requested trip duration in order")
        return days
