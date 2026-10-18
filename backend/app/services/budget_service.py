
import json
import math
from typing import Any


def _extract_records(tool_result: Any) -> list[dict[str, Any]]:
    """Normalize nested MCP responses into a list of records."""

    if isinstance(tool_result, list):
        records = []
        for item in tool_result:
            if isinstance(item, dict) and "text" in item:
                try:
                    parsed = json.loads(item["text"])
                    records.extend(_extract_records(parsed))
                except (json.JSONDecodeError, TypeError):
                    continue
            elif isinstance(item, dict):
                records.extend(_extract_records(item))
        return records

    if not isinstance(tool_result, dict):
        return []

    if tool_result.get("error"):
        return []

    # Unwrap common MCP response containers.
    for key in ("structuredContent", "structured_content", "data",
                "items", "results", "options"):
        value = tool_result.get(key)
        if isinstance(value, (dict, list)):
            return _extract_records(value)

    # MCP tools sometimes return {"result": {"result": [...]}}.
    nested = tool_result.get("result")
    if isinstance(nested, (dict, list)):
        return _extract_records(nested)

    # Ignore status-only or error-only responses.
    if set(tool_result).issubset({"status", "tool", "error", "message"}):
        return []

    return [tool_result]


def _get_records(
    tool_data: dict[str, Any],
    tool_name: str,
) -> list[dict[str, Any]]:
    return _extract_records(tool_data.get(tool_name, {}))


def _number(value: Any) -> float | None:
    """Convert a valid non-negative price to a finite float."""
    if isinstance(value, bool) or value is None:
        return None

    try:
        number = float(value)
    except (ValueError, TypeError):
        return None

    if not math.isfinite(number) or number < 0:
        return None

    return number


def _first_price(
    records: list[dict[str, Any]],
    fields: tuple[str, ...],
) -> tuple[dict[str, Any] | None, float | None]:
    """Find the first record with a usable price."""
    for record in records:
        for field in fields:
            price = _number(record.get(field))
            if price is not None:
                return record, price
    return None, None


def calculate_budget(
    *,
    tool_data: dict[str, Any],
    travelers: int,
    days: int,
    budget: float,
    food_per_person_per_day: float = 400,
    contingency_rate: float = 0.10,
) -> dict[str, Any]:
    """
    Calculate a transparent estimated trip budget.

    Returned prices may be sample data. This function does not
    confirm live prices, availability, or bookings.
    """

    travelers = max(1, int(travelers))
    days = max(1, int(days))
    nights = max(days - 1, 0)

    budget_value = _number(budget)
    if budget_value is None:
        raise ValueError("Budget must be a valid non-negative number.")

    food_rate = _number(food_per_person_per_day)
    if food_rate is None:
        raise ValueError("Food estimate must be non-negative.")

    contingency_value = _number(contingency_rate)
    if contingency_value is None or contingency_value > 1:
        raise ValueError("Contingency rate must be between 0 and 1.")

    tool_data = tool_data if isinstance(tool_data, dict) else {}

    transport_records = _get_records(tool_data, "find_transport")
    hotel_records = _get_records(tool_data, "find_hotels")
    activity_records = _get_records(tool_data, "find_activities")

    warnings: list[str] = []

    # Transport
    transport_option, transport_price = _first_price(
        transport_records,
        ("price_per_person", "estimated_price_per_person", "price"),
    )

    if transport_option is not None and transport_price is not None:
        trip_type = str(
            transport_option.get("trip_type", "")
        ).strip().lower()

        if trip_type in {"round_trip", "return", "roundtrip"}:
            transport_total = transport_price * travelers
        elif trip_type in {"one_way", "one-way", "single"}:
            transport_total = transport_price * travelers * 2
            warnings.append(
                "Transport fare is one-way; estimated return fare uses "
                "the same amount and is not a confirmed quote."
            )
        else:
            transport_total = transport_price * travelers * 2
            warnings.append(
                "Transport trip type is unknown; a round-trip estimate "
                "uses twice the listed per-person fare."
            )

        transport_source = (
            "Source record; not a confirmed live fare or booking."
        )
    else:
        transport_total = None
        transport_source = "No usable transport price returned."
        warnings.append("Transport price is unavailable.")

    # Accommodation
    hotel_option, nightly_rate = _first_price(
        hotel_records,
        (
            "estimated_price_per_night",
            "price_per_night",
            "nightly_rate",
        ),
    )

    if hotel_option is not None and nightly_rate is not None:
        hotel_total = nightly_rate * nights
        hotel_source = (
            "Source record multiplied by trip nights; availability "
            "and room occupancy are not confirmed."
        )
    else:
        hotel_total = None
        hotel_source = "No usable accommodation price returned."
        warnings.append("Accommodation price is unavailable.")

    # Food estimate
    food_total = food_rate * travelers * days

    # Activities: sum priced non-food records only.
    activity_total = 0.0
    priced_activity_count = 0

    for item in activity_records:
        if str(item.get("category", "")).strip().lower() == "food":
            continue

        price = _number(item.get("estimated_cost_per_person"))
        if price is None:
            price = _number(item.get("price_per_person"))

        if price is not None:
            activity_total += price * travelers
            priced_activity_count += 1

    if not activity_records:
        warnings.append(
            "No activity records were returned; activity costs "
            "may be incomplete."
        )
    elif priced_activity_count == 0:
        warnings.append(
            "No usable activity prices were returned; activities "
            "may cost more than the calculated amount."
        )

    # Sum only known costs; never silently convert missing essentials to zero.
    known_subtotal = food_total + activity_total

    if transport_total is not None:
        known_subtotal += transport_total

    if hotel_total is not None:
        known_subtotal += hotel_total

    essential_prices_complete = (
        transport_total is not None and hotel_total is not None
    )

    contingency = round(known_subtotal * contingency_value, 2)
    estimated_total = round(known_subtotal + contingency, 2)

    if not essential_prices_complete:
        warnings.append(
            "Estimated total is partial, not the complete trip cost. "
            "Obtain transport and accommodation prices before deciding "
            "whether the trip fits the budget."
        )

    within_budget = (
        estimated_total <= budget_value
        if essential_prices_complete
        else None
    )

    return {
        "currency": "INR",
        "travelers": travelers,
        "days": days,
        "nights": nights,
        "user_budget": round(budget_value, 2),
        "line_items": {
            "transport": {
                "amount": (
                    round(transport_total, 2)
                    if transport_total is not None else None
                ),
                "source": transport_source,
            },
            "accommodation": {
                "amount": (
                    round(hotel_total, 2)
                    if hotel_total is not None else None
                ),
                "source": hotel_source,
            },
            "food": {
                "amount": round(food_total, 2),
                "source": (
                    f"Illustrative estimate: ₹{food_rate:g} per "
                    "person per day."
                ),
            },
            "activities": {
                "amount": round(activity_total, 2),
                "priced_records": priced_activity_count,
                "source": (
                    "Sum of priced non-food activity records; "
                    "not confirmed live quotes."
                ),
            },
            "contingency": {
                "amount": contingency,
                "rate": contingency_value,
            },
        },
        "known_subtotal": round(known_subtotal, 2),
        "estimated_total": estimated_total,
        "essential_prices_complete": essential_prices_complete,
        # This is only a provisional balance when prices are missing.
        "budget_remaining": round(budget_value - estimated_total, 2),
        "budget_remaining_is_final": essential_prices_complete,
        "within_budget_based_on_known_costs": (
            estimated_total <= budget_value
        ),
        "within_budget": within_budget,
        "warnings": warnings,
        "is_live_quote": False,
    }
