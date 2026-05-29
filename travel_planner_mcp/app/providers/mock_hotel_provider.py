from __future__ import annotations

from datetime import date

from app.models.schemas import HotelOption
from app.providers.hotel_provider_base import BaseHotelProvider


def _mock_coordinates(destination: str) -> tuple[float, float]:
    seed = sum(ord(char) for char in destination)
    latitude = round(10 + (seed % 800) / 100, 4)
    longitude = round(70 + (seed % 900) / 100, 4)
    return latitude, longitude


class MockHotelProvider(BaseHotelProvider):
    provider_name = "mock"

    async def search_hotels(
        self,
        destination: str,
        check_in: str | None,
        check_out: str | None,
        adults: int = 1,
        budget: float | None = None,
    ) -> list[HotelOption]:
        nights = 2
        if check_in and check_out:
            nights = max((date.fromisoformat(check_out) - date.fromisoformat(check_in)).days, 1)

        total_budget = budget or 12000.0
        standard_nightly = max(1800.0, min((total_budget * 0.45) / nights, 8000.0))
        budget_nightly = max(1200.0, standard_nightly * 0.65)
        comfort_nightly = min(standard_nightly * 1.15, 9500.0)
        luxury_nightly = min(max(standard_nightly * 1.45, (total_budget * 0.60) / nights * 0.95), 14000.0)
        latitude, longitude = _mock_coordinates(destination)
        return [
            HotelOption(
                name=f"{destination} Budget Inn",
                address=f"Transit Hub, {destination}",
                nightly_price=round(budget_nightly, 2),
                total_price=round(budget_nightly * nights, 2),
                rating=3.9,
                review_count=205,
                latitude=round(latitude + 0.04, 4),
                longitude=round(longitude + 0.03, 4),
                booking_link="https://example.com/mock-hotel-3",
                source="mock",
                amenities=["wifi", "parking"],
                distance_to_center_km=3.4,
            ),
            HotelOption(
                name=f"{destination} Central Stay",
                address=f"City Center, {destination}",
                nightly_price=round(standard_nightly, 2),
                total_price=round(standard_nightly * nights, 2),
                rating=4.2,
                review_count=420,
                latitude=latitude,
                longitude=longitude,
                booking_link="https://example.com/mock-hotel-1",
                source="mock",
                amenities=["wifi", "breakfast", "family rooms"],
                distance_to_center_km=1.2,
            ),
            HotelOption(
                name=f"{destination} Comfort Suites",
                address=f"Tourist District, {destination}",
                nightly_price=round(comfort_nightly, 2),
                total_price=round(comfort_nightly * nights, 2),
                rating=4.4,
                review_count=318,
                latitude=round(latitude + 0.02, 4),
                longitude=round(longitude + 0.02, 4),
                booking_link="https://example.com/mock-hotel-2",
                source="mock",
                amenities=["wifi", "pool", "restaurant"],
                distance_to_center_km=2.0,
            ),
            HotelOption(
                name=f"{destination} Grand Heritage",
                address=f"Premium District, {destination}",
                nightly_price=round(luxury_nightly, 2),
                total_price=round(luxury_nightly * nights, 2),
                rating=4.8,
                review_count=760,
                latitude=round(latitude - 0.02, 4),
                longitude=round(longitude - 0.02, 4),
                booking_link="https://example.com/mock-hotel-4",
                source="mock",
                amenities=["wifi", "spa", "pool", "restaurant", "concierge"],
                distance_to_center_km=1.6,
            ),
        ]
