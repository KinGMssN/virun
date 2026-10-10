import os

from dotenv import load_dotenv
from fastapi import APIRouter

from app.concierge.model_adapter import MockAdapter, ModelError, get_adapter
from app.concierge.service import run_parse
from app.schemas.trip import ParseTripRequest, ParseTripResponse

load_dotenv()
router = APIRouter(prefix="/api")

FALLBACK_CODES = {"QUOTA_EXCEEDED", "MODEL_TIMEOUT", "MODEL_ERROR"}


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
