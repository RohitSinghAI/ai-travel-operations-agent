
from typing import Any, TypedDict


class TravelAgentState(TypedDict, total=False):
    source: str
    destination: str
    days: int
    budget: float
    travelers: int
    preferences: list[str]
    tool_data: dict[str, Any]
    itinerary: str
    error: str
