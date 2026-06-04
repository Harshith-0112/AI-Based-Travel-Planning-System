from __future__ import annotations

import logging
from typing import Any

import httpx

from app.mcp_servers.google_maps_mcp import GoogleMapsMCPServer
from app.models.schemas import Attraction
from app.providers.verified_places_cache import VerifiedPlacesCache


logger = logging.getLogger(__name__)


class PlaceImageService:
    """Finds reliable attraction images without using stock-photo fallbacks."""

    def __init__(
        self,
        maps_mcp: GoogleMapsMCPServer,
        verified_cache: VerifiedPlacesCache | None = None,
    ) -> None:
        self.maps_mcp = maps_mcp
        self.verified_cache = verified_cache or VerifiedPlacesCache()

    async def enrich_attractions(self, attractions: list[Attraction], destination: str) -> list[Attraction]:
        for attraction in attractions:
            attraction.image_url = await self.get_image_url(attraction, destination)
        return attractions

    async def get_image_url(self, attraction: Attraction, destination: str) -> str | None:
        if attraction.image_url:
            self._cache_image(destination, attraction, attraction.image_url, source="google_places_photo")
            return attraction.image_url

        image_url = await self._google_places_photo(attraction)
        if image_url:
            self._cache_image(destination, attraction, image_url, source="google_places_photo")
            return image_url

        cached_url = self.verified_cache.get_image_url(destination, attraction.name)
        if cached_url:
            return cached_url

        image_url = await self._wikimedia_image_search(attraction.name, destination)
        if image_url:
            self._cache_image(destination, attraction, image_url, source="wikimedia_commons")
            return image_url

        return None

    async def _google_places_photo(self, attraction: Attraction) -> str | None:
        if not attraction.place_id:
            return None
        try:
            details = await self.maps_mcp.get_place_details(attraction.place_id)
        except Exception as exc:
            logger.info("Google Places photo lookup failed for %s: %s", attraction.name, exc)
            return None

        if not isinstance(details, dict):
            return None
        image_url = details.get("photo_url")
        return str(image_url) if image_url else None

    async def _wikimedia_image_search(self, place_name: str, destination: str) -> str | None:
        query = f"{place_name} {destination}"
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": 6,
            "gsrlimit": 1,
            "prop": "imageinfo",
            "iiprop": "url",
            "origin": "*",
        }
        headers = {"User-Agent": "AITravelPlanner/1.0 (student project image lookup)"}
        try:
            async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
                response = await client.get("https://commons.wikimedia.org/w/api.php", params=params)
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            logger.info("Wikimedia image lookup failed for %s: %s", place_name, exc)
            return None

        pages = payload.get("query", {}).get("pages", {})
        if not isinstance(pages, dict):
            return None
        for page in pages.values():
            image_info = page.get("imageinfo", []) if isinstance(page, dict) else []
            if image_info and image_info[0].get("url"):
                return str(image_info[0]["url"])
        return None

    def _cache_image(
        self,
        destination: str,
        attraction: Attraction,
        image_url: str,
        source: str,
    ) -> None:
        try:
            self.verified_cache.cache_image_url(
                destination,
                attraction.model_dump(),
                image_url,
                source=source,
            )
        except Exception as exc:
            logger.info("Image URL cache write failed for %s: %s", attraction.name, exc)
