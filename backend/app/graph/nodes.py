
from backend.app.graph.state import TravelAgentState
from backend.app.integrations.groq_client import ask_llm


def plan_travel(state: TravelAgentState) -> TravelAgentState:
    prompt = f"""
You are an AI travel planning assistant.

Plan a trip using these details:
Source: {state.get("source", "")}
Destination: {state.get("destination", "")}
Duration: {state.get("days", 1)} days
Total budget: INR {state.get("budget", 0)}
Travelers: {state.get("travelers", 1)}
Preferences: {state.get("preferences", [])}

Requirements:
- Create a day-by-day itinerary.
- Include transport, hotels, food and activities.
- Give approximate costs in INR.
- Try to stay within the total budget.
- Mention that prices are estimates, not live quotes.
- Never claim that a booking is confirmed.
"""

    try:
        itinerary = ask_llm(prompt)
        return {**state, "itinerary": itinerary}
    except Exception as exc:
        return {
            **state,
            "error": f"Travel planning failed: {exc}",
        }
