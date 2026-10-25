
import logging

from fastapi import APIRouter, HTTPException

from backend.app.schemas import TravelRequest, TravelResponse
from backend.app.services.travel_service import generate_travel_plan

logger = logging.getLogger(__name__)

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

        # Generate the travel plan.
        result = generate_travel_plan(request)

        if result is None:
            raise RuntimeError(
                "generate_travel_plan returned None. "
                "Check travel_service.py return statement."
            )

        # Validate the response against the Pydantic response schema.
        return TravelResponse(**result)

    except HTTPException:
        raise

    except RuntimeError as exc:
        logger.exception("Travel planning runtime error")
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception("Travel planning failed")
        raise HTTPException(
            status_code=500,
            detail="Travel planning failed. Check backend logs.",
        ) from exc
