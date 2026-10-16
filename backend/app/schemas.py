
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TravelRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    source: str = Field(min_length=2, max_length=100)
    destination: str = Field(min_length=2, max_length=100)
    days: int = Field(ge=1, le=30)
    budget: float = Field(gt=0)
    travelers: int = Field(default=1, ge=1, le=50)
    preferences: list[str] = Field(default_factory=list)


class TravelResponse(BaseModel):
    status: str
    source: str
    destination: str
    itinerary: str
    budget: float
    days: int
    travelers: int
    tool_data: dict[str, Any] = Field(default_factory=dict)
    budget_breakdown: dict[str, Any] = Field(default_factory=dict)
    budget_analysis: str = ""
    review_notes: str = ""
