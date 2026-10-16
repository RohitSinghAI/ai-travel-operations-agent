
import json
from typing import Any


def _extract_records(tool_result: Any) -> list[dict[str, Any]]:
    """Normalize MCP results into a list of dictionaries."""

    if isinstance(tool_result, dict):
        if tool_result.get("error"):
            return []

        result = tool_result.get("result", tool_result)

        if isinstance(result, dict):
            # MCP structured content can wrap the returned list.
            for key in ("data", "items", "results", "options"):
                if isinstance(result.get(key), list):
                    result = result[key]
                    break
            else:
                return [result]

        if isinstance(result, list):
            records = []
            for item in result:
                if isinstance(item, dict) and "text" in item:
                    try:
                        parsed = json.loads(item["text"])
                        if isinstance(parsed, list):
                            records.extend(
                                x for x in parsed if isinstance(x, dict)
                            )
                        elif isinstance(parsed, dict):
                            records.append(parsed)
                    except (json.JSONDecodeError, TypeError):
                        continue
                elif isinstance(item, dict):
                    records.append(item)
            return records

    if isinstance(tool_result, list):
        return [item for item in tool_result if isinstance(item, dict)]

    return []


def _get_records(tool_data: dict[str, Any], tool_name: str):
    return _extract_records(tool_data.get(tool_name, {}))


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
    Calculate an illustrative trip budget from available tool records.

    Tool data may contain sample records, not live quotes.
    Missing prices are not silently treated as verified zero-cost options.
    """

    nights = max(days - 1, 0)

    transport_records = _get_records(tool_data, "find_transport")
    hotel_records = _get_records(tool_data, "find_hotels")
    activity_records = _get_records(tool_data, "find_activities")

    warnings: list[str] = []

    # Use the first returned transport option with a usable price.
    transport_option = next(
        (
            item for item in transport_records
            if isinstance(item.get("price_per_person"), (int, float))
        ),
        None,
    )

    if transport_option:
        transport_price = float(transport_option["price_per_person"])
        trip_type = str(transport_option.get("trip_type", "")).lower()

        if trip_type == "round_trip":
            transport_total = transport_price * travelers
        else:
            # Unknown trip type: do not assume that a one-way price
            # includes the return journey.
            transport_total = transport_price * travelers * 2
            warnings.append(
                "Transport trip type was not specified; a round-trip "
                "estimate was calculated using twice the listed fare."
            )

        transport_source = (
            "Sample tool record; not a live fare or booking."
        )
    else:
        transport_total = None
        transport_source = "No usable transport price returned."
        warnings.append("Transport price is unavailable.")

    hotel_option = next(
        (
            item for item in hotel_records
            if isinstance(
                item.get("estimated_price_per_night"), (int, float)
            )
        ),
        None,
    )

    if hotel_option:
        nightly_rate = float(hotel_option["estimated_price_per_night"])
        hotel_total = nightly_rate * nights
        hotel_source = (
            "Sample tool record; not verified hotel availability."
        )
    else:
        hotel_total = None
        hotel_source = "No usable accommodation price returned."
        warnings.append("Accommodation price is unavailable.")

    food_total = food_per_person_per_day * travelers * days

    # Food-category records are excluded to avoid double-counting meals.
    payable_activities = [
        item for item in activity_records
        if str(item.get("category", "")).lower() != "food"
        and isinstance(
            item.get("estimated_cost_per_person"), (int, float)
        )
    ]

    activity_total = sum(
        float(item["estimated_cost_per_person"]) * travelers
        for item in payable_activities
    )

    if not activity_records:
        warnings.append(
            "No activity records were returned; activity cost may be "
            "incomplete."
        )

    known_subtotal = food_total + activity_total

    if transport_total is not None:
        known_subtotal += transport_total

    if hotel_total is not None:
        known_subtotal += hotel_total

    # If essential prices are missing, this is only a partial estimate.
    essential_prices_complete = (
        transport_total is not None and hotel_total is not None
    )

    contingency = round(known_subtotal * contingency_rate, 2)
    estimated_total = round(known_subtotal + contingency, 2)

    return {
        "currency": "INR",
        "travelers": travelers,
        "days": days,
        "nights": nights,
        "user_budget": round(budget, 2),
        "line_items": {
            "transport": {
                "amount": transport_total,
                "source": transport_source,
            },
            "accommodation": {
                "amount": hotel_total,
                "source": hotel_source,
            },
            "food": {
                "amount": round(food_total, 2),
                "source": (
                    f"Illustrative assumption: ₹{food_per_person_per_day}"
                    " per person per day."
                ),
            },
            "activities": {
                "amount": round(activity_total, 2),
                "source": (
                    "Sum of priced non-food activity records; "
                    "records are not live quotes."
                ),
            },
            "contingency": {
                "amount": contingency,
                "rate": contingency_rate,
            },
        },
        "known_subtotal": round(known_subtotal, 2),
        "estimated_total": estimated_total,
        "essential_prices_complete": essential_prices_complete,
        "budget_remaining": round(budget - estimated_total, 2),
        "within_budget_based_on_known_costs": (
            estimated_total <= budget
        ),
        "warnings": warnings,
        "is_live_quote": False,
    }
