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



def _location_matches_destination(destination: str, location: Any) -> bool:
    """Compare resolved place/country fields with a user-entered destination."""
    if not isinstance(location, dict):
        return False

    requested_parts = [part.strip().casefold() for part in destination.split(",") if part.strip()]
    requested_place = requested_parts[0] if requested_parts else ""
    requested_country = requested_parts[-1] if len(requested_parts) > 1 else ""

    returned_name = str(location.get("name") or "").strip().casefold()
    returned_country = str(location.get("country") or "").strip().casefold()

    if not requested_place or not returned_name:
        return False
    if returned_name != requested_place and requested_place not in returned_name:
        return False
    if requested_country and returned_country and requested_country != returned_country:
        return False
    # If the request explicitly included a country but the provider omitted it,
    # do not claim the destination was fully verified.
    if requested_country and not returned_country:
        return False
    return True


def _forecast_for_trip(
    forecast: Any,
    check_in: Any,
    check_out: Any,
) -> tuple[list[dict[str, Any]], bool]:
    """Return forecast days inside the requested trip window and coverage status."""
    if not isinstance(forecast, list):
        return [], False

    start_date = str(check_in or "")[:10]
    end_date = str(check_out or "")[:10]
    if not start_date or not end_date:
        return [], False

    matching_days = [
        item for item in forecast
        if isinstance(item, dict)
        and start_date <= str(item.get("date") or "")[:10] <= end_date
    ]
    expected_dates = {str(item.get("date") or "")[:10] for item in matching_days}
    try:
        from datetime import date, timedelta
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        if end < start:
            return [], False
        required_dates = {
            (start + timedelta(days=offset)).isoformat()
            for offset in range((end - start).days + 1)
        }
    except (TypeError, ValueError):
        return matching_days, False

    return matching_days, required_dates.issubset(expected_dates)


def _rank_tourist_places(places: list) -> list:
    """Rank places by relevance without claiming official verification."""

    if not isinstance(places, list):
        return []

    category_scores = {
        "beach": 10,
        "waterfall": 10,
        "fort": 10,
        "castle": 10,
        "heritage": 9,
        "historic": 9,
        "museum": 9,
        "church": 9,
        "palace": 9,
        "manor": 8,
        "archaeological_site": 8,
        "viewpoint": 8,
        "attraction": 7,
        "gallery": 7,
        "zoo": 7,
        "theme_park": 7,
        "park": 3,
        "artwork": 2,
        "nearby documented place": 1,
    }

    keywords = {
        "beach": 10,
        "waterfall": 10,
        "fort": 10,
        "museum": 9,
        "church": 9,
        "palace": 9,
        "heritage": 9,
        "temple": 8,
        "viewpoint": 8,
    }

    ranked = []
    seen = set()

    for place in places:
        if not isinstance(place, dict):
            continue

        name = str(place.get("name") or "").strip()
        if not name:
            continue

        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)

        category = str(place.get("category") or "").casefold()
        name_lower = name.casefold()
        score = category_scores.get(category, 2)

        for keyword, keyword_score in keywords.items():
            if keyword in name_lower:
                score = max(score, keyword_score)

        # Keep original source and verification metadata unchanged.
        ranked.append((score, place))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [place for _, place in ranked]


def itinerary_agent_node(state: TravelAgentState) -> TravelAgentState:
    """Generate a practical itinerary from validated travel evidence."""

    if state.get("error"):
        return state

    tool_data = state.get("tool_data") or {}
    budget_breakdown = state.get("budget_breakdown") or {}
    live_weather = tool_data.get("live_weather") or {}
    live_places = tool_data.get("live_places") or {}

    destination = str(state.get("destination", "")).strip()

    # --------------------------------------------------
    # 1. Validate weather location and trip dates
    # --------------------------------------------------
    weather_location = live_weather.get("location") or {}

    weather_matches = _location_matches_destination(
        destination,
        weather_location,
    )

    trip_forecast, forecast_covers_trip = _forecast_for_trip(
        live_weather.get("forecast"),
        state.get("start_date"),
        state.get("end_date"),
    )

    weather_for_prompt = {
        "status": live_weather.get("status", "unavailable"),
        "location": weather_location,
        "location_matches_requested_destination": weather_matches,
        "current": (
            live_weather.get("current")
            if weather_matches
            else None
        ),
        "trip_forecast": (
            trip_forecast
            if weather_matches and forecast_covers_trip
            else []
        ),
        "forecast_covers_entire_trip": bool(
            weather_matches and forecast_covers_trip
        ),
        "note": (
            "Forecast covers the complete requested trip date range."
            if weather_matches and forecast_covers_trip
            else (
                "A destination-matched forecast for the complete trip "
                "date range is unavailable. Do not use current conditions "
                "or a partial forecast as trip-date weather."
            )
        ),
    }

    # --------------------------------------------------
    # 2. Validate tourist-place destination and rank places
    # --------------------------------------------------
    places_location = (
        live_places.get("location")
        or live_places.get("resolved_location")
        or {}
    )

    places_match = _location_matches_destination(
        destination,
        places_location,
    )

    raw_places = live_places.get("places") or []

    ranked_places = (
        _rank_tourist_places(raw_places)
        if places_match
        else []
    )

    places_for_prompt = {
        "status": live_places.get("status", "unavailable"),
        "provider": live_places.get("provider"),
        "location": places_location,
        "location_matches_requested_destination": places_match,
        "count": len(ranked_places),
        "places": ranked_places,
        "note": (
            "Places are ranked by relevance heuristics. Ranking does not "
            "prove official verification or current visitor access. "
            "Only describe a place as verified when its "
            "verified_tourist_attraction field is explicitly true."
            if places_match
            else (
                "Place results do not match the requested destination. "
                "Do not use them in the itinerary."
            )
        ),
    }

    # --------------------------------------------------
    # 3. Build itinerary prompt
    # --------------------------------------------------
    prompt = f"""
You are an AI travel itinerary planner. Be practical, transparent, and factual.

TRIP DETAILS
- Source: {state.get("source", "")}
- Destination: {destination}
- Start date: {state.get("start_date", "Not provided")}
- End date: {state.get("end_date", "Not provided")}
- Duration: {state.get("days", 1)} days
- Travelers: {state.get("travelers", 1)}
- Total budget: {state.get("currency", "INR")} {state.get("budget", 0)}
- Preferences: {state.get("preferences", [])}

SPECIALIST AGENT OUTPUTS

Transport options:
{_json_for_prompt(state.get("transport_options", {}), 5000)}

Hotel options:
{_json_for_prompt(state.get("hotel_options", {}), 5000)}

Activity options:
{_json_for_prompt(state.get("activity_options", {}), 5000)}

Weather summary from specialist agent:
{_json_for_prompt(state.get("weather_summary", {}), 3000)}

VALIDATED WEATHER FOR REQUESTED TRIP DATES:
{_json_for_prompt(weather_for_prompt, 4000)}

RANKED TOURIST-PLACE DATA:
{_json_for_prompt(places_for_prompt, 6000)}

COLLECTED TOOL DATA:
{_json_for_prompt(tool_data, 10000)}

AUTHORITATIVE PYTHON BUDGET:
{_json_for_prompt(budget_breakdown, 5000)}

RULES

1. The Python budget breakdown is authoritative. Copy its amounts exactly.
   Do not recalculate, alter, or silently replace its totals.

2. Do not suggest flights or use a flight API. Prefer train and bus.
   If transport options are missing, say that transport options and fares
   are unavailable and ask the traveler to verify independently.

3. Never invent transport fares, hotel prices, availability, opening
   hours, ticket prices, or booking confirmations.

4. Data marked is_live_quote=false, sample, or unavailable is not a
   confirmed live quote.

5. Use weather as trip-date forecast only when both
   location_matches_requested_destination and
   forecast_covers_entire_trip are true.

6. If a valid full-trip forecast is unavailable, explicitly say so.
   Never present current weather or a partial/out-of-range forecast
   as weather for the requested travel dates.

7. Use tourist-place data only when
   location_matches_requested_destination is true.

8. Prioritize relevant beaches, forts, waterfalls, heritage sites,
   museums, churches, viewpoints, and other suitable visitor attractions.

9. Deprioritize generic playgrounds, roadside statues, and ordinary
   residential localities unless specifically requested by the traveler.

10. Ranking is a relevance heuristic, not proof of official verification.
    Do not claim a place is officially verified or open to visitors unless
    the supplied evidence supports that claim.

11. Never call a Wikipedia result a verified attraction unless
    verified_tourist_attraction is explicitly true.

12. If no relevant places are available, disclose this limitation.
    Do not invent attractions or present unrelated places as highlights.

13. If accommodation or transport costs are missing, do not describe
    the budget as a complete trip cost.

14. Follow the requested number of days, travelers, and dates.

15. Respect the budget. Explain missing costs or potential shortfalls
    without changing the authoritative Python budget totals.

16. Do not present unsourced prices as confirmed prices. Label estimates
    only when the supplied budget data explicitly supports them.

17. This project does not provide flight booking.


18. OpenStreetMap tags are not proof of official tourist-attraction
    verification. Describe the source accurately.

19. Never claim that a place is open, safe to visit, or bookable
    unless the supplied data confirms it.

20. Never invent transport durations, distances, fares, hotel rates,
    attraction ticket prices, or restaurant prices.

21. Do not label a suggested activity as a confirmed booking.

22. If transport or accommodation prices are missing, show them as
    unavailable and clearly mark the budget as partial.

23. Do not describe the remaining budget as final until all essential
    costs have been obtained.

24. Do not claim that a suggested beach, fort, museum, or other place
    is nearby unless its location or distance supports that claim.


RETURN

- Short trip overview.
- Day-by-day itinerary aligned with the requested dates.
- Practical transport and accommodation notes.
- Relevant tourist places, with verification limitations where applicable.
- Weather note only when valid for the requested destination and dates.
- Exact budget breakdown copied from the Python result.
- Missing-data warnings and practical next steps.
"""

    # --------------------------------------------------
    # 4. Generate itinerary using the configured LLM
    # --------------------------------------------------
    try:
        itinerary = ask_llm(prompt)

        if not isinstance(itinerary, str) or not itinerary.strip():
            return {
                **state,
                "error": (
                    "Itinerary generation failed: "
                    "the LLM returned an empty response."
                ),
            }

        return {
            **state,
            "itinerary": itinerary.strip(),
            "error": "",
        }

    except Exception as exc:
        return {
            **state,
            "error": f"Itinerary generation failed: {exc}",
        }


def review_agent_node(state: TravelAgentState) -> TravelAgentState:
    """Check factual consistency without changing Python-calculated totals."""
    if state.get("error"):
        return state

    tool_data = state.get("tool_data") or {}
    live_weather = tool_data.get("live_weather") or {}
    live_places = tool_data.get("live_places") or {}
    budget = state.get("budget_breakdown") or {}

    requested_destination = str(state.get("destination", "")).strip()
    weather_location = live_weather.get("location") or {}
    places_location = live_places.get("location") or live_places.get("resolved_location") or {}
    weather_location_matches = _location_matches_destination(
        requested_destination, weather_location
    )
    places_location_matches = _location_matches_destination(
        requested_destination, places_location
    )
    trip_forecast, forecast_covers_trip = _forecast_for_trip(
        live_weather.get("forecast"),
        state.get("start_date"),
        state.get("end_date"),
    )

    compact_data = {
        "requested_destination": requested_destination,
        "weather_location": weather_location,
        "weather_status": live_weather.get("status"),
        "weather_location_matches_requested_destination": weather_location_matches,
        "trip_forecast_covers_entire_trip": bool(
            weather_location_matches and forecast_covers_trip
        ),
        "trip_forecast": trip_forecast if weather_location_matches else [],
        "places_status": live_places.get("status"),
        "places_location": places_location,
        "places_location_matches_requested_destination": places_location_matches,
        "places": [
            {
                "name": place.get("name"),
                "verified_tourist_attraction": place.get(
                    "verified_tourist_attraction", False
                ),
            }
            for place in ((live_places.get("places") or []) if places_location_matches else [])[:5]
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
- Start date: {state.get("start_date", "Not provided")}
- End date: {state.get("end_date", "Not provided")}
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
7. Only describe weather as a forecast for the trip dates if the location matches and the provider forecast covers the entire requested date range; otherwise say trip-date weather is unavailable.
8. If weather/place location does not match the requested destination, remove those claims and flag the mismatch.
9. Do not label unverified places as verified attractions.
10. Return the corrected itinerary only.
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
