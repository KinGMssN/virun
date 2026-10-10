"""FastAPI entrypoint.

Run from backend/:
    uvicorn app.main:app --reload
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.concierge.router import router as concierge_router
from app.auth.router import router as auth_router
from app.planner.router import router as planner_router
from app.railradar.router import router as railradar_router
from app.schemas.itinerary import ERR_INVALID_REQUEST

logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(
    title="TBS RoamAgent - Deterministic Route Planner",
    description="Member 3. All fares, timestamps and feasibility are computed here, never by an LLM. "
    "Bundled data is SIMULATED.",
    version="1.0.0",
)

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_PROJECT_ROOT = _BACKEND_ROOT.parent
_FRONTEND_ROOT = next(
    (
        candidate
        for candidate in (
            _PROJECT_ROOT / "frontend",
            _BACKEND_ROOT / "frontend",
            _BACKEND_ROOT,
        )
        if (candidate / "index.html").is_file()
    ),
    _PROJECT_ROOT / "frontend",
)
_RESOURCES = _FRONTEND_ROOT / "resources"
if _RESOURCES.is_dir():
    app.mount("/resources", StaticFiles(directory=str(_RESOURCES)), name="resources")

_FRONTEND = next(
    (
        candidate
        for candidate in (
            _FRONTEND_ROOT / "index.html",
            Path("/app/frontend/index.html"),
        )
        if candidate.is_file()
    ),
    _FRONTEND_ROOT / "index.html",
)


@app.get("/", include_in_schema=False)
def frontend():
    candidates = (
        _FRONTEND,
        Path.cwd() / "frontend" / "index.html",
        Path.cwd().parent / "frontend" / "index.html",
        Path("/app/frontend/index.html"),
        _BACKEND_ROOT / "frontend" / "index.html",
        Path.cwd() / "index.html",
    )
    frontend_file = next((candidate for candidate in candidates if candidate.is_file()), None)
    if frontend_file is None:
        return JSONResponse(status_code=404, content={"detail": "Frontend file not found."})
    return FileResponse(frontend_file, media_type="text/html")


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    details = [
        {"field": ".".join(str(p) for p in err["loc"][1:]) or "request", "message": err["msg"]}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={"error": {"code": ERR_INVALID_REQUEST, "message": "The trip request is invalid.", "details": details}},
    )


@app.exception_handler(Exception)
async def safe_error(_: Request, exc: Exception):
    logger.error(
        "Unhandled API request error",
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error_code": "INTERNAL_ERROR",
            "fallback": "manual_entry",
            "missing_fields": [],
            "clarification_questions": [],
        },
    )


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(concierge_router)
app.include_router(auth_router)
app.include_router(planner_router)
app.include_router(railradar_router)
