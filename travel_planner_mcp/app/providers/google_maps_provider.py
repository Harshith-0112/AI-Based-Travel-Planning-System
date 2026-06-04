from __future__ import annotations

from typing import Any

import httpx

from app.providers.maps_provider_base import BaseMapsProvider


class GoogleMapsProvider(BaseMapsProvider):
    provider_name = "google"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def _ensure_key(self) -> None:
        if not self.api_key:
            raise ValueError("GOOGLE_MAPS_API_KEY is not configured.")

    async def geocode_location(self, query: str) -> dict[str, Any]:
        self._ensure_key()
        params = {"address": query, "key": self.api_key}
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get("https://maps.googleapis.com/maps/api/geocode/json", params=params)
            response.raise_for_status()
            payload = response.json()
        result = payload["results"][0]
        location = result["geometry"]["location"]
        return {
            "query": query,
            "latitude": location["lat"],
            "longitude": location["lng"],
            "formatted_address": result["formatted_address"],
            "place_id": result.get("place_id"),
        }

    async def search_nearby_places(self, destination: str, category: str) -> list[dict[str, Any]]:
        self._ensure_key()
        geo = await self.geocode_location(destination)
        headers = {
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "places.id,places.displayName,places.formattedAddress,"
                "places.location,places.rating,places.userRatingCount,places.types,places.photos"
            ),
        }
        body = {
            "includedTypes": [category],
            "maxResultCount": 6,
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": geo["latitude"], "longitude": geo["longitude"]},
                    "radius": 10000.0,
                }
            },
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://places.googleapis.com/v1/places:searchNearby",
                headers=headers,
                json=body,
            )
            response.raise_for_status()
            payload = response.json()
        return [
            {
                "name": item["displayName"]["text"],
                "category": category,
                "address": item.get("formattedAddress"),
                "latitude": item["location"]["latitude"],
                "longitude": item["location"]["longitude"],
                "rating": item.get("rating"),
                "review_count": item.get("userRatingCount"),
                "estimated_visit_hours": 2.0,
                "place_id": item.get("id"),
                "image_url": self._photo_url(item),
                "source": "google_maps",
            }
            for item in payload.get("places", [])
        ]

    async def compute_route_matrix(
        self,
        origins: list[dict[str, Any]],
        destinations: list[dict[str, Any]],
        travel_mode: str = "DRIVE",
    ) -> list[dict[str, Any]]:
        self._ensure_key()
        headers = {
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "originIndex,destinationIndex,distanceMeters,duration,status",
        }
        body = {
            "origins": [
                {"waypoint": {"location": {"latLng": {"latitude": item["latitude"], "longitude": item["longitude"]}}}}
                for item in origins
            ],
            "destinations": [
                {"waypoint": {"location": {"latLng": {"latitude": item["latitude"], "longitude": item["longitude"]}}}}
                for item in destinations
            ],
            "travelMode": travel_mode,
        }
        async with httpx.AsyncClient(timeout=25.0) as client:
            response = await client.post(
                "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix",
                headers=headers,
                json=body,
            )
            response.raise_for_status()
            rows = response.json()
        normalized: list[dict[str, Any]] = []
        for row in rows:
            origin_index = row["originIndex"]
            destination_index = row["destinationIndex"]
            duration_seconds = float(str(row.get("duration", "0s")).replace("s", "") or 0)
            normalized.append(
                {
                    "origin_name": origins[origin_index]["name"],
                    "destination_name": destinations[destination_index]["name"],
                    "travel_mode": travel_mode,
                    "distance_km": round(row.get("distanceMeters", 0) / 1000, 2),
                    "duration_minutes": round(duration_seconds / 60, 1),
                    "provider": "google",
                }
            )
        return normalized

    async def get_place_details(self, place_id: str) -> dict[str, Any]:
        self._ensure_key()
        headers = {
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "id,displayName,formattedAddress,regularOpeningHours.weekdayDescriptions,"
                "websiteUri,editorialSummary,photos"
            ),
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(f"https://places.googleapis.com/v1/places/{place_id}", headers=headers)
            response.raise_for_status()
            payload = response.json()
        return {
            "place_id": payload.get("id"),
            "name": payload.get("displayName", {}).get("text"),
            "address": payload.get("formattedAddress"),
            "opening_hours": payload.get("regularOpeningHours", {}).get("weekdayDescriptions", []),
            "website": payload.get("websiteUri"),
            "description": payload.get("editorialSummary", {}).get("text"),
            "photo_url": self._photo_url(payload),
        }

    def _photo_url(self, place: dict[str, Any]) -> str | None:
        photos = place.get("photos") or []
        if not photos:
            return None
        photo_name = photos[0].get("name")
        if not photo_name:
            return None
        return (
            f"https://places.googleapis.com/v1/{photo_name}/media"
            f"?maxWidthPx=900&maxHeightPx=600&key={self.api_key}"
        )
