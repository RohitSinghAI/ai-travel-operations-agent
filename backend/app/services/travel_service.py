
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

    # Execute the LangGraph workflow
    result = travel_graph.invoke(initial_state)

    # Check workflow errors
    if result.get("error"):
        raise RuntimeError(result["error"])

    # Validate generated itinerary
    itinerary = result.get("itinerary")

    if not itinerary:
        raise RuntimeError(
            "The workflow did not generate an itinerary."
        )

    # Return the complete response
    return {
        "status": "success",
        "source": request.source,
        "destination": request.destination,
        "itinerary": itinerary,
        "budget": request.budget,
        "days": request.days,
        "travelers": request.travelers,
        "check_in": request.check_in.isoformat(),
        "check_out": request.check_out.isoformat(),

        # MCP and live API data
        "tool_data": result.get("tool_data", {}),

        # Specialist agent outputs
        "transport_options": result.get("transport_options", {}),
        "hotel_options": result.get("hotel_options", {}),
        "activity_options": result.get("activity_options", {}),
        "weather_summary": result.get("weather_summary", {}),

        # Budget information
        "budget_breakdown": result.get("budget_breakdown", {}),
        "budget_analysis": result.get("budget_analysis", ""),

        # Final review
        "review_notes": result.get("review_notes", ""),
    }
