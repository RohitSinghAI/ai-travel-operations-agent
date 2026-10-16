
import json
from pathlib import Path


DATA_FILE = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "hotel_data.json"
)


def search_hotels(destination: str) -> list[dict]:
    """Search sample hotels by destination city."""
    if not DATA_FILE.exists():
        return []

    with DATA_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict):
        hotels = data.get("hotels", data.get("options", []))
    elif isinstance(data, list):
        hotels = data
    else:
        return []

    city = destination.strip().casefold()

    return [
        hotel
        for hotel in hotels
        if isinstance(hotel, dict)
        and str(hotel.get("city", hotel.get("destination", "")))
        .casefold() == city
    ]
