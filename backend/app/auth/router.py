"""Expose only the Supabase public client settings needed by browser Auth flows."""
from __future__ import annotations

import base64
import json
import os

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/auth", tags=["authentication"])


def _is_service_role_key(key: str) -> bool:
    if key.startswith("sb_secret_"):
        return True
    parts = key.split(".")
    if len(parts) < 2:
        return False
    try:
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload.encode("ascii")))
        return claims.get("role") == "service_role"
    except (ValueError, UnicodeError, json.JSONDecodeError):
        return False


@router.get("/config")
def auth_config():
    """Return the public Supabase URL and anon key; never expose a secret key."""
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    key = os.getenv("SUPABASE_KEY", "").strip()
    if not url or not key:
        raise HTTPException(status_code=503, detail="Supabase Auth is not configured on the server.")
    if _is_service_role_key(key):
        raise HTTPException(
            status_code=503,
            detail="SUPABASE_KEY must be the anon/public key; a service-role key cannot be exposed to the browser.",
        )
    return {"url": url, "anon_key": key}
