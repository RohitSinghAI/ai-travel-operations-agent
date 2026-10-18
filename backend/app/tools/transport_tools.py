
import json
from pathlib import Path
from typing import Any

DATA_FILE = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "transport_data.json"
)


def load_data() -> list[dict[str, Any]]:
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Transport data file not found: {DATA_FILE}"
        )

    raw = DATA_FILE.read_text(encoding="utf-8")

    if not raw.strip():
        raise ValueError(
            f"Transport data file is empty: {DATA_FILE}"
        )

    data = json.loads(raw)

    if not isinstance(data, list):
        raise ValueError(
            "transport_data.json must contain a JSON list."
        )

    return data


def search_transport(
    source: str,
    destination: str,
) -> list[dict[str, Any]]:
    data = load_data()

    return [
        item
        for item in data
        if item.get("source", "").strip().casefold()
        == source.strip().casefold()
        and item.get("destination", "").strip().casefold()
        == destination.strip().casefold()
    ]
