"""FastAPI entrypoint.

Run from backend/:
    uvicorn app.main:app --reload
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.concierge.router import router as concierge_router
from app.planner.router import router as planner_router
from app.railradar.router import router as railradar_router
from app.schemas.itinerary import ERR_INVALID_REQUEST

load_dotenv()

app = FastAPI(
    title="TBS RoamAgent - Deterministic Route Planner",
    description="Member 3. All fares, timestamps and feasibility are computed here, never by an LLM. "
    "Bundled data is SIMULATED.",
    version="1.0.0",
)

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])

_RESOURCES = Path(__file__).resolve().parent.parent / "resources"
if _RESOURCES.is_dir():
    app.mount("/resources", StaticFiles(directory=str(_RESOURCES)), name="resources")

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_FRONTEND = next(
    (
        candidate
        for candidate in (
            _PROJECT_ROOT / "index.html",
            _PROJECT_ROOT / "backend" / "index.html",
        )
        if candidate.is_file()
    ),
    _PROJECT_ROOT / "index.html",
)


@app.get("/", include_in_schema=False)
def frontend():
    if not _FRONTEND.is_file():
        return JSONResponse(status_code=404, content={"detail": "Frontend file not found."})
    return FileResponse(_FRONTEND, media_type="text/html")


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
async def safe_error(_: Request, __: Exception):
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
app.include_router(planner_router)
app.include_router(railradar_router)
