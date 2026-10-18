
from langgraph.graph import END, START, StateGraph

from backend.app.graph.state import TravelAgentState
from backend.app.graph.nodes import (
    collect_tools_node,
    specialist_agents_node,
    budget_agent_node,
    itinerary_agent_node,
    review_agent_node,
)


def build_travel_graph():
    graph = StateGraph(TravelAgentState)

    # Register workflow nodes
    graph.add_node("collect_tools", collect_tools_node)
    graph.add_node("specialist_agents", specialist_agents_node)
    graph.add_node("budget_agent", budget_agent_node)
    graph.add_node("itinerary_agent", itinerary_agent_node)
    graph.add_node("review_agent", review_agent_node)

    # Start workflow
    graph.add_edge(START, "collect_tools")

    # Stop if data collection fails
    graph.add_conditional_edges(
        "collect_tools",
        lambda state: "error" if state.get("error") else "continue",
        {
            "continue": "specialist_agents",
            "error": END,
        },
    )

    # Process specialist agent outputs
    graph.add_conditional_edges(
        "specialist_agents",
        lambda state: "error" if state.get("error") else "continue",
        {
            "continue": "budget_agent",
            "error": END,
        },
    )

    # Calculate budget
    graph.add_conditional_edges(
        "budget_agent",
        lambda state: "error" if state.get("error") else "continue",
        {
            "continue": "itinerary_agent",
            "error": END,
        },
    )

    # Generate itinerary
    graph.add_conditional_edges(
        "itinerary_agent",
        lambda state: "error" if state.get("error") else "continue",
        {
            "continue": "review_agent",
            "error": END,
        },
    )

    # Finish after review
    graph.add_edge("review_agent", END)

    return graph.compile()


travel_graph = build_travel_graph()
