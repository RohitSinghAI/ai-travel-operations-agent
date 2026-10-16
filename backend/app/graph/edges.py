
from backend.app.graph.state import TravelAgentState


def route_after_planning(state: TravelAgentState) -> str:
    if state.get("error"):
        return "error"
    return "success"
