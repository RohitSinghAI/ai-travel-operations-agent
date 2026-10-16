
from typing import Any

from backend.app.services.budget_service import calculate_budget


def run_budget_agent(
    tool_data: dict[str, Any],
    travelers: int,
    days: int,
    budget: float,
) -> dict[str, Any]:
    """
    Analyze trip expenses and determine whether the trip
    fits within the user's budget.

    Budget amounts are calculated by Python, not by the LLM.
    """

    breakdown = calculate_budget(
        tool_data=tool_data,
        travelers=travelers,
        days=days,
        budget=budget,
    )

    essential_prices_complete = breakdown.get(
        "essential_prices_complete", False
    )

    estimated_total = breakdown.get("estimated_total")
    budget_remaining = breakdown.get("budget_remaining")

    if not essential_prices_complete:
        status = "incomplete"
        message = (
            "Transport or accommodation prices are missing. "
            "The final trip cost cannot yet be confirmed."
        )
    elif estimated_total is not None and estimated_total > budget:
        status = "over_budget"
        message = (
            "The estimated trip cost exceeds the user's budget."
        )
    else:
        status = "within_budget"
        message = (
            "The known estimated trip cost is within the budget."
        )

    return {
        "status": status,
        "message": message,
        "user_budget": budget,
        "estimated_total": estimated_total,
        "budget_remaining": budget_remaining,
        "breakdown": breakdown,
    }
