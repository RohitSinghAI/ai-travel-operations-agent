import json
import os
from datetime import date
from typing import TypedDict, Any

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END

# Project root .env: backend/app/travel_graph.py se three levels up
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

MODEL_NAME = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


class TravelState(TypedDict, total=False):
    travel_request: dict
    transport_options: list[dict]
    hotel_options: list[dict]
    weather_info: dict
    activities: list[dict]
    budget_summary: dict
    review_result: dict
    errors: list[str]


def get_llm():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing from .env")

    return ChatGroq(
        model=MODEL_NAME,
        temperature=0.2,
    )


def transport_node(state: TravelState):
    request = state["travel_request"]
    travelers = request["travelers"]

    # Demonstration prices, not live quotes
    options = [
        {"mode": "Bus", "price_per_person": 1000, "duration_hours": 16},
        {"mode": "Train", "price_per_person": 1200, "duration_hours": 14},
        {"mode": "Flight", "price_per_person": 4500, "duration_hours": 1.5},
    ]

    for option in options:
        option["total_cost"] = option["price_per_person"] * travelers
        option["data_source"] = "DEMO"

    return {"transport_options": options}


def hotel_node(state: TravelState):
    request = state["travel_request"]
    nights = (
        date.fromisoformat(request["end_date"])
        - date.fromisoformat(request["start_date"])
    ).days

    options = [
        {"name": "Budget Guesthouse", "price_per_night": 1200, "rating": 3.8},
        {"name": "Beachside Hotel", "price_per_night": 2500, "rating": 4.3},
        {"name": "Premium Resort", "price_per_night": 5000, "rating": 4.7},
    ]

    for option in options:
        option["nights"] = nights
        # Assumption: one room is sufficient for this demo
        option["total_cost_for_group"] = option["price_per_night"] * nights
        option["data_source"] = "DEMO"

    return {"hotel_options": options}


def weather_node(state: TravelState):
    request = state["travel_request"]

    # Explicit placeholder: no live forecast connected here
    return {
        "weather_info": {
            "destination": request["destination"],
            "travel_dates": [
                request["start_date"],
                request["end_date"],
            ],
            "weather_summary": "Check the forecast closer to the travel dates.",
            "source": "DEMO - not a live forecast",
            "recommendation": "Verify the actual forecast before departure.",
        }
    }


def activities_node(state: TravelState):
    request = state["travel_request"]

    prompt = f"""
You are a travel activity planner.
Return ONLY a valid JSON array with exactly 3 activity objects.
Each object must have:
- name: string
- description: string
- estimated_cost_per_person: number

Create activities for this request:
{json.dumps(request, ensure_ascii=False)}

Use reasonable illustrative estimates in INR.
Do not claim prices are live or verified.
"""

    try:
        response = get_llm().invoke(prompt)
        content = response.content

        if not isinstance(content, str):
            content = str(content)

        # Some models wrap JSON in markdown fences
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0].strip()

        activities = json.loads(content)

        if not isinstance(activities, list) or not activities:
            raise ValueError("Expected a non-empty JSON array")

        for activity in activities:
            if (
                not isinstance(activity, dict)
                or not isinstance(activity.get("name"), str)
                or not isinstance(activity.get("description"), str)
                or not isinstance(activity.get("estimated_cost_per_person"), (int, float))
                or activity["estimated_cost_per_person"] < 0
            ):
                raise ValueError("Invalid activity format")

        return {"activities": activities}

    except Exception as exc:
        # Keep the workflow usable if LLM output fails
        return {
            "activities": [
                {
                    "name": "Local sightseeing",
                    "description": "Explore notable local attractions.",
                    "estimated_cost_per_person": 500,
                },
                {
                    "name": "Local food experience",
                    "description": "Try regional food at local eateries.",
                    "estimated_cost_per_person": 500,
                },
                {
                    "name": "Relaxation activity",
                    "description": "Enjoy a relaxed activity at the destination.",
                    "estimated_cost_per_person": 500,
                },
            ],
            "errors": [f"LLM activity generation fallback: {exc}"],
        }


def budget_node(state: TravelState):
    request = state["travel_request"]
    travelers = request["travelers"]
    budget = request["budget"]

    # Choose cheapest transport and hotel for a baseline budget
    transport = min(
        state["transport_options"],
        key=lambda item: item["total_cost"],
    )
    hotel = min(
        state["hotel_options"],
        key=lambda item: item["total_cost_for_group"],
    )

    # Select activities within remaining budget, using a simple greedy approach
    food_estimate = 3000
    local_transport_estimate = 1000

    fixed_cost = (
        transport["total_cost"]
        + hotel["total_cost_for_group"]
        + food_estimate
        + local_transport_estimate
    )
    remaining_for_activities = budget - fixed_cost

    selected_activities = []
    activity_total = 0

    for activity in sorted(
        state["activities"],
        key=lambda item: item["estimated_cost_per_person"],
    ):
        cost = activity["estimated_cost_per_person"] * travelers

        if activity_total + cost <= max(remaining_for_activities, 0):
            selected_activities.append(activity)
            activity_total += cost

    total = fixed_cost + activity_total

    return {
        "activities": selected_activities,
        "budget_summary": {
            "currency": request.get("currency", "INR"),
            "total_budget": budget,
            "transport_cost": transport["total_cost"],
            "hotel_cost": hotel["total_cost_for_group"],
            "activities_cost": activity_total,
            "food_estimate": food_estimate,
            "local_transport_estimate": local_transport_estimate,
            "estimated_total": total,
            "remaining_budget": budget - total,
            "within_budget": total <= budget,
            "note": "Illustrative estimates; food and local transport are fixed assumptions.",
        },
    }


def review_node(state: TravelState):
    summary = state["budget_summary"]
    issues = []

    if not summary["within_budget"]:
        issues.append("Estimated trip cost exceeds the budget.")

    issues.append("Transport and hotel prices are demonstration estimates.")
    issues.append("Weather information is not a live forecast.")

    return {
        "review_result": {
            "status": "NEEDS_REVIEW" if issues else "READY",
            "issues": issues,
            "verified_live_prices": False,
        }
    }


builder = StateGraph(TravelState)

builder.add_node("transport", transport_node)
builder.add_node("hotel", hotel_node)
builder.add_node("weather", weather_node)
builder.add_node("activities", activities_node)
builder.add_node("budget", budget_node)
builder.add_node("review", review_node)

builder.add_edge(START, "transport")
builder.add_edge("transport", "hotel")
builder.add_edge("hotel", "weather")
builder.add_edge("weather", "activities")
builder.add_edge("activities", "budget")
builder.add_edge("budget", "review")
builder.add_edge("review", END)

travel_graph = builder.compile()


def run_travel_graph(travel_request: dict) -> dict:
    result = travel_graph.invoke({
        "travel_request": travel_request,
        "errors": [],
    })
    return result