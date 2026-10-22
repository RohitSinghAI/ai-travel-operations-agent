
from datetime import date
from typing import Any

from pydantic import BaseModel, Field, model_validator


class TravelRequest(BaseModel):
    source: str = Field(min_length=2, max_length=100)
    destination: str = Field(min_length=2, max_length=100)

    start_date: date
    end_date: date

    travelers: int = Field(ge=1, le=20)
    budget: float = Field(gt=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    preferences: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")

        trip_nights = (self.end_date - self.start_date).days

        if trip_nights > 30:
            raise ValueError("Trip cannot exceed 30 nights")

        return self


class TravelResponse(BaseModel):
    status: str
    source: str
    destination: str
    itinerary: str
    budget: float
    days: int
    travelers: int

    start_date: date | None = None
    end_date: date | None = None

    tool_data: dict[str, Any] = Field(default_factory=dict)
    budget_breakdown: dict[str, Any] = Field(default_factory=dict)
    budget_analysis: str = ""
    review_notes: str = ""

    transport_options: dict[str, Any] = Field(default_factory=dict)
    hotel_options: dict[str, Any] = Field(default_factory=dict)
    activity_options: dict[str, Any] = Field(default_factory=dict)
    weather_summary: dict[str, Any] = Field(default_factory=dict)
