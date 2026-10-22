from datetime import date, timedelta
from typing import Any


def run_weather_agent(
    weather_data: Any,
    destination: str,
    days: int = 1,
    start_date: str | date | None = None,
    end_date: str | date | None = None,
) -> dict[str, Any]:
    """
    Process weather data for a travel destination.

    Only returns forecast data matching the requested travel dates.
    This agent does not fetch weather data itself.
    """

    if days < 1:
        raise ValueError("days must be at least 1.")

    if not isinstance(destination, str) or not destination.strip():
        raise ValueError("Destination cannot be empty.")

    def parse_date(value: str | date | None) -> date | None:
        if value is None:
            return None
        if isinstance(value, date):
            return value
        return date.fromisoformat(value)

    trip_start = parse_date(start_date)
    trip_end = parse_date(end_date)

    if trip_start and trip_end and trip_end <= trip_start:
        raise ValueError("end_date must be after start_date.")

    def unavailable(message: str) -> dict[str, Any]:
        return {
            "status": "unavailable",
            "destination": destination.strip(),
            "days": days,
            "start_date": trip_start.isoformat() if trip_start else None,
            "end_date": trip_end.isoformat() if trip_end else None,
            "forecast": [],
            "travel_advice": [
                "Weather forecast is unavailable for the requested trip dates.",
                "Check the forecast again closer to departure.",
            ],
            "is_live": False,
            "message": message,
        }

    if not isinstance(weather_data, dict) or not weather_data:
        return unavailable("No usable weather data was provided.")

    forecast = weather_data.get(
        "forecast",
        weather_data.get("daily", weather_data.get("current")),
    )

    if forecast is None:
        forecast = weather_data.get("result", weather_data.get("data"))

    if forecast is None:
        forecast = weather_data

    # Normalize common forecast structures into dated records.
    records: list[dict[str, Any]] = []

    if isinstance(forecast, list):
        records = [item for item in forecast if isinstance(item, dict)]

    elif isinstance(forecast, dict):
        # Open-Meteo daily format commonly uses:
        # {"time": ["YYYY-MM-DD", ...], "temperature_2m_max": [...]}
        dates = forecast.get("time", forecast.get("dates"))

        if isinstance(dates, list):
            for index, day_value in enumerate(dates):
                record = {"date": day_value}
                for key, values in forecast.items():
                    if key in ("time", "dates"):
                        continue
                    if isinstance(values, list) and index < len(values):
                        record[key] = values[index]
                records.append(record)

        else:
            nested = forecast.get("forecast")
            if isinstance(nested, list):
                records = [item for item in nested if isinstance(item, dict)]
            elif any(key in forecast for key in ("date", "datetime")):
                records = [forecast]

    # Filter by the requested travel dates.
    if trip_start and trip_end:
        trip_records = []

        for record in records:
            raw_date = record.get("date", record.get("datetime", record.get("time")))
            try:
                forecast_date = (
                    raw_date if isinstance(raw_date, date)
                    else date.fromisoformat(str(raw_date)[:10])
                )
            except (TypeError, ValueError):
                continue

            # end_date is the checkout/departure date, so it is exclusive.
            if trip_start <= forecast_date < trip_end:
                trip_records.append(record)

        expected_days = (trip_end - trip_start).days
        covered_dates = {
            str(record.get("date", record.get("datetime", record.get("time")))[:10])
            for record in trip_records
            if isinstance(
                record.get("date", record.get("datetime", record.get("time"))),
                str,
            )
        }

        # Do not present a partial forecast as a complete trip forecast.
        expected_dates = {
            (trip_start + timedelta(days=offset)).isoformat()
            for offset in range(expected_days)
        }

        if len(trip_records) < expected_days or not expected_dates.issubset(covered_dates):
            return unavailable(
                "Available forecast does not cover all requested trip dates."
            )

        forecast = trip_records

    elif records:
        forecast = records[:days]

    else:
        return unavailable("No dated forecast records were found.")

    advice = [
        "Check local conditions again before outdoor activities."
    ]

    for record in forecast if isinstance(forecast, list) else []:
        condition = str(
            record.get("condition")
            or record.get("description")
            or record.get("weather")
            or ""
        ).lower()

        if any(word in condition for word in ("rain", "storm", "thunder")):
            advice.append(
                "Rain may affect outdoor activities; keep an indoor alternative."
            )
            break

    return {
        "status": "success",
        "destination": destination.strip(),
        "days": days,
        "start_date": trip_start.isoformat() if trip_start else None,
        "end_date": trip_end.isoformat() if trip_end else None,
        "forecast": forecast,
        "travel_advice": advice,
        "is_live": bool(weather_data.get("is_live", False)),
        "message": "Forecast matches the requested travel dates.",
    }