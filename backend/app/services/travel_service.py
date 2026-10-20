
from backend.app.graph.workflow import travel_graph
from backend.app.schemas import TravelRequest


def generate_travel_plan(request: TravelRequest) -> dict:
    # Calculate trip duration from the selected dates
    days = (request.end_date - request.start_date).days

    initial_state = {
        "source": request.source,
        "destination": request.destination,
        "start_date": request.start_date.isoformat(),
        "end_date": request.end_date.isoformat(),
        "days": days,
        "budget": request.budget,
        "travelers": request.travelers,
        "currency": request.currency,
        "preferences": request.preferences,
    }

    # Execute the LangGraph workflow
    result = travel_graph.invoke(initial_state)

    # Handle workflow errors
    if result.get("error"):
        raise RuntimeError(result["error"])

    itinerary = result.get("itinerary")

    if not itinerary or not str(itinerary).strip():
        raise RuntimeError(
            "The workflow did not generate an itinerary."
        )

    # Return data matching TravelResponse
    return {
        "status": "success",
        "source": request.source,
        "destination": request.destination,
        "start_date": request.start_date.isoformat(),
        "end_date": request.end_date.isoformat(),
        "itinerary": str(itinerary).strip(),
        "budget": request.budget,
        "days": days,
        "travelers": request.travelers,
        "tool_data": result.get("tool_data", {}),
        "budget_breakdown": result.get("budget_breakdown", {}),
        "budget_analysis": result.get("budget_analysis", ""),
        "review_notes": result.get("review_notes", ""),
        "transport_options": result.get("transport_options", {}),
        "hotel_options": result.get("hotel_options", {}),
        "activity_options": result.get("activity_options", {}),
        "weather_summary": result.get("weather_summary", {}),
    }
