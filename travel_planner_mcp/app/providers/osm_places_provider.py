from __future__ import annotations

import logging
from typing import Any

import httpx

from app.providers.fallback_places_provider import FallbackPlacesProvider
from app.providers.osm_geocoding_provider import OSMGeocodingProvider


logger = logging.getLogger(__name__)


PREFERENCE_TAGS = {
    "history": [
        ('historic', None),
        ("tourism", "museum"),
        ("tourism", "attraction"),
    ],
    "temples": [
        ("amenity", "place_of_worship"),
    ],
    "food": [
        ("amenity", "restaurant"),
        ("amenity", "cafe"),
    ],
    "beaches": [
        ("natural", "beach"),
    ],
    "nature": [
        ("leisure", "park"),
        ("tourism", "viewpoint"),
    ],
    "shopping": [
        ("shop", "mall"),
        ("tourism", "attraction"),
    ],
    "default": [
        ("tourism", "attraction"),
        ("historic", None),
    ],
}


class OSMPlacesProvider:
    """Discovers named POIs from OpenStreetMap Overpass around a destination."""

    def __init__(
        self,
        geocoding_provider: OSMGeocodingProvider | None = None,
        timeout_seconds: float = 28.0,
        radius_meters: int = 25_000,
    ) -> None:
        self.geocoding_provider = geocoding_provider or OSMGeocodingProvider()
        self.timeout_seconds = timeout_seconds
        self.radius_meters = radius_meters
        self.base_url = "https://overpass-api.de/api/interpreter"
        self.headers = {
            "User-Agent": "AITravelPlannerStudentProject/1.0 (osm-place-discovery)"
        }

    async def discover_places(
        self,
        destination: str,
        preference: str | None = None,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        destination_coordinates = await self.geocoding_provider.geocode_destination(destination)
        if destination_coordinates is None:
            logger.info("OSM discovery skipped for %s: destination geocode failed", destination)
            return []

        query = self._build_overpass_query(
            latitude=destination_coordinates["latitude"],
            longitude=destination_coordinates["longitude"],
            preference=preference,
        )
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, headers=self.headers) as client:
                response = await client.post(self.base_url, data={"data": query})
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("OSM Overpass discovery failed for %s: %s", destination, exc)
            return []

        return self._parse_elements(payload, destination, preference, limit)

    def _build_overpass_query(
        self,
        latitude: float,
        longitude: float,
        preference: str | None,
    ) -> str:
        clauses = []
        for key, value in PREFERENCE_TAGS.get(preference or "", PREFERENCE_TAGS["default"]):
            if value is None:
                selector = f'["{key}"]'
            else:
                selector = f'["{key}"="{value}"]'
            clauses.extend(
                [
                    f"node{selector}(around:{self.radius_meters},{latitude},{longitude});",
                    f"way{selector}(around:{self.radius_meters},{latitude},{longitude});",
                    f"relation{selector}(around:{self.radius_meters},{latitude},{longitude});",
                ]
            )

        joined_clauses = "\n  ".join(clauses)
        return f"""
[out:json][timeout:{int(self.timeout_seconds)}];
(
  {joined_clauses}
);
out center tags {max(20, self.radius_meters // 1000)};
"""

    @staticmethod
    def _parse_elements(
        payload: Any,
        destination: str,
        preference: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        if not isinstance(payload, dict):
            return []
        elements = payload.get("elements")
        if not isinstance(elements, list):
            return []

        places: list[dict[str, Any]] = []
        seen: set[str] = set()
        for element in elements:
            if not isinstance(element, dict):
                continue
            tags = element.get("tags")
            if not isinstance(tags, dict):
                continue
            name = tags.get("name")
            if not FallbackPlacesProvider.is_valid_place_name(name):
                continue
            latitude = element.get("lat") or (element.get("center") or {}).get("lat")
            longitude = element.get("lon") or (element.get("center") or {}).get("lon")
            if latitude is None or longitude is None:
                continue

            normalized_name = str(name).strip().lower()
            if normalized_name in seen:
                continue
            seen.add(normalized_name)

            try:
                lat_value = float(latitude)
                lon_value = float(longitude)
            except (TypeError, ValueError):
                continue

            category = OSMPlacesProvider._category_from_tags(tags, preference)
            places.append(
                {
                    "name": str(name).strip(),
                    "category": category,
                    "address": destination,
                    "description": OSMPlacesProvider._description_from_tags(tags, category),
                    "estimated_visit_hours": 2.0,
                    "rating": None,
                    "review_count": None,
                    "latitude": lat_value,
                    "longitude": lon_value,
                    "source": "openstreetmap",
                    "verification_source": "openstreetmap",
                    "verified": True,
                }
            )
            if len(places) >= limit:
                break

        return places

    @staticmethod
    def _category_from_tags(tags: dict[str, Any], preference: str | None) -> str:
        if tags.get("amenity") in {"restaurant", "cafe"}:
            return "food"
        if tags.get("amenity") == "place_of_worship":
            return "temples"
        if tags.get("natural") == "beach":
            return "beaches"
        if tags.get("leisure") == "park" or tags.get("tourism") == "viewpoint":
            return "nature"
        if tags.get("shop") == "mall":
            return "shopping"
        if tags.get("historic") or tags.get("tourism") == "museum":
            return "history"
        return preference or "tourist_attraction"

    @staticmethod
    def _description_from_tags(tags: dict[str, Any], category: str) -> str:
        if tags.get("description"):
            return str(tags["description"])
        if tags.get("tourism"):
            return f"OpenStreetMap-listed {tags['tourism']} suitable for a {category} stop."
        if tags.get("historic"):
            return f"OpenStreetMap-listed historic place suitable for a {category} stop."
        if tags.get("amenity"):
            return f"OpenStreetMap-listed {tags['amenity']} suitable for a {category} stop."
        return f"OpenStreetMap-listed place suitable for a {category} stop."
