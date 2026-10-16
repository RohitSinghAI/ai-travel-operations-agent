
from pydantic import BaseModel, Field


class TravelRequest(BaseModel):
    source: str = Field(
        min_length=2,
        max_length=100,
        description="Starting city"
    )
    destination: str = Field(
        min_length=2,
        max_length=100,
        description="Destination city"
    )
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
