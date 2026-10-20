from fastapi import APIRouter, HTTPException
from backend.app.schemas import TravelRequest, TravelResponse
from backend.app.services.travel_service import generate_travel_plan

router = APIRouter()


@router.post("/plan", response_model=TravelResponse)
def create_travel_plan(request: TravelRequest):
    try:
        result = generate_travel_plan(request)

        if result is None:
            raise RuntimeError(
                "generate_travel_plan returned None. "
                "Check travel_service.py return statement."
            )

        return TravelResponse(**result)

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc