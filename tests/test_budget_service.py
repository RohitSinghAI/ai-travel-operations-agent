
from backend.app.services.budget_service import calculate_budget


def sample_tool_data():
    return {
        "find_transport": {
            "result": [
                {
                    "source": "Hyderabad",
                    "destination": "Goa",
                    "mode": "Bus",
                    "price_per_person": 1800,
                    "trip_type": "round_trip",
                    "is_live_quote": False,
                }
            ]
        },
        "find_hotels": {
            "result": [
                {
                    "city": "Goa",
                    "name": "Sample Guesthouse",
                    "estimated_price_per_night": 1200,
                    "is_live_quote": False,
                }
            ]
        },
        "find_activities": {
            "result": [
                {
                    "city": "Goa",
                    "name": "Calangute Beach",
                    "category": "Beach",
                    "estimated_cost_per_person": 0,
                }
            ]
        },
    }


def test_budget_calculation():
    result = calculate_budget(
        tool_data=sample_tool_data(),
        travelers=2,
        days=3,
        budget=15000,
    )

    assert result["line_items"]["transport"]["amount"] == 3600
    assert result["line_items"]["accommodation"]["amount"] == 2400
    assert result["line_items"]["food"]["amount"] == 2400
    assert result["line_items"]["activities"]["amount"] == 0
    assert result["line_items"]["contingency"]["amount"] == 840
    assert result["estimated_total"] == 9240
    assert result["budget_remaining"] == 5760
    assert result["essential_prices_complete"] is True
    assert result["is_live_quote"] is False


def test_missing_transport_price_is_not_zero():
    data = sample_tool_data()
    data["find_transport"] = {
        "error": "Transport tool unavailable"
    }

    result = calculate_budget(
        tool_data=data,
        travelers=2,
        days=3,
        budget=15000,
    )

    assert result["line_items"]["transport"]["amount"] is None
    assert result["essential_prices_complete"] is False
    assert any(
        "Transport price is unavailable" in warning
        for warning in result["warnings"]
    )


def test_one_day_trip_has_zero_nights():
    result = calculate_budget(
        tool_data=sample_tool_data(),
        travelers=1,
        days=1,
        budget=5000,
    )

    assert result["nights"] == 0
    assert result["line_items"]["accommodation"]["amount"] == 0


def test_budget_exceeded_is_reported():
    result = calculate_budget(
        tool_data=sample_tool_data(),
        travelers=2,
        days=3,
        budget=5000,
    )

    assert result["estimated_total"] > 5000
    assert result["within_budget_based_on_known_costs"] is False
