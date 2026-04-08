from fastapi.testclient import TestClient

from app.api.main import app


client = TestClient(app)


def test_plan_trip_schema() -> None:
    payload = {
        "destination": "Mysore",
        "budget": 15000,
        "days": 3,
        "preferences": ["history", "food"],
        "start_date": "2026-04-10",
        "travelers": 2,
    }
    response = client.post("/plan-trip", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["trip_request"]["destination"] == "Mysore"
    assert "daily_plans" in data
    assert "budget_breakdown" in data
