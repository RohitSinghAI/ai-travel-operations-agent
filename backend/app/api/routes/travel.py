
import logging

from fastapi import APIRouter, HTTPException

from backend.app.schemas import TravelRequest, TravelResponse
from backend.app.services.travel_service import generate_travel_plan

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/travel",
    tags=["Travel"],
)


@router.post("/plan", response_model=TravelResponse)
def create_travel_plan(request: TravelRequest) -> TravelResponse:
    try:
        result = generate_travel_plan(request)
        return TravelResponse(**result)

    except RuntimeError as exc:
        logger.warning("Travel workflow failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception("Unexpected travel planning error")
        raise HTTPException(
            status_code=500,
            detail="Travel planning failed. Check backend logs.",
        ) from exc
