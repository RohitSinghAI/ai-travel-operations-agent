
import json
from pathlib import Path
from typing import Any

DATA_FILE = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "hotel_data.json"
)


def load_data() -> list[dict[str, Any]]:
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Hotel data file not found: {DATA_FILE}"
        )

    raw = DATA_FILE.read_text(encoding="utf-8")

    if not raw.strip():
        raise ValueError(
            f"Hotel data file is empty: {DATA_FILE}"
        )

    data = json.loads(raw)

    if not isinstance(data, list):
        raise ValueError(
            "hotel_data.json must contain a JSON list."
        )

    return data


def search_hotels(
    destination: str,
) -> list[dict[str, Any]]:
    data = load_data()

    return [
        item
        for item in data
        if item.get("city", "").strip().casefold()
        == destination.strip().casefold()
    ]
