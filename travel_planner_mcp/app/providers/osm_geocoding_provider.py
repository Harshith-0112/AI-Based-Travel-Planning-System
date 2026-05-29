from __future__ import annotations

import logging
from typing import Any

import httpx


logger = logging.getLogger(__name__)


class OSMGeocodingProvider:
    """Free Nominatim geocoder used only to verify fallback place candidates."""

    def __init__(self, timeout_seconds: float = 9.0) -> None:
        self.timeout_seconds = timeout_seconds
        self.base_url = "https://nominatim.openstreetmap.org/search"
        self.headers = {
            "User-Agent": "AITravelPlannerStudentProject/1.0 (fallback-place-verification)"
        }

    async def geocode_destination(self, query: str) -> dict[str, float] | None:
        return await self._geocode(f"{query}, India")

    async def geocode_place(self, place_name: str, destination: str) -> dict[str, float] | None:
        return await self._geocode(f"{place_name}, {destination}, India")

    async def _geocode(self, query: str) -> dict[str, float] | None:
        params = {
            "q": query,
            "format": "jsonv2",
            "limit": 1,
            "countrycodes": "in",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, headers=self.headers) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("OSM geocoding failed for %s: %s", query, exc)
            return None

        if not isinstance(data, list) or not data:
            return None
        return self._coordinates_from_item(data[0])

    @staticmethod
    def _coordinates_from_item(item: Any) -> dict[str, float] | None:
        if not isinstance(item, dict):
            return None
        try:
            return {"latitude": float(item["lat"]), "longitude": float(item["lon"])}
        except (KeyError, TypeError, ValueError):
            return None
