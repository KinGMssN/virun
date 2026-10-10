import os
import logging

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException

from app.concierge.model_adapter import MockAdapter, ModelError, get_adapter
from app.concierge.itinerary_service import generate_itinerary
from app.concierge.service import run_parse
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
        reply = adapter.chat(
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
        return generate_itinerary(req, adapter)
    except ModelError as exc:
        log.warning("itinerary generation error code=%s", exc.code)
        status_code = 503 if exc.code == "NOT_CONFIGURED" else 502
        raise HTTPException(
            status_code=status_code,
            detail={
                "code": exc.code,
                "message": "AI itinerary generation is unavailable. Check the Groq configuration and retry.",
            },
        ) from exc
