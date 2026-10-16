
import json
from pathlib import Path


DATA_FILE = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "transport_data.json"
)


def search_transport(source: str, destination: str) -> list[dict]:
    """Search sample transport options between two cities."""
    if not DATA_FILE.exists():
        return []

    with DATA_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict):
        options = data.get("transport", data.get("options", []))
    elif isinstance(data, list):
        options = data
    else:
        return []

    source = source.strip().casefold()
    destination = destination.strip().casefold()

    results = []
    for option in options:
        if not isinstance(option, dict):
            continue

        origin = str(option.get("source", "")).casefold()
        target = str(option.get("destination", "")).casefold()

        if origin == source and target == destination:
            results.append(option)

    return results
