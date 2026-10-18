
from typing import Any


def run_review_agent(
    itinerary: str,
    budget: float,
    budget_analysis: Any = None,
    weather_data: Any = None,
    transport_data: Any = None,
    hotel_data: Any = None,
) -> dict[str, Any]:
    """Review a travel plan and report missing or potentially risky details."""

    if budget <= 0:
        raise ValueError("Budget must be greater than zero.")

    issues = []
    recommendations = []

    # Check itinerary
    if not isinstance(itinerary, str) or not itinerary.strip():
        issues.append("Itinerary is missing.")
    else:
        recommendations.append(
            "Confirm travel dates, timings, and activity opening hours."
        )

    # Check budget analysis
    if isinstance(budget_analysis, dict):
        if budget_analysis.get("essential_prices_complete") is False:
            issues.append(
                "Essential transport or accommodation prices are missing."
            )

        estimated_total = budget_analysis.get("estimated_total")

        if estimated_total is not None:
            try:
                if float(estimated_total) > budget:
                    issues.append("Estimated trip cost exceeds the budget.")
                else:
                    recommendations.append(
                        "Keep some budget aside for unexpected expenses."
                    )
            except (TypeError, ValueError):
                issues.append("Estimated total cost is not a valid number.")
    elif not budget_analysis:
        issues.append("Budget analysis was not provided.")

    # Check transport information
    if not transport_data:
        issues.append("Transport options or prices are unavailable.")

    # Check accommodation information
    if not hotel_data:
        issues.append("Hotel options or prices are unavailable.")

    # Check weather information
    if not weather_data:
        issues.append("Weather forecast is unavailable.")
        recommendations.append(
            "Check the destination forecast before travelling."
        )

    status = "needs_review" if issues else "reviewed"

    return {
        "status": status,
        "issues": issues,
        "recommendations": recommendations,
        "budget": budget,
        "message": (
            "Review completed with issues to resolve."
            if issues
            else "Review completed. Verify live prices before booking."
        ),
    }
