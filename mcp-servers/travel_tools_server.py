
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("travel-operations-tools")


@mcp.tool()
def search_transport(
    source: str,
    destination: str,
    travelers: int = 1
) -> list[dict]:
    """Return sample transport options for a route."""
    if travelers < 1:
        raise ValueError("Travelers must be at least 1.")

    options = [
        {"mode": "Flight", "price_per_person": 4500, "duration_hours": 1.5},
        {"mode": "Train", "price_per_person": 1200, "duration_hours": 14},
        {"mode": "Bus", "price_per_person": 1000, "duration_hours": 16},
    ]

    return [
        {
            **option,
            "source": source,
            "destination": destination,
            "travelers": travelers,
            "estimated_total": option["price_per_person"] * travelers,
            "data_source": "DEMO"
        }
        for option in options
    ]


@mcp.tool()
def search_hotels(
    destination: str,
    nights: int,
    travelers: int = 1
) -> list[dict]:
    """Return sample hotel options and estimated costs."""
    if nights < 1 or travelers < 1:
        raise ValueError("Nights and travelers must be at least 1.")

    hotels = [
        {"name": "Budget Guesthouse", "price_per_night": 1200},
        {"name": "Beachside Hotel", "price_per_night": 2500},
        {"name": "Premium Resort", "price_per_night": 5000},
    ]

    return [
        {
            **hotel,
            "destination": destination,
            "nights": nights,
            "travelers": travelers,
            "estimated_total": hotel["price_per_night"] * nights,
            "data_source": "DEMO"
        }
        for hotel in hotels
    ]


@mcp.tool()
def get_weather(destination: str, travel_date: str) -> dict:
    """Return a placeholder, not a live weather forecast."""
    return {
        "destination": destination,
        "travel_date": travel_date,
        "forecast": "No live forecast connected",
        "data_source": "DEMO"
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
