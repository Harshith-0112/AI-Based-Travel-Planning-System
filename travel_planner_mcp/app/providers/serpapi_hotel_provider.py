from __future__ import annotations

from datetime import date, timedelta
import re

import httpx

from app.models.schemas import HotelOption
from app.providers.hotel_provider_base import BaseHotelProvider
from app.utils.logger import get_logger


logger = get_logger(__name__)


def _to_float(value) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = re.sub(r"[^\d.]", "", value)
        return float(cleaned) if cleaned else 0.0
    return 0.0


class SerpApiHotelProvider(BaseHotelProvider):
    provider_name = "serpapi"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def search_hotels(
        self,
        destination: str,
        check_in: str | None,
        check_out: str | None,
        adults: int = 1,
        budget: float | None = None,
    ) -> list[HotelOption]:
        if not self.api_key:
            raise ValueError("SERPAPI_API_KEY is not configured.")

        if not check_in:
            check_in = date.today().isoformat()
        if not check_out:
            check_out = (date.fromisoformat(check_in) + timedelta(days=2)).isoformat()

        params = {
            "engine": "google_hotels",
            "q": destination,
            "check_in_date": check_in,
            "check_out_date": check_out,
            "adults": adults,
            "api_key": self.api_key,
            "currency": "INR",
            "gl": "in",
            "hl": "en",
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get("https://serpapi.com/search.json", params=params)
            response.raise_for_status()
            payload = response.json()

        properties = payload.get("properties", [])
        normalized: list[HotelOption] = []

        for item in properties:
            nightly = (
                item.get("rate_per_night", {}).get("lowest")
                or item.get("total_rate", {}).get("lowest")
                or 0
            )
            total = item.get("total_rate", {}).get("lowest") or nightly
            gps = item.get("gps_coordinates", {}) or {}

            normalized.append(
                HotelOption(
                    name=item.get("name", "Unknown Hotel"),
                    address=item.get("address", destination),
                    nightly_price=_to_float(nightly),
                    total_price=_to_float(total),
                    rating=item.get("overall_rating"),
                    review_count=item.get("reviews"),
                    latitude=gps.get("latitude"),
                    longitude=gps.get("longitude"),
                    booking_link=item.get("link"),
                    source="serpapi",
                    amenities=item.get("amenities", []),
                )
            )

        logger.info("Normalized %s hotels from SerpAPI", len(normalized))
        return normalized