import os
import logging

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException

from app.concierge.model_adapter import MockAdapter, ModelError, get_adapter
from app.concierge.agent_service import plan_trip, run_agent
from app.concierge.itinerary_service import generate_itinerary
from app.concierge.places_service import find_nearby_places
from app.concierge.service import run_parse
from app.db.session import DatabaseNotConfigured, save_generated_itinerary
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.trip import (
    GeneratedItinerary,
    ItineraryGenerationRequest,
    ParseTripRequest,
    ParseTripResponse,
)

load_dotenv()
router = APIRouter(prefix="/api")
log = logging.getLogger("concierge")

FALLBACK_CODES = {"QUOTA_EXCEEDED", "MODEL_TIMEOUT", "MODEL_ERROR"}

@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        adapter = get_adapter()
        if not hasattr(adapter, "chat"):
            raise ModelError("NOT_CONFIGURED")
        reply = run_agent(
            adapter,
            [turn.model_dump() for turn in req.history],
            req.message,
        )
        return ChatResponse(reply=reply)
    except ModelError as exc:
        log.warning("chat model error code=%s", exc.code)
        status_code = 503 if exc.code == "NOT_CONFIGURED" else 502
        raise HTTPException(
            status_code=status_code,
            detail={
                "code": exc.code,
                "message": "Virun chat is temporarily unavailable. Check the Groq configuration and retry.",
            },
        ) from exc


@router.post("/parse-trip", response_model=ParseTripResponse)
def parse_trip(req: ParseTripRequest):
    try:
        adapter = get_adapter()
    except ModelError as e:
        return ParseTripResponse(status="error", error_code=e.code, fallback="manual_entry")

    res = run_parse(req, adapter)

    if (
        res.status == "error"
        and res.error_code in FALLBACK_CODES
        and os.getenv("ENABLE_MOCK_FALLBACK", "false").lower() == "true"
    ):
        mock = run_parse(req, MockAdapter())
        if mock.status != "error":
            mock.fallback = "mock_parser"
            return mock
    return res


@router.post("/generate-itinerary", response_model=GeneratedItinerary)
def generate_trip_itinerary(req: ItineraryGenerationRequest):
    try:
        adapter = get_adapter()
        real_places = find_nearby_places(req.destination)
        if hasattr(adapter, "chat_with_tools"):
            itinerary = plan_trip(adapter, req, real_places)
        else:
            itinerary = generate_itinerary(req, adapter, real_places)
    except ModelError as exc:
        log.warning("itinerary generation error code=%s", exc.code)
        status_code = 503 if exc.code == "NOT_CONFIGURED" else 502
        message = {
            "NOT_CONFIGURED": "AI itinerary generation is unavailable. Check the Groq configuration and retry.",
        }.get(
            exc.code,
            "AI itinerary generation is unavailable. Check the Groq configuration and retry.",
        )
        raise HTTPException(
            status_code=status_code,
            detail={
                "code": exc.code,
                "message": f"{message} (error code: {exc.code})" + (f" Details: {exc.detail}" if exc.detail else ""),
            },
        ) from exc
    try:
        itinerary.itinerary_id = save_generated_itinerary(
            plan=itinerary,
            duration_nights=req.duration_nights,
            budget_inr=req.budget_inr,
        )
        itinerary.saved_to_database = True
        return itinerary
    except DatabaseNotConfigured:
        log.warning("itinerary generated but database persistence is not configured")
        itinerary.save_error = "Database is not configured. Add DATABASE_URL and apply the itinerary migration."
        return itinerary
    except Exception as exc:
        log.exception("generated itinerary could not be saved")
        itinerary.save_error = "Database save failed. Check DATABASE_URL, database connectivity, and that the itinerary migration is applied."
        return itinerary
