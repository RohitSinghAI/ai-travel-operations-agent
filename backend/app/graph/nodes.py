
import asyncio
import json
from typing import Any

from backend.app.graph.state import TravelAgentState
from backend.app.integrations.groq_client import ask_llm
from backend.app.integrations.mcp_client import call_travel_mcp_tool


async def collect_travel_data(
    source: str,
    destination: str,
) -> dict[str, Any]:
    """Collect travel information using MCP tools."""

    async def safe_call(
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            return await call_travel_mcp_tool(
                tool_name,
                arguments,
            )
        except Exception as exc:
            return {
                "tool": tool_name,
                "error": str(exc),
            }

    results = await asyncio.gather(
        safe_call(
            "find_transport",
            {"source": source, "destination": destination},
        ),
        safe_call(
            "find_hotels",
            {"destination": destination},
        ),
        safe_call(
            "find_activities",
            {"destination": destination},
        ),
        safe_call(
            "check_weather",
            {"destination": destination},
        ),
    )

    return {item["tool"]: item for item in results}


def collect_tools_node(
    state: TravelAgentState,
) -> TravelAgentState:
    """Node 1: Gather data from MCP."""

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
            "error": f"MCP data collection failed: {exc}",
        }


def budget_agent_node(
    state: TravelAgentState,
) -> TravelAgentState:
    """Node 2: Analyze the budget using available tool data."""

    if state.get("error"):
        return state

    prompt = f"""
You are a travel budget analysis agent.

Trip:
- Source: {state.get("source", "")}
- Destination: {state.get("destination", "")}
- Days: {state.get("days", 1)}
- Travelers: {state.get("travelers", 1)}
- Total available budget in INR: {state.get("budget", 0)}

MCP tool data:
{json.dumps(state.get("tool_data", {}), ensure_ascii=False, indent=2, default=str)}

Analyze a realistic budget for transport, accommodation, food,
activities and a reasonable contingency.

Rules:
- Distinguish verified tool data from estimates.
- Do not invent prices or availability from missing tool results.
- State when data is insufficient for a reliable estimate.
- Consider the number of travelers and trip duration.
- Compare the estimated total with the user's budget.
- Do not claim that anything has been booked.
- Write a concise analysis in plain text.
"""

    try:
        analysis = ask_llm(prompt)
        return {**state, "budget_analysis": analysis}
    except Exception as exc:
        return {
            **state,
            "error": f"Budget analysis failed: {exc}",
        }


def itinerary_agent_node(
    state: TravelAgentState,
) -> TravelAgentState:
    """Node 3: Generate the day-by-day itinerary."""

    if state.get("error"):
        return state

    prompt = f"""
You are a professional AI travel planning agent.

TRIP DETAILS
Source: {state.get("source", "")}
Destination: {state.get("destination", "")}
Duration: {state.get("days", 1)} days
Total budget: INR {state.get("budget", 0)}
Travelers: {state.get("travelers", 1)}
Preferences: {state.get("preferences", [])}

MCP DATA
{json.dumps(state.get("tool_data", {}), ensure_ascii=False, indent=2, default=str)}

BUDGET ANALYSIS
{state.get("budget_analysis", "No budget analysis available.")}

Create a useful day-by-day itinerary with transport, accommodation,
food and activities.

Requirements:
- Use actual returned tool options when available.
- Never fabricate tool results, live weather, prices or availability.
- Clearly label costs as estimates unless verified by tool data.
- Give a cost breakdown and estimated total in INR.
- Explain whether the plan fits the budget.
- If important data is missing, explicitly say so.
- Never claim that a booking is confirmed.
- Use clear headings and practical suggestions.
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
    """Node 4: Review and improve the generated itinerary."""

    if state.get("error"):
        return state

    prompt = f"""
You are the final quality-review agent for a travel planning system.

User's budget: INR {state.get("budget", 0)}
Trip duration: {state.get("days", 1)} days
Travelers: {state.get("travelers", 1)}

Tool data:
{json.dumps(state.get("tool_data", {}), ensure_ascii=False, indent=2, default=str)}

Budget analysis:
{state.get("budget_analysis", "")}

Draft itinerary:
{state.get("itinerary", "")}

Review for:
1. Missing days or impractical sequencing.
2. Budget inconsistencies.
3. Unsupported claims about prices, weather or availability.
4. Claims that bookings have been confirmed.
5. Missing caveats about estimates.

Return two sections:
FINAL ITINERARY
Provide the corrected, user-ready itinerary.

REVIEW NOTES
Briefly list important limitations, missing information or budget concerns.

Do not invent live data or booking confirmations.
"""

    try:
        reviewed = ask_llm(prompt)
        return {
            **state,
            "itinerary": reviewed,
            "review_notes": "Final review completed.",
        }
    except Exception as exc:
        # Preserve the original itinerary if review fails.
        return {
            **state,
            "review_notes": f"Review unavailable: {exc}",
        }
