
from typing import Any


def run_weather_agent(
    weather_data: Any,
    destination: str,
    days: int = 1,
) -> dict[str, Any]:
    """
    Process weather data for a travel destination.

    This agent processes supplied weather data.
    It does not fetch a live forecast by itself.
    """

    if days < 1:
        raise ValueError("days must be at least 1.")

    if not isinstance(destination, str) or not destination.strip():
        raise ValueError("Destination cannot be empty.")

    # Handle missing or invalid weather data.
    if not isinstance(weather_data, dict) or not weather_data:
        return {
            "status": "unavailable",
            "destination": destination.strip(),
            "forecast": None,
            "travel_advice": [
                "Weather forecast is unavailable.",
                "Check the forecast before travelling.",
            ],
            "is_live": False,
            "message": "No usable weather data was provided.",
        }

    # Support common API response formats.
    forecast = weather_data.get(
        "forecast",
        weather_data.get("daily", weather_data.get("current")),
    )

    if forecast is None:
        forecast = weather_data.get("result", weather_data.get("data"))

    if forecast is None:
        forecast = weather_data

    # Preserve source data without inventing forecast values.
    advice = []

    if isinstance(forecast, dict):
        temperature = forecast.get("temperature")
        condition = str(
            forecast.get("condition")
            or forecast.get("description")
            or forecast.get("weather")
            or ""
        ).lower()

        if temperature is not None:
            try:
                temp = float(temperature)

                if temp >= 35:
                    advice.append(
                        "Hot conditions may require water, sunscreen, "
                        "and outdoor breaks."
                    )
                elif temp <= 10:
                    advice.append(
                        "Consider warm clothing if these temperatures "
                        "are forecast for your travel dates."
                    )
            except (TypeError, ValueError):
                pass

        if any(word in condition for word in ("rain", "storm", "thunder")):
            advice.append(
                "Check rain conditions and keep an indoor activity option."
            )

        if not advice:
            advice.append(
                "Check the forecast for each travel day before finalizing "
                "outdoor activities."
            )

    else:
        advice.append(
            "Review the forecast for each travel day before planning "
            "outdoor activities."
        )

    return {
        "status": "success",
        "destination": destination.strip(),
        "days": days,
        "forecast": forecast,
        "travel_advice": advice,
        "is_live": weather_data.get("is_live", False),
        "message": "Weather data processed successfully.",
    }
