"""HTTP endpoints for the planner."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.planner.service import plan_trip
from app.repositories.transport_repository import TransportRepository, get_default_repository
from app.schemas.itinerary import (
    ERR_INVALID_REQUEST,
    ERR_NO_FEASIBLE_ROUTE,
    ERR_UNKNOWN_LOCATION,
    PlanResponse,
)
from app.schemas.transport import Stop, TransportOption
from app.schemas.trip_request import TripRequest

router = APIRouter(prefix="/api", tags=["planner"])

# HTTP status per error code. Change here if the team prefers different codes.
ERROR_STATUS = {
    ERR_NO_FEASIBLE_ROUTE: 404,
    ERR_INVALID_REQUEST: 422,
    ERR_UNKNOWN_LOCATION: 422,
}


def get_repository() -> TransportRepository:
    return get_default_repository()


class TransportOptionsResponse(BaseModel):
    count: int
    meta: dict[str, Any]
    stops: list[Stop]
    options: list[TransportOption]


class RecoverRequest(BaseModel):
    trip_request: TripRequest
    unavailable_leg_ids: list[str] = Field(
        default_factory=list,
        description="Option IDs to treat as cancelled/sold-out for replanning.",
    )


def _plan_result_to_response(result: PlanResponse):
    """Convert a PlanResponse into an HTTP response, mapping errors to 4xx."""
    if result.error is not None:
        return JSONResponse(
            status_code=ERROR_STATUS.get(result.error.code, 400),
            content={"error": result.error.model_dump(mode="json", exclude_none=True)},
        )
    return result


@router.post("/plan", response_model=PlanResponse, response_model_exclude={"error"})
def plan(request: TripRequest, repo: TransportRepository = Depends(get_repository)):
    """Plan a trip. Success: 200 + itineraries. Failure: {"error": {...}} with a 4xx status."""
    return _plan_result_to_response(plan_trip(request, repository=repo))


@router.post("/plan/recover", response_model=PlanResponse, response_model_exclude={"error"})
def recover(body: RecoverRequest, repo: TransportRepository = Depends(get_repository)):
    """Replan after disruption. Accepts the original trip request plus leg IDs to exclude."""
    return _plan_result_to_response(
        plan_trip(body.trip_request, unavailable_leg_ids=body.unavailable_leg_ids, repository=repo)
    )


@router.get("/transport/options", response_model=TransportOptionsResponse)
def transport_options(
    origin_stop_id: Optional[str] = Query(None),
    destination_stop_id: Optional[str] = Query(None),
    mode: Optional[str] = Query(None),
    repo: TransportRepository = Depends(get_repository),
):
    """Every transport record in the current dataset (including cancelled ones), with source labels."""
    options = repo.list_options()
    if origin_stop_id:
        options = [o for o in options if o.origin_stop_id == origin_stop_id]
    if destination_stop_id:
        options = [o for o in options if o.destination_stop_id == destination_stop_id]
    if mode:
        options = [o for o in options if o.mode == mode]
    options = sorted(options, key=lambda o: (o.departure_at, o.option_id))
    return TransportOptionsResponse(
        count=len(options), meta=repo.metadata(), stops=repo.list_stops(), options=options
    )
