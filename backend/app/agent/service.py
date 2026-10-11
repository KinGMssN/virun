"""Agentic loop for the Virun travel agent.

Live mode: Groq (OpenAI-compatible) tool calling, same adapter style as
app/concierge. Mock mode: transparent rule-based routing that only uses
the repo's own datasets. The response always says which mode ran.
"""
import json
import logging
import os
import re
from typing import Any, Dict, List

from app.agent.tools import TOOLS_SPEC, rapido_handoff, run_tool, search_hotels
from app.schemas.agent import AgentChatResponse, HotelResult, ToolCallRecord

log = logging.getLogger("agent")

SYSTEM = (
    "You are Virun Agent, a travel assistant for Indian cities. "
    "You have tools: search_hotels (real OSM dataset — never invent hotels), "
    "rapido_handoff (returns deep links; you cannot book rides), "
    "tracking_session (explains live GPS tracking). "
    "Be concise. If the user asks for hotels, call search_hotels first. "
    "Never claim a booking was completed."
)


def _groq_client():
    key = os.getenv("GROQ_API_KEY")
    model = os.getenv("GROQ_MODEL")
    if not key or not model:
        return None, None
    from openai import OpenAI
    return OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1",
                  timeout=float(os.getenv("MODEL_TIMEOUT_SECONDS", "60")),
                  max_retries=0), model


def _live_reply(message: str, city: str):
    client, model = _groq_client()
    if client is None:
        return None
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": message + ("\n[Trip city: %s]" % city if city else "")},
    ]
    tool_calls: List[ToolCallRecord] = []
    hotels: List[HotelResult] = []
    rapido = None
    for _ in range(4):  # bounded agentic loop
        r = client.chat.completions.create(
            model=model, messages=messages, tools=TOOLS_SPEC,
            tool_choice="auto", temperature=0.2)
        msg = r.choices[0].message
        if not msg.tool_calls:
            reply = msg.content or ""
            break
        messages.append(msg)
        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception:
                args = {}
            try:
                result = run_tool(name, args)
                ok, note = True, ""
            except Exception as e:  # noqa: BLE001
                result, ok, note = None, False, str(e)[:120]
            tool_calls.append(ToolCallRecord(tool=name, args=args, ok=ok, note=note))
            if name == "search_hotels" and ok:
                hotels = [HotelResult(name=h.get("name", "?"),
                                      type=h.get("type", "hotel"),
                                      lat=h.get("lat"), lng=h.get("lng"),
                                      address=h.get("address")) for h in result]
            if name == "rapido_handoff" and ok:
                rapido = result
            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "content": json.dumps(result, default=str)[:4000]})
    else:
        reply = "I ran the available tools; here is what I found."
    return reply, tool_calls, hotels, rapido


def _mock_reply(message: str, city: str):
    low = message.lower()
    tool_calls: List[ToolCallRecord] = []
    hotels: List[HotelResult] = []
    rapido = None
    mcity = city or ""
    m = re.search(r"\b(kashmir|goa|hyderabad|visakhapatnam|mumbai|delhi|bengaluru)\b", low)
    if m:
        mcity = m.group(1)
    if re.search(r"\bhotel|stay|room|lodge\b", low):
        if not mcity:
            return ("Which city? I have hotel data for Kashmir, Goa, Hyderabad, "
                    "Visakhapatnam, Mumbai, Delhi and Bengaluru."), tool_calls, hotels, rapido, "mock"
        found = search_hotels(mcity, limit=5)
        tool_calls.append(ToolCallRecord(tool="search_hotels",
                                         args={"city": mcity, "limit": 5}, ok=bool(found),
                                         note="" if found else "no dataset file"))
        hotels = [HotelResult(name=h.get("name", "?"), type=h.get("type", "hotel"),
                              lat=h.get("lat"), lng=h.get("lng"),
                              address=h.get("address")) for h in found]
        reply = ("Found %d places in %s (OpenStreetMap data). Booking is a "
                 "mock in this demo — your team connects a booking API next."
                 % (len(found), mcity.title()))
        return reply, tool_calls, hotels, rapido, "mock"
    if re.search(r"\brapido|bike|cab|ride\b", low):
        rapido = rapido_handoff(pickup=mcity.title() or "current location",
                                drop="destination")
        tool_calls.append(ToolCallRecord(tool="rapido_handoff",
                                         args={"pickup": rapido["pickup"]}, ok=True,
                                         note="deep-link only, no booking API"))
        reply = ("I can't book Rapido directly (no public API), but I prepared "
                 "a handoff that opens the Rapido app with your trip details.")
        return reply, tool_calls, hotels, rapido, "mock"
    if re.search(r"\btrack|gps|live|where am i\b", low):
        tool_calls.append(ToolCallRecord(tool="tracking_session",
                                         args={"city": mcity or "goa"}, ok=True))
        reply = ("Live tracking uses your phone's GPS (with your permission) "
                 "and shows you moving along the trip route on the map.")
        return reply, tool_calls, hotels, rapido, "mock"
    reply = ("I can search hotels (7 cities), plan trips, track you live, and "
             "hand off to Rapido. Try: 'hotels in Goa'.")
    return reply, tool_calls, hotels, rapido, "mock"


def run_agent(message: str, city: str = "", lat=None, lng=None,
              mode: str = "auto") -> AgentChatResponse:
    """Run one agent turn. Returns the reply plus a tool-call trace."""
    if mode == "auto":
        try:
            live = _live_reply(message, city or "")
        except Exception as e:  # noqa: BLE001
            log.warning("agent live mode failed: %s", str(e)[:120])
            live = None
        if live is not None:
            reply, calls, hotels, rapido = live
            return AgentChatResponse(reply=reply, tool_calls=calls,
                                     mode="live", hotels=hotels, rapido=rapido)
    reply, calls, hotels, rapido, _ = _mock_reply(message, city or "")
    return AgentChatResponse(reply=reply, tool_calls=calls, mode="mock",
                             hotels=hotels, rapido=rapido)
