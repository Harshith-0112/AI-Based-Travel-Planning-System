from __future__ import annotations

import logging
import re
from typing import Any

from app.mcp_servers.google_maps_mcp import GoogleMapsMCPServer
from app.providers.fallback_places_provider import FallbackPlacesProvider
from app.providers.osm_geocoding_provider import OSMGeocodingProvider
from app.utils.destination_normalizer import destination_slug, display_destination_name
from app.utils.helpers import geodesic_distance_km


logger = logging.getLogger(__name__)

FAMOUS_LANDMARK_CITIES = {
    "taj mahal": {"agra"},
    "qutub minar": {"delhi", "new_delhi"},
    "gateway of india": {"mumbai"},
    "mysore palace": {"mysore"},
    "hawa mahal": {"jaipur"},
    "red fort": {"delhi", "new_delhi"},
    "india gate": {"delhi", "new_delhi"},
}


class PlaceVerifier:
    """Verifies AI place candidates by checking coordinates near the destination."""

    def __init__(
        self,
        maps_mcp: GoogleMapsMCPServer,
        osm_provider: OSMGeocodingProvider | None = None,
    ) -> None:
        self.maps_mcp = maps_mcp
        self.osm_provider = osm_provider or OSMGeocodingProvider()

    async def verify_candidates(
        self,
        destination: str,
        candidates: list[dict[str, Any]],
        preference: str | None = None,
    ) -> list[dict[str, Any]]:
        destination_display = display_destination_name(destination)
        destination_coordinates = await self._geocode_destination(destination_display)
        if destination_coordinates is None:
            logger.info("Rejected all candidates for %s: no_coordinates for destination", destination_display)
            return []

        verified_places: list[dict[str, Any]] = []
        for candidate in candidates:
            if self.should_reject_name(candidate.get("name"), destination_display):
                reason = (
                    "wrong_city_landmark"
                    if self._is_wrong_city_landmark(candidate.get("name"), destination_display)
                    else "generic_name"
                )
                logger.info("Rejected candidate %r for %s: %s", candidate.get("name"), destination_display, reason)
                continue

            place_coordinates = await self._geocode_place(candidate["name"], destination_display)
            if place_coordinates is None:
                logger.info("Rejected candidate %r for %s: no_coordinates", candidate.get("name"), destination_display)
                continue

            distance_km = geodesic_distance_km(
                destination_coordinates["latitude"],
                destination_coordinates["longitude"],
                place_coordinates["latitude"],
                place_coordinates["longitude"],
            )
            radius_km = 150.0 if self._is_day_trip(candidate) else 80.0
            if distance_km > radius_km:
                logger.info(
                    "Rejected candidate %r for %s: too_far %.1f km > %.1f km",
                    candidate.get("name"),
                    destination_display,
                    distance_km,
                    radius_km,
                )
                continue

            verified_places.append(
                {
                    "name": candidate["name"],
                    "category": candidate.get("category") or preference or "tourist_attraction",
                    "address": candidate.get("address") or destination_display,
                    "description": candidate.get("description", ""),
                    "estimated_visit_hours": candidate.get("estimated_visit_hours", 2.0),
                    "rating": candidate.get("rating"),
                    "review_count": candidate.get("review_count"),
                    "latitude": place_coordinates["latitude"],
                    "longitude": place_coordinates["longitude"],
                    "source": "verified_ai",
                    "verification_source": place_coordinates["source"],
                    "verified": True,
                }
            )
        return verified_places

    @classmethod
    def should_reject_name(cls, name: Any, destination: str) -> bool:
        normalized_name = re.sub(r"[^a-z0-9]+", " ", str(name).strip().lower()).strip()
        if normalized_name == "central museum":
            return False
        if not FallbackPlacesProvider.is_valid_place_name(name):
            return True
        return cls._is_wrong_city_landmark(name, destination)

    @classmethod
    def _is_wrong_city_landmark(cls, name: Any, destination: str) -> bool:
        normalized_name = re.sub(r"[^a-z0-9]+", " ", str(name).strip().lower()).strip()
        actual_cities = FAMOUS_LANDMARK_CITIES.get(normalized_name)
        if not actual_cities:
            return False
        return destination_slug(destination) not in actual_cities

    @staticmethod
    def _is_day_trip(candidate: dict[str, Any]) -> bool:
        category = str(candidate.get("category", "")).lower()
        return bool(candidate.get("day_trip")) or "day_trip" in category or "day trip" in category

    async def _geocode_destination(self, destination: str) -> dict[str, float | str] | None:
        google_result = await self._geocode_with_google(destination)
        if google_result is not None:
            return google_result
        osm_result = await self.osm_provider.geocode_destination(destination)
        if osm_result is None:
            return None
        return {**osm_result, "source": "openstreetmap"}

    async def _geocode_place(self, place_name: str, destination: str) -> dict[str, float | str] | None:
        google_result = await self._geocode_with_google(f"{place_name}, {destination}, India")
        if google_result is not None:
            return google_result
        osm_result = await self.osm_provider.geocode_place(place_name, destination)
        if osm_result is None:
            return None
        return {**osm_result, "source": "openstreetmap"}

    async def _geocode_with_google(self, query: str) -> dict[str, float | str] | None:
        try:
            result = await self.maps_mcp.geocode_location(query)
        except Exception as exc:
            logger.warning("Google Maps geocoding failed for %s: %s", query, exc)
            return None
        if not isinstance(result, dict):
            return None

        latitude = result.get("latitude", result.get("lat"))
        longitude = result.get("longitude", result.get("lng"))
        try:
            if latitude is None or longitude is None:
                return None
            return {"latitude": float(latitude), "longitude": float(longitude), "source": "google_maps"}
        except (TypeError, ValueError):
            return None
