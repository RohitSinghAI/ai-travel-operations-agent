
from typing import Any


def _extract_options(transport_data: dict[str, Any]) -> list:
    """Support direct lists and nested MCP/tool result formats."""

    raw_options = transport_data.get("options")

    if raw_options is None:
        raw_options = transport_data.get("result", [])

    # Support {"result": {"result": [...]}}
    for _ in range(3):
        if isinstance(raw_options, list):
            return raw_options

        if not isinstance(raw_options, dict):
            return []

        if isinstance(raw_options.get("options"), list):
            return raw_options["options"]

        if "result" in raw_options:
            raw_options = raw_options["result"]
        else:
            return []

    return raw_options if isinstance(raw_options, list) else []


def run_transport_agent(
    transport_data: dict[str, Any],
    budget: float,
    travelers: int = 1,
    max_results: int = 5,
) -> dict[str, Any]:
    """
    Normalize train and bus options.

    Missing prices are preserved as None.
    Sample data is never presented as a live quote.
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

    raw_options = _extract_options(transport_data)
    options = []

    for item in raw_options:
        if not isinstance(item, dict):
            continue

        mode = str(
            item.get("mode", item.get("type", ""))
        ).strip().lower()

        if mode not in {"train", "bus"}:
            continue

        currency = str(item.get("currency") or "INR").upper()

        # Prefer an explicitly declared total fare.
        raw_total = item.get("total_price")
        raw_per_person = item.get("price_per_person")
        raw_price = item.get("price")

        price = None
        total_price = None
        price_basis = "unavailable"

        try:
            if raw_total is not None:
                total_price = float(raw_total)
                price = total_price
                price_basis = "total"

            elif raw_per_person is not None:
                price = float(raw_per_person)
                total_price = price * travelers
                price_basis = "per_person"

            elif raw_price is not None:
                price = float(raw_price)

                # Do not guess whether a generic price is per person
                # or for all travellers.
                price_basis = str(
                    item.get("price_basis", "unspecified")
                ).strip().lower()

                if price_basis in {"per_person", "per-person"}:
                    total_price = price * travelers
                    price_basis = "per_person"
                elif price_basis in {"total", "group", "all_travelers"}:
                    total_price = price
                    price_basis = "total"

        except (TypeError, ValueError):
            price = None
            total_price = None
            price_basis = "unavailable"

        if price is not None and price < 0:
            continue

        if total_price is not None and total_price < 0:
            continue

        is_live = item.get("is_live", False) is True

        options.append({
            "mode": mode,
            "provider": item.get("provider", "Unknown"),
            "name": item.get(
                "name",
                item.get("service_name", "Unnamed service"),
            ),
            "price": price,
            "total_price": total_price,
            "price_basis": price_basis,
            "currency": currency,
            "departure": item.get("departure"),
            "arrival": item.get("arrival"),
            "duration": item.get("duration"),
            "source_status": item.get("status", "unknown"),
            "is_live": is_live,
            "price_available": price is not None,
            "within_budget": (
                total_price <= budget
                if total_price is not None and currency == "INR"
                else None
            ),
        })

    # Do not compare prices in different currencies.
    inr_options = [
        option for option in options
        if option["currency"] == "INR"
    ]

    # Known fares first; unknown fares are still shown.
    inr_options.sort(
        key=lambda option: (
            option["total_price"] is None,
            option["total_price"]
            if option["total_price"] is not None
            else float("inf"),
        )
    )

    selected = inr_options[:max_results]
    known_prices = [
        option for option in selected
        if option["total_price"] is not None
    ]

    if not selected:
        status = "unavailable"
        message = "No train or bus options were returned with usable INR records."
    elif not known_prices:
        status = "partial"
        message = (
            "Train and bus options were found, but fares are unavailable. "
            "Confirm prices with the transport provider."
        )
    elif len(known_prices) < len(selected):
        status = "partial"
        message = (
            "Some options have prices; others require fare confirmation."
        )
    else:
        status = "success"
        message = "Train and bus options normalized and sorted by total fare."

    return {
        "status": status,
        "budget": budget,
        "travelers": travelers,
        "options": selected,
        "count": len(selected),
        "priced_count": len(known_prices),
        "unpriced_count": len(selected) - len(known_prices),
        "is_live_quote": any(
            option["is_live"] for option in known_prices
        ),
        "message": message,
    }
