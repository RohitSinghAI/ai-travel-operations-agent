
import json
from pathlib import Path


DATA_FILE = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "activity_data.json"
)


def search_activities(destination: str) -> list[dict]:
    """Search sample activities by destination city."""
    if not DATA_FILE.exists():
        return []

    with DATA_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict):
        activities = data.get("activities", data.get("options", []))
    elif isinstance(data, list):
        activities = data
    else:
        return []

    city = destination.strip().casefold()

    return [
        activity
        for activity in activities
        if isinstance(activity, dict)
        and str(activity.get("city", activity.get("destination", "")))
        .casefold() == city
    ]
