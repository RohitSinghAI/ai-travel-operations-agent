from backend.app.travel_graph import run_travel_graph


def create_travel_plan(travel_request: dict) -> dict:
    result = run_travel_graph(travel_request)

    return {
        "status": "success",
        "travel_request": result["travel_request"],
        "transport_options": result["transport_options"],
        "hotel_options": result["hotel_options"],
        "weather_info": result["weather_info"],
        "activities": result["activities"],
        "budget_summary": result["budget_summary"],
        "review_result": result["review_result"],
        "errors": result.get("errors", []),
    }