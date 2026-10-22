
import json
import math
from datetime import date, datetime
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

    for key in (
        "structuredContent",
        "structured_content",
        "data",
        "items",
        "results",
        "options",
    ):
        value = tool_result.get(key)
        if isinstance(value, (dict, list)):
            return _extract_records(value)

    nested = tool_result.get("result")
    if isinstance(nested, (dict, list)):
        return _extract_records(nested)

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


def _parse_date(value: Any) -> date | None:
    """Parse date, datetime, or ISO-formatted date strings."""

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None

    return None


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
    start_date: Any = None,
    end_date: Any = None,
    food_per_person_per_day: float = 400,
    contingency_rate: float = 0.10,
) -> dict[str, Any]:
    """
    Calculate a transparent estimated trip budget.

    If start_date and end_date are supplied, calculate nights from
    those dates. The end date is the checkout/departure date and is
    excluded from the overnight stay count.

    Prices may be sample data. This function does not confirm live
    prices, availability, or bookings.
    """

    travelers = max(1, int(travelers))
    days = max(1, int(days))

    parsed_start = _parse_date(start_date)
    parsed_end = _parse_date(end_date)

    if start_date is not None and parsed_start is None:
        raise ValueError("start_date must be a valid date.")

    if end_date is not None and parsed_end is None:
        raise ValueError("end_date must be a valid date.")

    if parsed_start is not None and parsed_end is not None:
        if parsed_end <= parsed_start:
            raise ValueError("end_date must be after start_date.")

        nights = (parsed_end - parsed_start).days

        # Keep the supplied duration consistent with the dates.
        expected_days = nights
        if days != expected_days:
            raise ValueError(
                f"Trip duration mismatch: days={days}, but the supplied "
                f"dates represent {expected_days} nights/days."
            )
    else:
        # Fallback for callers that do not provide dates.
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

    # --------------------------------------------------
    # 1. Transport
    # --------------------------------------------------
    transport_total = None
    transport_source = "No usable transport price returned."

    for record in transport_records:
        currency = str(record.get("currency") or "INR").upper()
        if currency != "INR":
            continue

        trip_type = str(record.get("trip_type", "")).strip().lower()
        fare_basis = str(record.get("price_basis", "")).strip().lower()

        # Prefer an explicit total fare or explicit per-person fare.
        total_fare = _number(record.get("total_price"))
        per_person_fare = _number(
            record.get("price_per_person")
        )
        if per_person_fare is None:
            per_person_fare = _number(
                record.get("estimated_price_per_person")
            )

        if total_fare is not None:
            if trip_type in {"one_way", "one-way", "single"}:
                candidate_total = total_fare * 2
                source_note = (
                    "Listed total fare treated as one-way and doubled "
                    "for return; return fare is not confirmed."
                )
                warnings.append(source_note)
            else:
                candidate_total = total_fare
                if trip_type not in {"round_trip", "return", "roundtrip"}:
                    warnings.append(
                        "Transport fare basis is not explicit; the listed "
                        "total is used without assuming a return fare."
                    )

            transport_total = candidate_total
            transport_source = (
                "Source record; not a confirmed live fare or booking."
            )
            break

        if per_person_fare is not None:
            candidate_total = per_person_fare * travelers

            if trip_type in {"one_way", "one-way", "single"}:
                candidate_total *= 2
                warnings.append(
                    "Transport fare is one-way; return estimate assumes "
                    "the same fare and is not a confirmed quote."
                )
            elif trip_type not in {"round_trip", "return", "roundtrip"}:
                warnings.append(
                    "Transport trip type is unknown; listed per-person fare "
                    "is multiplied by travelers but return travel is not included."
                )

            transport_total = candidate_total
            transport_source = (
                "Source per-person fare multiplied by travelers; "
                "not a confirmed live fare or booking."
            )
            break

        # A generic `price` is ambiguous unless the source declares its basis.
        generic_price = _number(record.get("price"))
        if generic_price is None:
            continue

        if fare_basis in {"per_person", "per-person"}:
            candidate_total = generic_price * travelers
            if trip_type in {"one_way", "one-way", "single"}:
                candidate_total *= 2
                warnings.append(
                    "Transport fare is one-way; return estimate assumes "
                    "the same fare and is not a confirmed quote."
                )
            elif trip_type not in {"round_trip", "return", "roundtrip"}:
                warnings.append(
                    "Transport trip type is unknown; return travel is not included."
                )
        elif fare_basis in {"total", "group", "all_travelers"}:
            candidate_total = generic_price
            if trip_type in {"one_way", "one-way", "single"}:
                candidate_total *= 2
                warnings.append(
                    "Transport total is one-way; return estimate assumes "
                    "the same fare and is not a confirmed quote."
                )
        else:
            # Do not guess whether a generic price is per person or group.
            continue

        transport_total = candidate_total
        transport_source = (
            "Source record with declared fare basis; "
            "not a confirmed live fare or booking."
        )
        break

    if transport_total is None:
        warnings.append("Transport price is unavailable.")

    # --------------------------------------------------
    # 2. Accommodation
    # --------------------------------------------------
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
            "Source record multiplied by trip nights; room availability, "
            "occupancy, taxes, and final price are not confirmed."
        )
    else:
        hotel_total = None
        hotel_source = "No usable accommodation price returned."
        warnings.append("Accommodation price is unavailable.")

    # --------------------------------------------------
    # 3. Food estimate
    # --------------------------------------------------
    food_total = food_rate * travelers * days

    # --------------------------------------------------
    # 4. Activities
    # --------------------------------------------------
    activity_total = 0.0
    priced_activity_count = 0

    for item in activity_records:
        category = str(item.get("category", "")).strip().lower()

        if category == "food":
            continue

        price = _number(item.get("estimated_cost_per_person"))

        if price is None:
            price = _number(item.get("price_per_person"))

        if price is not None:
            activity_total += price * travelers
            priced_activity_count += 1

    if not activity_records:
        warnings.append(
            "No activity records were returned; activity costs may "
            "be incomplete."
        )
    elif priced_activity_count == 0:
        warnings.append(
            "No usable activity prices were returned; activities may "
            "cost more than the calculated amount."
        )

    # --------------------------------------------------
    # 5. Sum known costs only
    # --------------------------------------------------
    known_subtotal = food_total + activity_total

    if transport_total is not None:
        known_subtotal += transport_total

    if hotel_total is not None:
        known_subtotal += hotel_total

    essential_prices_complete = (
        transport_total is not None and hotel_total is not None
    )

    contingency = round(
        known_subtotal * contingency_value,
        2,
    )

    estimated_total = round(
        known_subtotal + contingency,
        2,
    )

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

    # --------------------------------------------------
    # 6. Return budget report
    # --------------------------------------------------
    return {
        "currency": "INR",
        "travelers": travelers,
        "days": days,
        "nights": nights,
        "start_date": (
            parsed_start.isoformat() if parsed_start else None
        ),
        "end_date": (
            parsed_end.isoformat() if parsed_end else None
        ),
        "user_budget": round(budget_value, 2),
        "line_items": {
            "transport": {
                "amount": (
                    round(transport_total, 2)
                    if transport_total is not None
                    else None
                ),
                "source": transport_source,
            },
            "accommodation": {
                "amount": (
                    round(hotel_total, 2)
                    if hotel_total is not None
                    else None
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
        "budget_remaining": round(
            budget_value - estimated_total,
            2,
        ),
        "budget_remaining_is_final": essential_prices_complete,
        "within_budget_based_on_known_costs": (
            estimated_total <= budget_value
        ),
        "within_budget": within_budget,
        "warnings": warnings,
        "is_live_quote": False,
    }
