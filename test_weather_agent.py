
from backend.app.agents.weather_agent import run_weather_agent

weather = {
    "forecast": {
        "temperature": 37,
        "condition": "Clear sky",
    },
    "is_live": True,
}

result = run_weather_agent(
    weather_data=weather,
    destination="Goa",
    days=3,
)

print(result)
