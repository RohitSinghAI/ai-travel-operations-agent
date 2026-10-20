
import json
from pathlib import Path
from typing import Any

DATA_FILE = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "activity_data.json"
)


def load_data() -> list[dict[str, Any]]:
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Activity data file not found: {DATA_FILE}"
        )

    raw = DATA_FILE.read_text(encoding="utf-8")

    if not raw.strip():
        raise ValueError(
            f"Activity data file is empty: {DATA_FILE}"
        )

    data = json.loads(raw)

    if not isinstance(data, list):
        raise ValueError(
            "activity_data.json must contain a JSON list."
        )

    return data

def search_activities(destination: str) -> list[dict[str, Any]]:
    data = load_data()

    destination_name = destination.split(",")[0].strip().casefold()

    return [
        item for item in data
        if item.get("city", "").split(",")[0].strip().casefold()
        == destination_name
    ]
