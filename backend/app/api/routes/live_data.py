
from fastapi import APIRouter, HTTPException, Query

from backend.app.services.live_travel_data import (
    LiveDataError,
    geocode_city,
    get_live_weather,
    get_tourist_places,
)

router = APIRouter(prefix="/api/live", tags=["Live Travel Data"])


def _handle_error(exc: Exception) -> None:
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if isinstance(exc, LiveDataError):
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    raise HTTPException(
        status_code=502,
        detail="Live travel-data provider failed.",
    ) from exc


@router.get("/cities")
async def search_cities(
    q: str = Query(..., min_length=2, max_length=100),
):
    try:
        return await geocode_city(q)
    except Exception as exc:
        _handle_error(exc)


@router.get("/weather")
async def city_weather(
    city: str = Query(..., min_length=2, max_length=100),
):
    try:
        return await get_live_weather(city)
    except Exception as exc:
        _handle_error(exc)


@router.get("/places")
async def city_places(
    city: str = Query(..., min_length=2, max_length=100),
    radius_m: int = Query(10000, ge=1000, le=30000),
    limit: int = Query(20, ge=1, le=50),
):
    try:
        return await get_tourist_places(
            city=city,
            radius_m=radius_m,
            limit=limit,
        )
    except Exception as exc:
        _handle_error(exc)
