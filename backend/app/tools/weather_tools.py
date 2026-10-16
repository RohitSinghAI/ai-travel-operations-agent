
def get_weather(destination: str) -> dict:
    """Return an explicit notice until a weather provider is configured."""
    return {
        "destination": destination,
        "available": False,
        "message": (
            "Live weather data is not configured. "
            "Connect a weather API to retrieve a forecast."
        ),
    }
