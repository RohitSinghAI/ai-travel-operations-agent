
from typing import Any


def run_hotel_agent(
    hotel_data: dict[str, Any],
    budget: float,
    travelers: int = 1,
    max_results: int = 5,
) -> dict[str, Any]:
    """
    Filter and rank hotel offers using available price data.

    This function does not fetch live data itself.
    hotel_data must come from the hotel search tool/provider.
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

    offers = hotel_data.get("offers", [])

    if not isinstance(offers, list) or not offers:
        return {
            "status": hotel_data.get("status", "unavailable"),
            "provider": hotel_data.get("provider"),
            "message": "No hotel offers are available to compare.",
            "hotels": [],
            "count": 0,
        }

    hotels = []

    for offer in offers:
        if not isinstance(offer, dict):
            continue

        # Amadeus hotel-offer responses contain a hotel object
        # and an offers list. Also support normalized provider data.
        hotel = offer.get("hotel", {})
        nested_offers = offer.get("offers", [])

        if not nested_offers and offer.get("price") is not None:
            nested_offers = [offer]

        if not isinstance(nested_offers, list):
            continue

        for price_offer in nested_offers:
            if not isinstance(price_offer, dict):
                continue

            price_data = price_offer.get("price", {})
            if not isinstance(price_data, dict):
                price_data = {}

            raw_amount = price_data.get(
                "total", price_offer.get("price")
            )

            try:
                amount = float(raw_amount)
            except (TypeError, ValueError):
                continue

            if amount < 0:
                continue

            currency = price_data.get(
                "currency", price_offer.get("currency", "INR")
            )

            hotels.append({
                "hotel_id": hotel.get(
                    "hotelId", price_offer.get("hotel_id")
                ),
                "name": hotel.get(
                    "name", price_offer.get("name", "Hotel")
                ),
                "price": amount,
                "currency": currency,
                "check_in": price_offer.get("checkInDate"),
                "check_out": price_offer.get("checkOutDate"),
                "room": price_offer.get("room", {}),
                "provider": hotel_data.get("provider"),
                "status": hotel_data.get("status", "unknown"),
            })

    # Only compare prices in INR. Do not compare different
    # currencies without a verified currency conversion.
    priced_hotels = [
        hotel
        for hotel in hotels
        if hotel["currency"] == "INR"
    ]

    priced_hotels.sort(key=lambda hotel: hotel["price"])

    return {
        "status": (
            hotel_data.get("status", "unknown")
            if priced_hotels
            else "unavailable"
        ),
        "provider": hotel_data.get("provider"),
        "budget": budget,
        "travelers": travelers,
        "hotels": priced_hotels[:max_results],
        "count": len(priced_hotels),
        "message": (
            "Hotel offers sorted by total price."
            if priced_hotels
            else "No usable INR hotel prices were returned."
        ),
    }
