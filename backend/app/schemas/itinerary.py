"""Response schemas returned by POST /api/plan and plan_trip()."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

RiskLevel = Literal["low", "medium", "high"]

# Error codes (shared by service + router)
ERR_NO_FEASIBLE_ROUTE = "NO_FEASIBLE_ROUTE"
ERR_INVALID_REQUEST = "INVALID_REQUEST"
ERR_UNKNOWN_LOCATION = "UNKNOWN_LOCATION"


class ItineraryLeg(BaseModel):
    leg_number: int
    option_id: str
    origin_stop_id: str
    destination_stop_id: str
    origin_name: Optional[str] = None
    destination_name: Optional[str] = None
    mode: str
    operator: Optional[str] = None
    departure_at: datetime
    arrival_at: datetime
    duration_minutes: int
    wait_before_minutes: Optional[int] = Field(
        default=None, description="Transfer wait before this leg (null for the first leg)"
    )
    fare_per_passenger_inr: int
    luggage_fee_per_passenger_inr: int = Field(description="Only non-zero when has_luggage is true")
    leg_total_inr: int = Field(description="(fare + luggage fee) x passengers")
    seat_type: Optional[str] = None
    ac: Optional[bool] = None
    reliability_score: float
    origin_lat: Optional[float] = None
    origin_lng: Optional[float] = None
    destination_lat: Optional[float] = None
    destination_lng: Optional[float] = None
    data_source: str


class Itinerary(BaseModel):
    itinerary_id: str
    route_key: str = Field(description="Stable key: option IDs joined by '+'")
    label: str
    labels: list[str]
    legs: list[ItineraryLeg]
    passengers: int
    fare_per_passenger_inr: int
    total_fare_inr: int
    departure_at: datetime
    arrival_at: datetime
    duration_minutes: int
    arrival_buffer_minutes: int
    transfer_count: int
    risk_level: RiskLevel
    risk_score: float
    balanced_score: float
    feasible: bool = True
    data_source: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Optional[dict[str, Any] | list[Any]] = None


class PlanResponse(BaseModel):
    itineraries: list[Itinerary] = Field(default_factory=list)
    error: Optional[ErrorBody] = None
    unavailable_leg_ids: list[str] = Field(default_factory=list)
    candidates_evaluated: int = 0
    candidates_feasible: int = 0
