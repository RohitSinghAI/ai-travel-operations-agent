
from typing import Any, TypedDict


class TravelAgentState(TypedDict, total=False):
    # Trip details
    source: str
    destination: str
    days: int
    budget: float
    currency: str
    travelers: int
    preferences: list[str]

    # Trip dates
    start_date: str
    end_date: str

    # Raw MCP and live-provider responses
    tool_data: dict[str, Any]

    # Specialist agent results
    transport_options: dict[str, Any]
    hotel_options: dict[str, Any]
    activity_options: dict[str, Any]
    weather_summary: dict[str, Any]

    # Budget agent results
    budget_breakdown: dict[str, Any]
    budget_analysis: str

    # Final itinerary and review
    itinerary: str
    review_notes: str

    # Error handling
    error: str
