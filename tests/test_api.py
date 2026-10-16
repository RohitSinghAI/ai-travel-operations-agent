
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.api.routes import travel

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_travel_plan(monkeypatch):
    def fake_generate_travel_plan(request):
        return {
            "status": "success",
            "source": request.source,
            "destination": request.destination,
            "itinerary": "Day 1: Explore the destination.",
            "budget": request.budget,
            "days": request.days,
            "travelers": request.travelers,
            "tool_data": {
                "find_transport": {
                    "tool": "find_transport",
                    "result": [],
                }
            },
        }

    monkeypatch.setattr(
        travel,
        "generate_travel_plan",
        fake_generate_travel_plan,
    )

    payload = {
        "source": "Hyderabad",
        "destination": "Goa",
        "days": 3,
        "budget": 15000,
        "travelers": 2,
        "preferences": ["beaches", "local food"],
    }

    response = client.post(
        "/api/travel/plan",
        json=payload,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "success"
    assert data["source"] == "Hyderabad"
    assert data["destination"] == "Goa"
    assert data["days"] == 3
    assert data["travelers"] == 2
    assert "itinerary" in data
    assert "tool_data" in data


def test_invalid_travel_request():
    response = client.post(
        "/api/travel/plan",
        json={
            "source": "H",
            "destination": "Goa",
            "days": 3,
            "budget": 15000,
            "travelers": 2,
        },
    )

    assert response.status_code == 422
