from datetime import date
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
        return self