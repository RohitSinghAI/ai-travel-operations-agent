
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
    }

    result = travel_graph.invoke(initial_state)

    if result.get("error"):
        raise RuntimeError(result["error"])

    return {
        "status": "success",
        "source": request.source,
        "destination": request.destination,
        "itinerary": result.get("itinerary", ""),
        "budget": request.budget,
        "days": request.days,
        "travelers": request.travelers,
    }
