from fastapi.testclient import TestClient

from app.api.main import app, planning_service
from app.auth.dependencies import get_current_user
from app.db.models import User
from app.providers.mock_hotel_provider import MockHotelProvider
from app.providers.mock_maps_provider import MockMapsProvider


client = TestClient(app)


def test_plan_trip_schema() -> None:
    original_hotel_provider = planning_service.hotel_provider
    original_maps_provider = planning_service.maps_provider
    planning_service.hotel_provider = MockHotelProvider()
    planning_service.hotel_mcp.provider = planning_service.hotel_provider
    planning_service.maps_provider = MockMapsProvider()
    planning_service.maps_mcp.provider = planning_service.maps_provider

    app.dependency_overrides[get_current_user] = lambda: User(
        id=1,
        full_name="Test User",
        email="test@example.com",
        hashed_password="test",
    )
    try:
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
        assert data["trip_request"]["hotel_preference"] == "standard"
        assert data["trip_request"]["transport_mode"] == "auto"
        assert "transport" in data
        assert "daily_plans" in data
        assert "budget_breakdown" in data
    finally:
        app.dependency_overrides.clear()
        planning_service.hotel_provider = original_hotel_provider
        planning_service.hotel_mcp.provider = original_hotel_provider
        planning_service.maps_provider = original_maps_provider
        planning_service.maps_mcp.provider = original_maps_provider
