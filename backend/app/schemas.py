
from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TravelRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    # Trip details
    source: str = Field(min_length=2, max_length=100)
    destination: str = Field(min_length=2, max_length=100)

    days: int = Field(ge=1, le=30)
    budget: float = Field(gt=0)
    travelers: int = Field(default=1, ge=1, le=50)
    preferences: list[str] = Field(default_factory=list)

    # Hotel search and travel dates
    check_in: date
    check_out: date

    @model_validator(mode="after")
    def validate_trip_dates(self):
        if self.check_out <= self.check_in:
            raise ValueError("check_out must be after check_in")

        if (self.check_out - self.check_in).days > 30:
            raise ValueError("Hotel stay cannot exceed 30 nights")

        return self


class TravelResponse(BaseModel):
    status: str
    source: str
    destination: str
    itinerary: str
    budget: float
    days: int
    travelers: int

    # Return selected trip dates to the frontend
    check_in: date | None = None
    check_out: date | None = None

    # Additional travel planning results
    tool_data: dict[str, Any] = Field(default_factory=dict)
    budget_breakdown: dict[str, Any] = Field(default_factory=dict)
    budget_analysis: str = ""
    review_notes: str = ""
