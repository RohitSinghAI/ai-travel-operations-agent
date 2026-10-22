
import os
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP


# Add project root to Python import path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from backend.app.tools.transport_tools import search_transport
from backend.app.tools.hotel_tools import search_hotels
from backend.app.tools.activity_tools import search_activities
from backend.app.tools.weather_tools import get_weather


mcp = FastMCP("travel-tools")


@mcp.tool()
def find_transport(source: str, destination: str) -> dict:
    """Find sample transport options and report live API configuration."""

    train_configured = bool(
        os.getenv("TRAIN_API_BASE_URL")
        and os.getenv("TRAIN_API_KEY")
    )

    bus_configured = bool(
        os.getenv("BUS_API_BASE_URL")
        and os.getenv("BUS_API_USERNAME")
        and os.getenv("BUS_API_PASSWORD")
    )

    sample_options = search_transport(source, destination)

    return {
        "source": source,
        "destination": destination,
        "status": "not_configured",
        "live_data": False,
        "providers": {
            "train": {
                "configured": train_configured,
                "status": (
                    "credentials_configured"
                    if train_configured
                    else "not_configured"
                ),
            },
            "bus": {
                "configured": bus_configured,
                "status": (
                    "credentials_configured"
                    if bus_configured
                    else "not_configured"
                ),
            },
        },
        "sample_options": sample_options,
        "message": (
            "This tool currently returns sample transport data only. "
            "Live train and bus API calls have not been implemented. "
            "Configured credentials alone do not mean live data is available."
        ),
    }


@mcp.tool()
def find_hotels(destination: str) -> list[dict]:
    """Find sample hotel options in a destination city."""
    return search_hotels(destination)


@mcp.tool()
def find_activities(destination: str) -> list[dict]:
    """Find sample activities in a destination city."""
    return search_activities(destination)


@mcp.tool()
def check_weather(destination: str) -> dict:
    """Check weather using the configured weather tool."""
    return get_weather(destination)


if __name__ == "__main__":
    mcp.run(transport="stdio")
