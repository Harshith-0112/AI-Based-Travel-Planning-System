import asyncio

from app.providers.mock_hotel_provider import MockHotelProvider


def test_mock_hotel_provider_normalization() -> None:
    provider = MockHotelProvider()
    hotels = asyncio.run(
        provider.search_hotels("Mysore", "2026-04-10", "2026-04-12", adults=2, budget=12000)
    )
    assert hotels
    first = hotels[0]
    assert first.name
    assert first.total_price > 0
    assert first.source == "mock"
