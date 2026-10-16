
from backend.app.graph.state import TravelAgentState


def route_after_planning(state: TravelAgentState) -> str:
    """Route the workflow based on the planning result."""
    if state.get("error"):
        return "error"

    return "success"
