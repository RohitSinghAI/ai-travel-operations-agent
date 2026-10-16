
import asyncio
import json
from typing import Any

from backend.app.graph.state import TravelAgentState
from backend.app.integrations.groq_client import ask_llm
from backend.app.integrations.mcp_client import call_travel_mcp_tool
from backend.app.services.budget_service import calculate_budget


async def collect_travel_data(
    source: str,
    destination: str,
) -> dict[str, Any]:
    """Call MCP tools sequentially and retain tool errors."""

    calls = [
        ("find_transport", {
            "source": source,
            "destination": destination,
        }),
        ("find_hotels", {"destination": destination}),
        ("find_activities", {"destination": destination}),
        ("check_weather", {"destination": destination}),
    ]

    results = {}

    for name, arguments in calls:
        try:
            results[name] = await call_travel_mcp_tool(
                name, arguments
            )
        except Exception as exc:
            results[name] = {
                "tool": name,
                "error": str(exc),
            }

    return results


def collect_tools_node(
    state: TravelAgentState,
) -> TravelAgentState:
    try:
        tool_data = asyncio.run(
            collect_travel_data(
                state.get("source", ""),
                state.get("destination", ""),
            )
        )
        return {**state, "tool_data": tool_data}
    except Exception as exc:
        return {
            **state,
            "error": f"MCP collection failed: {exc}",
        }


def budget_agent_node(
    state: TravelAgentState,
) -> TravelAgentState:
    """Calculate the budget deterministically in Python."""

    if state.get("error"):
        return state

    try:
        breakdown = calculate_budget(
            tool_data=state.get("tool_data", {}),
            travelers=state.get("travelers", 1),
            days=state.get("days", 1),
            budget=state.get("budget", 0),
        )

        analysis = json.dumps(
            breakdown,
            ensure_ascii=False,
            indent=2,
        )

        return {
            **state,
            "budget_breakdown": breakdown,
            "budget_analysis": analysis,
        }

    except Exception as exc:
        return {
            **state,
            "error": f"Budget calculation failed: {exc}",
        }


def itinerary_agent_node(
    state: TravelAgentState,
) -> TravelAgentState:
    if state.get("error"):
        return state

    prompt = f"""
You are an AI travel itinerary planner.

Trip details:
- Source: {state.get("source", "")}
- Destination: {state.get("destination", "")}
- Days: {state.get("days", 1)}
- Travelers: {state.get("travelers", 1)}
- Budget: INR {state.get("budget", 0)}
- Preferences: {state.get("preferences", [])}

MCP data:
{json.dumps(state.get("tool_data", {}), ensure_ascii=False, indent=2, default=str)}

AUTHORITATIVE PYTHON BUDGET CALCULATION:
{json.dumps(state.get("budget_breakdown", {}), ensure_ascii=False, indent=2, default=str)}

Rules:
1. Use the Python calculated amounts as the single source of truth.
2. Do not recalculate or change the calculated total.
3. Explain that sample records and food assumptions are not live quotes.
4. Do not claim that bookings or availability are confirmed.
5. If essential prices are missing, state that the total is incomplete.
6. Make the schedule consistent with the stated number of days and nights.
7. If the budget is insufficient, explain the shortfall honestly.
8. Do not describe unverified activities as confirmed options.

Write a clear day-by-day itinerary, followed by the exact budget
breakdown from the Python calculation.
"""

    try:
        itinerary = ask_llm(prompt)
        return {**state, "itinerary": itinerary}
    except Exception as exc:
        return {
            **state,
            "error": f"Itinerary generation failed: {exc}",
        }


def review_agent_node(
    state: TravelAgentState,
) -> TravelAgentState:
    if state.get("error"):
        return state

    prompt = f"""
Review this travel itinerary for factual consistency.

Trip: {state.get("source", "")} to {state.get("destination", "")}
Days: {state.get("days", 1)}
Travelers: {state.get("travelers", 1)}

Authoritative Python budget:
{json.dumps(state.get("budget_breakdown", {}), ensure_ascii=False, indent=2)}

Draft itinerary:
{state.get("itinerary", "")}

Correct unsupported booking claims and schedule inconsistencies.
Do not change any numeric budget amount from the Python calculation.
Clearly disclose missing prices and unverified sample data.
Return the corrected itinerary only, including the budget breakdown.
"""

    try:
        reviewed = ask_llm(prompt)
        return {
            **state,
            "itinerary": reviewed,
            "review_notes": "Final review completed.",
        }
    except Exception as exc:
        return {
            **state,
            "review_notes": f"Review unavailable: {exc}",
        }
