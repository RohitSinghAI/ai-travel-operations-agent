
from typing import Any


def run_transport_agent(
    transport_data: dict[str, Any],
    budget: float,
    travelers: int = 1,
    max_results: int = 5,
) -> dict[str, Any]:
    """
    Filter and rank available train and bus options.

    The input must come from an existing transport provider
    or MCP tool. This function does not fetch live data.
    """

    if budget <= 0:
        raise ValueError("Budget must be greater than zero.")

    if travelers < 1:
        raise ValueError("Travelers must be at least one.")

    if max_results < 1:
        raise ValueError("max_results must be at least one.")

    if not isinstance(transport_data, dict):
        return {
            "status": "unavailable",
            "message": "Transport data must be a dictionary.",
            "options": [],
            "count": 0,
        }

    # Accept either {"result": [...]} or {"options": [...]}.
    raw_options = transport_data.get(
        "options", transport_data.get("result", [])
    )

    # Some MCP responses wrap the result inside another dictionary.
    if isinstance(raw_options, dict):
        raw_options = raw_options.get(
            "result", raw_options.get("options", [])
        )

    if not isinstance(raw_options, list):
        raw_options = []

    options = []

    for item in raw_options:
        if not isinstance(item, dict):
            continue

        mode = str(
            item.get("mode", item.get("type", ""))
        ).strip().lower()

        # Exclude flights as requested.
        if mode not in {"train", "bus"}:
            continue

        raw_price = item.get(
            "total_price",
            item.get("price"),
        )

        try:
            price = float(raw_price)
        except (TypeError, ValueError):
            continue

        if price < 0:
            continue

        currency = str(item.get("currency", "INR")).upper()

        options.append({
            "mode": mode,
            "provider": item.get("provider", "Unknown"),
            "name": item.get(
                "name",
                item.get("service_name", "Unnamed service"),
            ),
            "price": price,
            "currency": currency,
            "departure": item.get("departure"),
            "arrival": item.get("arrival"),
            "duration": item.get("duration"),
            "status": item.get("status", "unknown"),
            "is_live": item.get("is_live", False),
        })

    # Compare only INR amounts; never mix currencies.
    options = [
        option for option in options
        if option["currency"] == "INR"
    ]

    options.sort(key=lambda option: option["price"])

    return {
        "status": (
            transport_data.get("status", "unknown")
            if options else "unavailable"
        ),
        "budget": budget,
        "travelers": travelers,
        "options": options[:max_results],
        "count": len(options),
        "message": (
            "Train and bus options sorted by listed price."
            if options
            else "No usable train or bus prices were returned."
        ),
    }
