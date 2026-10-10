import json
import logging

from pydantic import ValidationError

from app.concierge.model_adapter import ModelError
from app.concierge.prompts import build_itinerary_prompt
from app.schemas.trip import GeneratedItinerary, ItineraryGenerationRequest, RealPlace

log = logging.getLogger("concierge")


def generate_itinerary(req: ItineraryGenerationRequest, adapter, real_places=None) -> GeneratedItinerary:
    prompt = build_itinerary_prompt(
        req.destination,
        req.duration_days,
        req.preferences,
        req.duration_nights,
        req.budget_inr,
    )
    try:
        raw = adapter.generate_itinerary(prompt)
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("model response must be a JSON object")
        itinerary = GeneratedItinerary.model_validate(data)
        if itinerary.duration_days != req.duration_days:
            raise ValueError("model response duration does not match request")
        if itinerary.destination.strip().casefold() != req.destination.strip().casefold():
            raise ValueError("model response destination does not match request")
        itinerary.places = [RealPlace.model_validate(place) for place in (real_places or [])]
        return itinerary
    except ModelError:
        raise
    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        log.warning("itinerary generation returned an invalid response")
        raise ModelError("INVALID_MODEL_OUTPUT") from exc
    except Exception as exc:
        log.warning("itinerary generation failed")
        raise ModelError("MODEL_ERROR") from exc
