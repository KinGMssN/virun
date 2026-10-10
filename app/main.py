import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

load_dotenv()

from app.concierge.router import router  # noqa: E402

app = FastAPI(title="TBS RoamAgent")

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])

app.include_router(router)


@app.get("/health")
def health():
    return {"ok": True}


@app.exception_handler(Exception)
async def safe_error(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"status": "error", "error_code": "INTERNAL_ERROR", "fallback": "manual_entry",
                 "missing_fields": [], "clarification_questions": []},
    )
