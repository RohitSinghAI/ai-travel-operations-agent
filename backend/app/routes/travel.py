
from fastapi import APIRouter, HTTPException

from backend.app.schemas import TravelRequest, TravelResponse
from backend.app.services.travel_service import generate_travel_plan

router = APIRouter(prefix="/api/travel", tags=["Travel"])


@router.post("/plan", response_model=TravelResponse)
def create_travel_plan(request: TravelRequest):
    try:
        # Validate trip dates when both dates are provided.
        if request.check_in and request.check_out:
            if request.check_out <= request.check_in:
                raise HTTPException(
                    status_code=422,
                    detail="Check-out date must be after check-in date.",
                )

        # Pass the complete request, including dates,
        # to the travel planning service.
        return generate_travel_plan(request)

    except HTTPException:
        raise

    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        # Keep the full error in the backend terminal for debugging.
        import logging

        logging.exception("Travel planning failed")

        raise HTTPException(
            status_code=500,
            detail="Travel planning failed. Check backend logs.",
        ) from exc
