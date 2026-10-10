"""FastAPI entrypoint.   Run from backend/:   uvicorn app.main:app --reload"""
from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.planner.router import router as planner_router
from app.schemas.itinerary import ERR_INVALID_REQUEST

app = FastAPI(
    title="TBS RoamAgent - Deterministic Route Planner",
    description="Member 3. All fares, timestamps and feasibility are computed here, never by an LLM. "
    "Bundled data is SIMULATED.",
    version="1.0.0",
)

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])


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


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(planner_router)
