"""Agent schemas — new, additive. Follows the team's canonical schema style."""
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    city: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    mode: Literal["auto", "mock"] = "auto"


class ToolCallRecord(BaseModel):
    tool: str
    args: Dict[str, Any] = {}
    ok: bool = True
    note: str = ""


class HotelResult(BaseModel):
    name: str
    type: str = "hotel"
    lat: Optional[float] = None
    lng: Optional[float] = None
    address: Optional[str] = None


class AgentChatResponse(BaseModel):
    reply: str
    tool_calls: List[ToolCallRecord] = []
    mode: Literal["live", "mock"] = "mock"
    hotels: List[HotelResult] = []
    rapido: Optional[Dict[str, Any]] = None
