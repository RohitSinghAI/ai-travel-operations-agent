
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
            {
                "source": source,
                "destination": destination,
            },
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

    return {
        result["tool"]: result
        for result in results
    }


def plan_travel(
    state: TravelAgentState,
) -> TravelAgentState:
    try:
        # MCP tools are called before generating the itinerary.
        tool_data = asyncio.run(
            collect_travel_data(
                source=state.get("source", ""),
                destination=state.get("destination", ""),
            )
        )

        prompt = f"""
You are an AI travel planning assistant.

TRIP DETAILS
Source: {state.get("source", "")}
Destination: {state.get("destination", "")}
Duration: {state.get("days", 1)} days
Total budget: INR {state.get("budget", 0)}
Travelers: {state.get("travelers", 1)}
Preferences: {state.get("preferences", [])}

MCP TOOL RESULTS
{json.dumps(tool_data, ensure_ascii=False, indent=2, default=str)}

INSTRUCTIONS
1. Create a day-by-day travel itinerary.
2. Include transport, accommodation, food, and activities.
3. Estimate costs in INR and provide a total estimate.
4. Consider the number of travelers when estimating costs.
5. Try to stay within the supplied total budget.
6. Prefer options actually returned by the tools.
7. Never invent tool results, hotel availability, or live prices.
8. If tool data is missing or a tool fails, explain this clearly.
9. Any general suggestions must be labelled as suggestions.
10. Clearly state that costs are estimates, not live quotes.
11. Never claim that a booking has been confirmed.
12. Mention whether the estimated total fits the budget.
13. Reply in a clear, easy-to-read format.
"""

        itinerary = ask_llm(prompt)

        return {
            **state,
            "tool_data": tool_data,
            "itinerary": itinerary,
        }

    except Exception as exc:
        return {
            **state,
            "error": f"Travel planning failed: {exc}",
        }
