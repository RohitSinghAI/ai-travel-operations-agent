
from langgraph.graph import END, START, StateGraph

from backend.app.graph.state import TravelAgentState
from backend.app.graph.nodes import (
    collect_tools_node,
    budget_agent_node,
    itinerary_agent_node,
    review_agent_node,
)


def build_travel_graph():
    graph = StateGraph(TravelAgentState)

    graph.add_node("collect_tools", collect_tools_node)
    graph.add_node("budget_agent", budget_agent_node)
    graph.add_node("itinerary_agent", itinerary_agent_node)
    graph.add_node("review_agent", review_agent_node)

    graph.add_edge(START, "collect_tools")

    graph.add_conditional_edges(
        "collect_tools",
        lambda state: (
            "error" if state.get("error") else "continue"
        ),
        {
            "continue": "budget_agent",
            "error": END,
        },
    )

    graph.add_conditional_edges(
        "budget_agent",
        lambda state: (
            "error" if state.get("error") else "continue"
        ),
        {
            "continue": "itinerary_agent",
            "error": END,
        },
    )

    graph.add_conditional_edges(
        "itinerary_agent",
        lambda state: (
            "error" if state.get("error") else "continue"
        ),
        {
            "continue": "review_agent",
            "error": END,
        },
    )

    graph.add_edge("review_agent", END)

    return graph.compile()


travel_graph = build_travel_graph()
