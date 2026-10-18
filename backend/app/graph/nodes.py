import asyncio
import json
from typing import Any

from backend.app.agents.activity_agent import run_activity_agent
from backend.app.agents.hotel_agent import run_hotel_agent
from backend.app.agents.transport_agent import run_transport_agent
from backend.app.agents.weather_agent import run_weather_agent
from backend.app.graph.state import TravelAgentState
from backend.app.integrations.groq_client import ask_llm
from backend.app.integrations.mcp_client import call_travel_mcp_tool
from backend.app.services.budget_service import calculate_budget
from backend.app.services.live_travel_data import (
    get_live_weather,
    get_tourist_places,
)


def _as_dict(value: Any) -> dict[str, Any]:
    """Normalize a provider result to a dictionary."""
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        return {"items": value}
    return {"result": value} if value is not None else {}


async def _safe_mcp_call(
    name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Call one MCP tool without letting a single failure stop collection."""
    try:
        result = await call_travel_mcp_tool(name, arguments)
        normalized = _as_dict(result)
        normalized.setdefault("tool", name)
        normalized.setdefault("status", "available")
        return normalized
    except Exception as exc:
        return {
            "tool": name,
            "status": "unavailable",
            "error": str(exc),
            "result": [],
        }


async def _safe_live_call(name: str, destination: str) -> dict[str, Any]:
    """Call live weather/place providers and preserve useful error details."""
    try:
        if name == "live_weather":
            result = await get_live_weather(destination)
        elif name == "live_places":
            result = await get_tourist_places(destination)
        else:
            return {
                "status": "unavailable",
                "error": f"Unknown live-data service: {name}",
            }

        normalized = _as_dict(result)
        normalized.setdefault("status", "available")
        return normalized
    except Exception as exc:
        response: dict[str, Any] = {
            "status": "unavailable",
            "error": str(exc),
            "destination_requested": destination,
        }
        if name == "live_places":
            response.update({"count": 0, "places": []})
        return response


async def collect_travel_data(
    source: str,
    destination: str,
) -> dict[str, Any]:
    """
    Collect MCP sample/provider data and live weather/nearby-place data.

    This project currently does not integrate a flight booking API. Transport
    results must not be described as live/confirmed unless the provider says so.
    """
    calls = [
        (
            "find_transport",
            {"source": source, "destination": destination},
        ),
        ("find_hotels", {"destination": destination}),
        ("find_activities", {"destination": destination}),
        ("check_weather", {"destination": destination}),
    ]

    results: dict[str, Any] = {}

    # Keep MCP calls sequential to avoid overwhelming a local MCP server.
    for name, arguments in calls:
        results[name] = await _safe_mcp_call(name, arguments)

    # Weather and places use the same requested destination. The location
    # resolver in live_travel_data.py must disambiguate names such as "Goa".
    results["live_weather"] = await _safe_live_call(
        "live_weather", destination
    )
    results["live_places"] = await _safe_live_call(
        "live_places", destination
    )
    return results


def collect_tools_node(state: TravelAgentState) -> TravelAgentState:
    """Collect available travel data for the graph."""
    source = str(state.get("source", "")).strip()
    destination = str(state.get("destination", "")).strip()

    if not destination:
        return {**state, "error": "Destination is required."}

    try:
        tool_data = asyncio.run(collect_travel_data(source, destination))
        return {**state, "tool_data": tool_data, "error": ""}
    except Exception as exc:
        return {
            **state,
            "error": f"Travel data collection failed: {exc}",
        }


def specialist_agents_node(state: TravelAgentState) -> TravelAgentState:
    """Run transport, hotel, activity, and weather specialist agents."""
    if state.get("error"):
        return state

    tool_data = state.get("tool_data") or {}
    budget = float(state.get("budget") or 0)
    travelers = max(1, int(state.get("travelers") or 1))
    days = max(1, int(state.get("days") or 1))

    try:
        transport_options = run_transport_agent(
            transport_data=tool_data.get("find_transport", {}),
            budget=budget,
            travelers=travelers,
        )
        hotel_options = run_hotel_agent(
            tool_data.get("find_hotels", {}),
            budget=budget,
        )
        activity_options = run_activity_agent(
            activity_data=tool_data.get("find_activities", {}),
            preferences=state.get("preferences") or [],
        )
        weather_summary = run_weather_agent(
            weather_data=tool_data.get("live_weather", {}),
            destination=str(state.get("destination", "")),
            days=days,
        )

        return {
            **state,
            "transport_options": transport_options,
            "hotel_options": hotel_options,
            "activity_options": activity_options,
            "weather_summary": weather_summary,
        }
    except Exception as exc:
        # Keep the collected source data available for debugging/fallback.
        return {
            **state,
            "transport_options": state.get("transport_options", {}),
            "hotel_options": state.get("hotel_options", {}),
            "activity_options": state.get("activity_options", {}),
            "weather_summary": state.get("weather_summary", {}),
            "error": f"Specialist agent processing failed: {exc}",
        }


def budget_agent_node(state: TravelAgentState) -> TravelAgentState:
    """Calculate budget using deterministic Python logic, not the LLM."""
    if state.get("error"):
        return state

    try:
        breakdown = calculate_budget(
            tool_data=state.get("tool_data", {}),
            travelers=max(1, int(state.get("travelers") or 1)),
            days=max(1, int(state.get("days") or 1)),
            budget=float(state.get("budget") or 0),
        )
        analysis = json.dumps(
            breakdown,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
        return {
            **state,
            "budget_breakdown": breakdown,
            "budget_analysis": analysis,
        }
    except Exception as exc:
        return {**state, "error": f"Budget calculation failed: {exc}"}


def _json_for_prompt(value: Any, max_chars: int = 16000) -> str:
    """Serialize prompt data safely and limit excessive provider payloads."""
    try:
        serialized = json.dumps(
            value, ensure_ascii=False, indent=2, default=str
        )
    except (TypeError, ValueError):
        serialized = str(value)
    if len(serialized) > max_chars:
        return serialized[:max_chars] + "\n[Data truncated to fit prompt.]"
    return serialized


def itinerary_agent_node(state: TravelAgentState) -> TravelAgentState:
    """Generate a practical itinerary from the collected evidence."""
    if state.get("error"):
        return state

    tool_data = state.get("tool_data") or {}
    budget_breakdown = state.get("budget_breakdown") or {}
    live_weather = tool_data.get("live_weather") or {}
    live_places = tool_data.get("live_places") or {}

    prompt = f"""
You are an AI travel itinerary planner. Be practical, transparent, and factual.

TRIP DETAILS
- Source: {state.get("source", "")}
- Destination: {state.get("destination", "")}
- Start date: {state.get("check_in", "Not provided")}
- End date: {state.get("check_out", "Not provided")}
- Duration: {state.get("days", 1)} days
- Travelers: {state.get("travelers", 1)}
- Total budget: INR {state.get("budget", 0)}
- Preferences: {state.get("preferences", [])}

SPECIALIST AGENT OUTPUTS
Transport options:
{_json_for_prompt(state.get("transport_options", {}), 5000)}

Hotel options:
{_json_for_prompt(state.get("hotel_options", {}), 5000)}

Activity options:
{_json_for_prompt(state.get("activity_options", {}), 5000)}

Weather summary:
{_json_for_prompt(state.get("weather_summary", {}), 4000)}

COLLECTED TOOL DATA
{_json_for_prompt(tool_data, 10000)}

AUTHORITATIVE PYTHON BUDGET (do not modify these amounts)
{_json_for_prompt(budget_breakdown, 5000)}

RULES
1. The Python budget breakdown is authoritative. Do not recalculate or change its amounts.
2. Do not suggest flights or use a flight API. Prefer train and bus; if options are missing, say transport prices/options are unavailable and ask the traveler to verify independently.
3. Never invent transport fares, hotel prices, availability, opening hours, ticket prices, or booking confirmations.
4. Treat data with is_live_quote=false, sample labels, or unavailable status as sample/non-live data, not a live quote.
5. If live weather status is not "live", say live weather could not be retrieved.
6. Confirm that live weather/place data refers to the requested destination. If the returned location is different from the requested destination, do not use that data; explicitly flag a location mismatch.
7. Do not call a Wikipedia result a verified attraction unless verified_tourist_attraction is explicitly true.
8. If accommodation or transport costs are missing, do not present the budget as a complete trip cost. Clearly mention the missing costs.
9. Follow the requested number of days and travelers. If dates are provided, align the schedule to those dates.
10. Respect the stated budget and explain any shortfall without changing the Python totals.
11. Suggest practical meals and activities, but label any unsourced prices as estimates only if the budget service explicitly provides them as estimates.
12. The project currently has no flight booking integration; do not mention flight booking as an available feature.

Return:
- A short trip overview
- Day-by-day plan
- Transport and accommodation notes
- Weather note, only if valid for the requested destination
- Exact budget breakdown copied from the Python result
- Missing-data warnings and practical next steps
"""

    try:
        itinerary = ask_llm(prompt)
        if not isinstance(itinerary, str) or not itinerary.strip():
            return {
                **state,
                "error": "Itinerary generation failed: the LLM returned an empty response.",
            }
        return {**state, "itinerary": itinerary.strip(), "error": ""}
    except Exception as exc:
        return {**state, "error": f"Itinerary generation failed: {exc}"}


def review_agent_node(state: TravelAgentState) -> TravelAgentState:
    """Check factual consistency without changing Python-calculated totals."""
    if state.get("error"):
        return state

    tool_data = state.get("tool_data") or {}
    live_weather = tool_data.get("live_weather") or {}
    live_places = tool_data.get("live_places") or {}
    budget = state.get("budget_breakdown") or {}

    requested_destination = str(state.get("destination", "")).strip().casefold()
    weather_location = live_weather.get("location") or {}
    returned_location = str(
        weather_location.get("name")
        or live_weather.get("resolved_location")
        or ""
    ).strip().casefold()

    # Basic mismatch guard. Exact/case-insensitive comparison is intentionally
    # conservative; robust global disambiguation belongs in live_travel_data.py.
    location_mismatch = bool(
        returned_location
        and requested_destination
        and returned_location != requested_destination
        and requested_destination not in returned_location
    )

    compact_data = {
        "requested_destination": state.get("destination"),
        "weather_location": weather_location,
        "weather_status": live_weather.get("status"),
        "weather_location_mismatch": location_mismatch,
        "current_weather": live_weather.get("current"),
        "forecast": live_weather.get("forecast", [])[:3]
        if isinstance(live_weather.get("forecast"), list)
        else [],
        "places_status": live_places.get("status"),
        "places_location": live_places.get("location")
        or live_places.get("resolved_location"),
        "places": [
            {
                "name": place.get("name"),
                "verified_tourist_attraction": place.get(
                    "verified_tourist_attraction", False
                ),
            }
            for place in (live_places.get("places") or [])[:5]
            if isinstance(place, dict)
        ],
    }

    compact_budget = {
        "currency": budget.get("currency", "INR"),
        "user_budget": budget.get("user_budget"),
        "known_subtotal": budget.get("known_subtotal"),
        "estimated_total": budget.get("estimated_total"),
        "essential_prices_complete": budget.get("essential_prices_complete"),
        "budget_remaining": budget.get("budget_remaining"),
        "line_items": budget.get("line_items", {}),
        "warnings": budget.get("warnings", []),
        "is_live_quote": budget.get("is_live_quote", False),
    }

    draft = str(state.get("itinerary") or "")
    if len(draft) > 10000:
        draft = draft[:10000] + "\n\n[Draft truncated for review.]"

    prompt = f"""
You are a travel itinerary quality reviewer.

TRIP
- Source: {state.get("source", "")}
- Destination: {state.get("destination", "")}
- Start date: {state.get("check_in", "Not provided")}
- End date: {state.get("check_out", "Not provided")}
- Days: {state.get("days", 1)}
- Travelers: {state.get("travelers", 1)}

FACT CHECK DATA
{_json_for_prompt(compact_data, 5000)}

AUTHORITATIVE PYTHON BUDGET
{_json_for_prompt(compact_budget, 4000)}

DRAFT
{draft}

RULES
1. Correct day-count, destination, and factual inconsistencies.
2. Never claim a booking or availability is confirmed.
3. Never invent prices, opening hours, weather, or live data.
4. Never change any Python-calculated budget amount.
5. Disclose missing transport/accommodation prices and sample data.
6. Do not suggest flights; this project has no flight API.
7. If weather location mismatches the requested destination, remove weather claims and state that destination-matched live weather was unavailable.
8. Do not label unverified places as verified attractions.
9. Return the corrected itinerary only.
"""

    try:
        reviewed = ask_llm(prompt)
        if not isinstance(reviewed, str) or not reviewed.strip():
            return {
                **state,
                "review_notes": (
                    "Review returned an empty response; original itinerary preserved."
                ),
            }
        return {
            **state,
            "itinerary": reviewed.strip(),
            "review_notes": "Final review completed.",
        }
    except Exception as exc:
        # Review is optional: preserve the draft if the review model is down.
        return {
            **state,
            "review_notes": f"Review unavailable; original itinerary preserved: {exc}",
        }
