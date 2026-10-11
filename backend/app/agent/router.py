"""Agent routes — new, additive. Wire with one line in app/main.py:
    from app.agent.router import router as agent_router
    app.include_router(agent_router)
"""
from typing import List

from fastapi import APIRouter

from app.agent.service import run_agent
from app.agent.tools import KNOWN_CITIES, search_hotels
from app.schemas.agent import AgentChatRequest, AgentChatResponse, HotelResult

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/chat", response_model=AgentChatResponse)
def agent_chat(req: AgentChatRequest):
    return run_agent(req.message, city=req.city or "", lat=req.lat,
                     lng=req.lng, mode=req.mode)


@router.get("/hotels", response_model=List[HotelResult])
def agent_hotels(city: str, q: str = "", limit: int = 5):
    found = search_hotels(city, query=q, limit=limit)
    return [HotelResult(name=h.get("name", "?"), type=h.get("type", "hotel"),
                        lat=h.get("lat"), lng=h.get("lng"),
                        address=h.get("address")) for h in found]


@router.get("/cities")
def agent_cities():
    return {"cities": KNOWN_CITIES}
