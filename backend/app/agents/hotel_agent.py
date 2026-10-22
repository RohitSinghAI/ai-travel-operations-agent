
from datetime import date, datetime
from typing import Any


def _parse_date(value: Any) -> date | None:
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


def _extract_hotels(hotel_data: dict[str, Any]) -> list:
    """Support sample data, normalized offers and Amadeus responses."""

    result = hotel_data.get("result")

    # Current project format:
    # {"result": {"result": [hotel, ...]}}
    if isinstance(result, dict):
        nested = result.get("result")
        if isinstance(nested, list):
            return nested

        nested_offers = result.get("offers")
        if isinstance(nested_offers, list):
            return nested_offers

    if isinstance(result, list):
        return result

    offers = hotel_data.get("offers")
    if isinstance(offers, list):
        return offers

    hotels = hotel_data.get("hotels")
    if isinstance(hotels, list):
        return hotels

    return []


def run_hotel_agent(
    hotel_data: dict[str, Any],
    budget: float,
    travelers: int = 1,
    max_results: int = 5,
    nights: int = 1,
    start_date: str | date | None = None,
    end_date: str | date | None = None,
) -> dict[str, Any]:
    """
    Normalize and rank hotel records.

    Sample estimates remain estimates; they are never presented as
    confirmed live booking quotes. For sample per-night rates, pass
    the actual trip nights to calculate an estimated stay total.
    """

    if budget <= 0:
        raise ValueError("Budget must be greater than zero.")

    if travelers < 1:
        raise ValueError("Travelers must be at least one.")

    if max_results < 1:
        raise ValueError("max_results must be at least one.")

    if not isinstance(hotel_data, dict):
        return {
            "status": "unavailable",
            "message": "Hotel data must be a dictionary.",
            "hotels": [],
            "count": 0,
        }

    check_in = _parse_date(start_date)
    check_out = _parse_date(end_date)

    if start_date is not None and check_in is None:
        raise ValueError("Invalid start_date; use YYYY-MM-DD.")

    if end_date is not None and check_out is None:
        raise ValueError("Invalid end_date; use YYYY-MM-DD.")

    if check_in is not None and check_out is not None:
        if check_out <= check_in:
            raise ValueError("end_date must be after start_date.")

        nights = (check_out - check_in).days

    if nights < 1:
        raise ValueError("nights must be at least one.")

    records = _extract_hotels(hotel_data)

    if not records:
        return {
            "status": "unavailable",
            "provider": hotel_data.get("provider"),
            "budget": budget,
            "travelers": travelers,
            "nights": nights,
            "hotels": [],
            "count": 0,
            "message": "No hotel records were returned by the hotel search tool.",
        }

    hotels = []

    for record in records:
        if not isinstance(record, dict):
            continue

        hotel = record.get("hotel")
        if not isinstance(hotel, dict):
            hotel = {}

        # Handle Amadeus-style records with nested offers.
        nested_offers = record.get("offers")
        if isinstance(nested_offers, list) and nested_offers:
            price_records = nested_offers
        else:
            price_records = [record]

        for offer in price_records:
            if not isinstance(offer, dict):
                continue

            price_data = offer.get("price")
            if not isinstance(price_data, dict):
                price_data = {}

            raw_currency = (
                price_data.get("currency")
                or offer.get("currency")
                or record.get("currency")
                or "INR"
            )
            currency = str(raw_currency).upper()

            is_sample_rate = (
                offer.get("estimated_price_per_night") is not None
                or record.get("estimated_price_per_night") is not None
            )

            raw_amount = (
                offer.get("estimated_price_per_night")
                if offer.get("estimated_price_per_night") is not None
                else record.get("estimated_price_per_night")
            )

            if raw_amount is not None:
                price_kind = "per_night_estimate"
            else:
                raw_amount = price_data.get("total")
                if raw_amount is None:
                    raw_amount = offer.get("price")

                price_kind = "total_offer_price"

            try:
                amount = float(raw_amount)
            except (TypeError, ValueError):
                # Do not invent missing prices.
                continue

            if amount < 0:
                continue

            if price_kind == "per_night_estimate":
                price_per_night = amount
                total_price = amount * nights
            else:
                total_price = amount
                price_per_night = (
                    total_price / nights if nights else None
                )

            room = offer.get("room", {})
            if not isinstance(room, dict):
                room = {}

            name = (
                hotel.get("name")
                or offer.get("name")
                or record.get("name")
                or "Unnamed hotel"
            )

            room_type = (
                record.get("room_type")
                or room.get("type")
                or room.get("description", {}).get("text")
                if isinstance(room.get("description"), dict)
                else record.get("room_type") or room.get("type")
            )

            live_quote = (
                offer.get("is_live_quote")
                if offer.get("is_live_quote") is not None
                else record.get("is_live_quote")
            )

            hotels.append({
                "hotel_id": (
                    hotel.get("hotelId")
                    or offer.get("hotel_id")
                    or record.get("hotel_id")
                ),
                "name": name,
                "room_type": room_type or "Room type not specified",
                "price": round(total_price, 2),
                "price_per_night": round(price_per_night, 2),
                "currency": currency,
                "price_type": (
                    "estimated_stay_total"
                    if price_kind == "per_night_estimate"
                    else "provider_offer_total"
                ),
                "nights": nights,
                "check_in": (
                    offer.get("checkInDate")
                    or record.get("check_in")
                    or (check_in.isoformat() if check_in else None)
                ),
                "check_out": (
                    offer.get("checkOutDate")
                    or record.get("check_out")
                    or (check_out.isoformat() if check_out else None)
                ),
                "provider": (
                    hotel_data.get("provider")
                    or record.get("provider")
                    or "Sample Data"
                ),
                "is_live_quote": bool(live_quote),
                "within_budget": (
                    total_price <= budget if currency == "INR" else None
                ),
            })

    # Do not compare prices across different currencies.
    priced_hotels = [
        hotel for hotel in hotels if hotel["currency"] == "INR"
    ]

    priced_hotels.sort(key=lambda hotel: hotel["price"])

    if not priced_hotels:
        return {
            "status": "unavailable",
            "provider": hotel_data.get("provider"),
            "budget": budget,
            "travelers": travelers,
            "nights": nights,
            "hotels": [],
            "count": 0,
            "message": "No usable INR hotel prices were returned.",
        }

    has_live_quote = any(
        hotel["is_live_quote"] for hotel in priced_hotels
    )

    return {
        "status": "available",
        "provider": hotel_data.get("provider") or "Sample Data",
        "budget": budget,
        "travelers": travelers,
        "nights": nights,
        "start_date": check_in.isoformat() if check_in else None,
        "end_date": check_out.isoformat() if check_out else None,
        "hotels": priced_hotels[:max_results],
        "count": min(len(priced_hotels), max_results),
        "is_live_quote": has_live_quote,
        "message": (
            "Hotel offers processed. Check each hotel's is_live_quote field."
        ),
    }
