
from typing import TypedDict


class TravelAgentState(TypedDict, total=False):
    source: str
    destination: str
    days: int
    budget: float
    travelers: int
    preferences: list[str]
    itinerary: str
    error: str
