
from backend.app.schemas import TravelRequest
from backend.app.graph.workflow import travel_graph


def generate_travel_plan(request: TravelRequest) -> dict:
    initial_state = {
    "source": request.source,
    "destination": request.destination,
    "days": request.days,
    "budget": request.budget,
    "travelers": request.travelers,
    "preferences": request.preferences,
    "check_in": request.check_in.isoformat(),
    "check_out": request.check_out.isoformat(),
}

    result = travel_graph.invoke(initial_state)

    if result.get("error"):
        raise RuntimeError(result["error"])

    itinerary = result.get("itinerary")
    if not itinerary:
        raise RuntimeError(
            "The workflow did not generate an itinerary."
        )

    return {
        "status": "success",
        "source": request.source,
        "destination": request.destination,
        "itinerary": itinerary,
        "budget": request.budget,
        "days": request.days,
        "travelers": request.travelers,
        "tool_data": result.get("tool_data", {}),
        "budget_breakdown": result.get("budget_breakdown", {}),
        "budget_analysis": result.get("budget_analysis", ""),
        "review_notes": result.get("review_notes", ""),
    }
