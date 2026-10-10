"""Authenticated API for storing the signed-in user's guide details."""
from __future__ import annotations

import hashlib
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import GuideLanguage, GuideProfile, GuideProfileLanguage, Profile
from app.db.session import DatabaseNotConfigured, _session_factory

router = APIRouter(prefix="/api/guides", tags=["guides"])
profile_router = APIRouter(prefix="/api/profile", tags=["profiles"])


class GuideProfileInput(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=7, max_length=32)
    city: str = Field(min_length=1, max_length=120)
    years_experience: int = Field(ge=0, le=60)
    city_knowledge_rating: int = Field(ge=1, le=5)
    biography: str | None = Field(default=None, max_length=2000)
    languages: list[str] = Field(min_length=1, max_length=10)


class AccountRoleInput(BaseModel):
    account_type: str = Field(pattern="^(tourist|guide)$")


def _current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Sign in before saving a guide profile.")
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    key = os.getenv("SUPABASE_KEY", "").strip()
    if not url or not key:
        raise HTTPException(status_code=503, detail="Supabase Auth is not configured on the server.")
    request = Request(
        f"{url}/auth/v1/user",
        headers={"apikey": key, "Authorization": authorization, "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=8) as response:
            user = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code in (401, 403):
            raise HTTPException(status_code=401, detail="Your sign-in session expired. Sign in and retry.") from exc
        raise HTTPException(status_code=503, detail="Could not verify the Supabase session.") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=503, detail="Could not verify the Supabase session.") from exc
    try:
        user["id"] = UUID(str(user["id"]))
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=401, detail="Supabase returned an invalid user session.") from exc
    return user


def _language_code(name: str) -> str:
    return "l_" + hashlib.sha256(name.casefold().encode("utf-8")).hexdigest()[:14]


@profile_router.put("/role")
def save_account_role(payload: AccountRoleInput, user: dict = Depends(_current_user)):
    """Lock the authenticated Supabase account to one app role."""
    metadata = user.get("user_metadata") or {}
    email = user.get("email") or ""
    display_name = str(metadata.get("full_name") or metadata.get("name") or email or "Traveler")[:120]
    phone = metadata.get("phone")
    try:
        with _session_factory()() as session:
            profile = session.get(Profile, user["id"])
            if profile is not None and profile.account_type != payload.account_type:
                raise HTTPException(status_code=409, detail="This email is already registered as a different account type. One email can belong to either a tourist or a guide.")
            if profile is None:
                session.add(Profile(
                    id=user["id"], display_name=display_name,
                    phone=str(phone)[:32] if phone else None,
                    account_type=payload.account_type,
                ))
                session.commit()
            return {"account_type": payload.account_type}
    except HTTPException:
        raise
    except DatabaseNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="This profile conflicts with an existing account record.") from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Could not save the account type. Check the database connection and apply migrations.") from exc


@profile_router.get("/role")
def get_account_role(user: dict = Depends(_current_user)):
    try:
        with _session_factory()() as session:
            profile = session.get(Profile, user["id"])
            if profile is None:
                raise HTTPException(status_code=404, detail="Account type has not been saved yet.")
            return {"account_type": profile.account_type}
    except HTTPException:
        raise
    except DatabaseNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Account database is unavailable.") from exc


def _payload(session: Session, account_id: UUID) -> dict:
    profile = session.get(Profile, account_id)
    guide = session.scalar(select(GuideProfile).where(GuideProfile.profile_id == account_id))
    if profile is None or profile.account_type != "guide" or guide is None:
        raise HTTPException(status_code=404, detail="Guide profile has not been saved yet.")
    language_names = session.scalars(
        select(GuideLanguage.name)
        .join(GuideProfileLanguage, GuideProfileLanguage.language_code == GuideLanguage.code)
        .where(GuideProfileLanguage.guide_profile_id == guide.id)
        .order_by(GuideLanguage.name)
    ).all()
    return {
        "display_name": profile.display_name,
        "phone": profile.phone,
        "city": guide.city,
        "years_experience": guide.years_experience,
        "city_knowledge_rating": guide.city_knowledge_rating,
        "biography": guide.biography,
        "languages": language_names,
        "verification_status": guide.verification_status,
    }


@router.get("/profile")
def get_guide_profile(user: dict = Depends(_current_user)):
    try:
        with _session_factory()() as session:
            return _payload(session, user["id"])
    except DatabaseNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Guide profile database is unavailable.") from exc


@router.put("/profile")
def save_guide_profile(payload: GuideProfileInput, user: dict = Depends(_current_user)):
    display_name = " ".join(payload.display_name.split())
    phone = payload.phone.strip()
    city = " ".join(payload.city.split())
    if not display_name or not phone or not city:
        raise HTTPException(status_code=422, detail="Name, phone, and city cannot be blank.")
    names = []
    seen_languages = set()
    for raw_name in payload.languages:
        name = " ".join(raw_name.split())
        if name and name.casefold() not in seen_languages:
            names.append(name)
            seen_languages.add(name.casefold())
    if not names:
        raise HTTPException(status_code=422, detail="Enter at least one language.")
    if any(len(name) > 80 for name in names):
        raise HTTPException(status_code=422, detail="Language names must be 80 characters or fewer.")

    try:
        with _session_factory()() as session:
            profile = session.get(Profile, user["id"])
            if profile is not None and profile.account_type != "guide":
                raise HTTPException(status_code=409, detail="This email already belongs to a tourist account. One email can use only one account type.")
            if profile is None:
                metadata = user.get("user_metadata") or {}
                full_name = payload.display_name or metadata.get("full_name") or user.get("email") or "Guide"
                profile = Profile(id=user["id"], display_name=display_name or full_name[:120], phone=phone, account_type="guide")
                session.add(profile)
                session.flush()
            else:
                profile.display_name = display_name
                profile.phone = phone

            guide = session.scalar(select(GuideProfile).where(GuideProfile.profile_id == user["id"]))
            if guide is None:
                guide = GuideProfile(profile_id=user["id"], city=city)
                session.add(guide)
                session.flush()
            guide.city = city
            guide.years_experience = payload.years_experience
            guide.city_knowledge_rating = payload.city_knowledge_rating
            guide.biography = payload.biography

            session.execute(delete(GuideProfileLanguage).where(GuideProfileLanguage.guide_profile_id == guide.id))
            for name in names:
                code = _language_code(name)
                language = session.get(GuideLanguage, code)
                if language is None:
                    language = GuideLanguage(code=code, name=name)
                    session.add(language)
                    session.flush()
                session.add(GuideProfileLanguage(guide_profile_id=guide.id, language_code=code))
            session.commit()
            return _payload(session, user["id"])
    except HTTPException:
        raise
    except DatabaseNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="That phone number is already in use, or guide details conflict with an existing record.") from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Could not save guide details. Check the database connection and apply migrations.") from exc
