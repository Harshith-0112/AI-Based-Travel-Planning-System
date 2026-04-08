from __future__ import annotations

from app.models.schemas import HotelOption
from app.providers.hotel_provider_base import BaseHotelProvider


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
        base_price = max(1800.0, min((budget or 12000.0) / max(adults, 1) / 3, 6500.0))
        return [
            HotelOption(
                name=f"{destination} Central Stay",
                address=f"City Center, {destination}",
                nightly_price=round(base_price, 2),
                total_price=round(base_price * 2, 2),
                rating=4.2,
                review_count=420,
                latitude=12.9716,
                longitude=77.5946,
                booking_link="https://example.com/mock-hotel-1",
                source="mock",
                amenities=["wifi", "breakfast", "family rooms"],
                distance_to_center_km=1.2,
            ),
            HotelOption(
                name=f"{destination} Comfort Suites",
                address=f"Tourist District, {destination}",
                nightly_price=round(base_price * 1.15, 2),
                total_price=round(base_price * 2.3, 2),
                rating=4.4,
                review_count=318,
                latitude=12.9616,
                longitude=77.5846,
                booking_link="https://example.com/mock-hotel-2",
                source="mock",
                amenities=["wifi", "pool", "restaurant"],
                distance_to_center_km=2.0,
            ),
            HotelOption(
                name=f"{destination} Budget Inn",
                address=f"Transit Hub, {destination}",
                nightly_price=round(base_price * 0.8, 2),
                total_price=round(base_price * 1.6, 2),
                rating=3.9,
                review_count=205,
                latitude=12.9516,
                longitude=77.5746,
                booking_link="https://example.com/mock-hotel-3",
                source="mock",
                amenities=["wifi", "parking"],
                distance_to_center_km=3.4,
            ),
        ]
