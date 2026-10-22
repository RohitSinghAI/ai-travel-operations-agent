
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
            "itinerary": "Day 1: Explore Goa.",
            "budget": request.budget,
            "days": (request.end_date - request.start_date).days,
            "travelers": request.travelers,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "tool_data": {},
            "budget_breakdown": {
                "estimated_total": 9240,
                "is_live_quote": False,
            },
            "budget_analysis": "Illustrative budget estimate.",
            "review_notes": "Sample response.",
        }

    monkeypatch.setattr(
        travel,
        "generate_travel_plan",
        fake_generate_travel_plan,
    )

    response = client.post(
        "/api/travel/plan",
        json={
            "source": "Hyderabad",
            "destination": "Goa",
            "start_date": "2026-11-10",
            "end_date": "2026-11-13",
            "budget": 15000,
            "travelers": 2,
            "preferences": ["beaches", "local food"],
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "success"
    assert data["destination"] == "Goa"
    assert data["days"] == 3
    assert data["budget_breakdown"]["estimated_total"] == 9240
    assert data["budget_breakdown"]["is_live_quote"] is False


def test_invalid_travel_request():
    response = client.post(
        "/api/travel/plan",
        json={
            "source": "H",
            "destination": "Goa",
            "start_date": "2026-11-10",
            "end_date": "2026-11-13",
            "budget": 15000,
            "travelers": 2,
        },
    )

    assert response.status_code == 422


def test_missing_required_fields():
    response = client.post(
        "/api/travel/plan",
        json={"source": "Hyderabad"},
    )

    assert response.status_code == 422
