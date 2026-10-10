import json
import logging

from pydantic import ValidationError

from app.concierge.model_adapter import ModelError
from app.concierge.prompts import build_itinerary_prompt
from app.schemas.trip import GeneratedItinerary, ItineraryGenerationRequest, RealPlace

log = logging.getLogger("concierge")

_ACTIVITY_TAGS = {
    "morning_location": {"museum": ("museum", "gallery"), "nature": ("park", "viewpoint", "zoo"), "heritage": ("monument", "fort", "historic", "castle", "ruins"), "market": ("market",), "food": ("restaurant", "cafe", "food")},
    "afternoon_location": {"museum": ("museum", "gallery"), "nature": ("park", "viewpoint", "lake", "zoo"), "heritage": ("monument", "fort", "historic", "castle", "ruins"), "market": ("market",), "food": ("restaurant", "cafe", "food")},
    "evening_location": {"nature": ("park", "viewpoint", "lake"), "food": ("restaurant", "cafe", "food"), "music": ("theatre", "arts", "music")},
}
_ACTIVITY_CUES = {
    "museum": ("museum", "gallery", "art", "exhibition"),
    "nature": ("nature", "park", "lake", "hike", "hill", "viewpoint", "picnic", "sunset", "beach", "walk", "relax"),
    "heritage": ("heritage", "historic", "monument", "fort", "castle", "ruins", "culture", "temple"),
    "market": ("market", "bazaar", "shopping", "handicraft", "souvenir"),
    "food": ("food", "restaurant", "cafe", "eatery", "dinner", "street food"),
    "music": ("music", "performance", "theatre", "concert"),
}


def _attach_real_locations(itinerary: GeneratedItinerary, places: list[RealPlace]) -> None:
    """Attach only sourced OSM places; never manufacture a place name."""
    if not places:
        return
    unused = list(places)
    slots = ("morning", "afternoon", "evening")
    for day in itinerary.days:
        for slot in slots:
            field = f"{slot}_location"
            activity = f"{day.title} {getattr(day, slot)}".casefold()
            keywords = set()
            for group, terms in _ACTIVITY_TAGS[field].items():
                if any(cue in activity for cue in _ACTIVITY_CUES[group]):
                    keywords.update(terms)
            candidates = unused or list(places)
            place = max(
                candidates,
                key=lambda item: sum(term in f"{item.category} {item.name}".casefold() for term in keywords),
            )
            setattr(day, field, place)
            unused = [candidate for candidate in unused if candidate != place]


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
        _attach_real_locations(itinerary, itinerary.places)
        return itinerary
    except ModelError:
        raise
    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        log.warning("itinerary generation returned an invalid response")
        raise ModelError("INVALID_MODEL_OUTPUT") from exc
    except Exception as exc:
        log.warning("itinerary generation failed")
        raise ModelError("MODEL_ERROR") from exc
