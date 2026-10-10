"""Read-only endpoints for RailRadar station lookup and train search."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.railradar.client import RailRadarClient

router = APIRouter(prefix="/api/rail", tags=["live rail data"])
class RailStation(BaseModel):
    code: str
    name: str
    city: str | None = None


class RailTrain(BaseModel):
    number: str
    name: str
    train_type: str | None = None
    departure: str | None = None
    arrival: str | None = None
    departure_day: int | None = None
    arrival_day: int | None = None
    duration_minutes: int | None = None
    delay_minutes: int | None = None
    live_status: str | None = None


class TrainSearchResponse(BaseModel):
    source: str = "RailRadar"
    data_kind: str = "live rail timetable; live status when available"
    fare_available: bool = False
    seat_inventory_available: bool = False
    booking_available: bool = False
    origin: RailStation
    destination: RailStation
    travel_date: date
    trains: list[RailTrain]


@router.get("/stations", response_model=list[RailStation])
def stations(q: str = Query(min_length=2, max_length=80), limit: int = Query(default=10, ge=5, le=50)):
    return RailRadarClient().search_stations(q.strip(), limit)


@router.get("/trains", response_model=TrainSearchResponse)
def trains(
    from_station: str = Query(pattern=r"^[A-Za-z0-9]{2,6}$"),
    to_station: str = Query(pattern=r"^[A-Za-z0-9]{2,6}$"),
    travel_date: date = Query(),
):
    origin, destination = from_station.upper(), to_station.upper()
    if origin == destination:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail="Choose two different stations.")

    data = RailRadarClient().trains_between(origin, destination, travel_date.isoformat(), live=True)
    raw_trains = data.get("trains", [])
    mapped = []
    for item in raw_trains if isinstance(raw_trains, list) else []:
        train = item.get("train") or {}
        from_info = item.get("from") or {}
        to_info = item.get("to") or {}
        live_info = item.get("live") or {}
        mapped.append(RailTrain(
            number=str(train.get("number") or ""),
            name=str(train.get("name") or "Train"),
            train_type=train.get("type"),
            departure=from_info.get("departure"),
            arrival=to_info.get("arrival"),
            departure_day=from_info.get("day"),
            arrival_day=to_info.get("day"),
            duration_minutes=item.get("duration"),
            delay_minutes=live_info.get("delayMinutes"),
            live_status=live_info.get("type"),
        ))

    from_info, to_info = data.get("from") or {}, data.get("to") or {}
    return TrainSearchResponse(
        origin=RailStation(code=origin, name=from_info.get("name") or origin),
        destination=RailStation(code=destination, name=to_info.get("name") or destination),
        travel_date=travel_date,
        trains=mapped,
    )
