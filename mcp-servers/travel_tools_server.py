
from mcp.server.fastmcp import FastMCP

from backend.app.tools.transport_tools import search_transport
from backend.app.tools.hotel_tools import search_hotels
from backend.app.tools.activity_tools import search_activities
from backend.app.tools.weather_tools import get_weather


mcp = FastMCP("travel-tools")


@mcp.tool()
def find_transport(source: str, destination: str) -> list[dict]:
    """Find sample transport options between two cities."""
    return search_transport(source, destination)


@mcp.tool()
def find_hotels(destination: str) -> list[dict]:
    """Find sample hotels in a destination city."""
    return search_hotels(destination)


@mcp.tool()
def find_activities(destination: str) -> list[dict]:
    """Find sample tourist activities in a destination city."""
    return search_activities(destination)


@mcp.tool()
def check_weather(destination: str) -> dict:
    """Check whether live weather information is configured."""
    return get_weather(destination)


if __name__ == "__main__":
    mcp.run(transport="stdio")
