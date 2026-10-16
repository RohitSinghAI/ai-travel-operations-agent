
from fastapi import APIRouter, HTTPException

from backend.app.schemas import TravelRequest, TravelResponse
from backend.app.services.travel_service import generate_travel_plan

router = APIRouter(prefix="/api/travel", tags=["Travel"])


@router.post("/plan", response_model=TravelResponse)
def create_travel_plan(request: TravelRequest):
    try:
        return generate_travel_plan(request)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Travel planning failed. Check backend logs.",
        ) from exc
