
import os
from mcp.server.fastmcp import FastMCP

from backend.app.tools.transport_tools import search_transport
from backend.app.tools.hotel_tools import search_hotels
from backend.app.tools.activity_tools import search_activities
from backend.app.tools.weather_tools import get_weather


mcp = FastMCP("travel-tools")


@mcp.tool()
def find_transport(source: str, destination: str) -> dict:
    """Find transport options. Reports whether live provider APIs are configured."""

    train_configured = bool(
        os.getenv("TRAIN_API_BASE_URL") and os.getenv("TRAIN_API_KEY")
    )

    bus_configured = bool(
        os.getenv("BUS_API_BASE_URL")
        and os.getenv("BUS_API_USERNAME")
        and os.getenv("BUS_API_PASSWORD")
    )

    # Existing function currently supplies sample data, not live API quotes.
    sample_options = search_transport(source, destination)

    return {
        "source": source,
        "destination": destination,
        "status": "not_configured",
        "live_data": False,
        "providers": {
            "train": {
                "configured": train_configured,
                "status": "credentials_configured"
                if train_configured
                else "not_configured",
            },
            "bus": {
                "configured": bus_configured,
                "status": "credentials_configured"
                if bus_configured
                else "not_configured",
            },
        },
        "sample_options": sample_options,
        "message": (
            "Live train and bus search is not implemented in this tool yet. "
            "Sample options are not live quotes. Configure provider access "
            "and implement its documented API before using live fares."
        ),
    }


@mcp.tool()
def find_hotels(destination: str) -> list[dict]:
    """Find hotel options using the existing hotel tool."""
    return search_hotels(destination)


@mcp.tool()
def find_activities(destination: str) -> list[dict]:
    """Find tourist activities using the existing activities tool."""
    return search_activities(destination)


@mcp.tool()
def check_weather(destination: str) -> dict:
    """Check weather using the existing weather tool."""
    return get_weather(destination)


if __name__ == "__main__":
    mcp.run(transport="stdio")
