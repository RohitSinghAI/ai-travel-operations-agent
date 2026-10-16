
from langgraph.graph import END, START, StateGraph

from backend.app.graph.state import TravelAgentState
from backend.app.graph.nodes import plan_travel
from backend.app.graph.edges import route_after_planning


def build_travel_graph():
    graph = StateGraph(TravelAgentState)

    graph.add_node("plan_travel", plan_travel)

    graph.add_edge(START, "plan_travel")

    graph.add_conditional_edges(
        "plan_travel",
        route_after_planning,
        {
            "success": END,
            "error": END,
        },
    )

    return graph.compile()


travel_graph = build_travel_graph()
