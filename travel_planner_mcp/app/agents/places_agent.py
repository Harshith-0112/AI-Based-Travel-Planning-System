from __future__ import annotations

import logging

from app.models.schemas import Attraction, HotelOption, TripRequest
from app.mcp_servers.google_maps_mcp import GoogleMapsMCPServer
from app.providers.fallback_places_provider import FallbackPlacesProvider
from app.providers.ollama_candidate_provider import OllamaCandidateProvider
from app.providers.osm_places_provider import OSMPlacesProvider
from app.providers.place_verifier import PlaceVerifier
from app.providers.verified_places_cache import VerifiedPlacesCache
from app.services.ollama_client import OllamaClient
from app.services.scoring_service import score_attraction
from app.utils.destination_normalizer import display_destination_name


logger = logging.getLogger(__name__)

PLACE_TYPE_MAP = {
    "nature": "park",
    "food": "restaurant",
    "shopping": "shopping_mall",
    "adventure": "tourist_attraction",
    "history": "museum",
    "temples": "hindu_temple",
    "beaches": "tourist_attraction",
    "nightlife": "bar",
    "family": "tourist_attraction",
    "relaxation": "spa",
}


class PlacesAgent:
    def __init__(
        self,
        maps_mcp: GoogleMapsMCPServer,
        ollama_client: OllamaClient,
        fallback_provider: FallbackPlacesProvider | None = None,
        osm_places_provider: OSMPlacesProvider | None = None,
        candidate_provider: OllamaCandidateProvider | None = None,
        place_verifier: PlaceVerifier | None = None,
        verified_cache: VerifiedPlacesCache | None = None,
    ) -> None:
        self.maps_mcp = maps_mcp
        self.ollama_client = ollama_client
        self.fallback_provider = fallback_provider or FallbackPlacesProvider()
        self.osm_places_provider = osm_places_provider or OSMPlacesProvider()
        self.candidate_provider = candidate_provider or OllamaCandidateProvider(ollama_client)
        self.place_verifier = place_verifier or PlaceVerifier(maps_mcp)
        self.verified_cache = verified_cache or VerifiedPlacesCache()

    async def _fallback_places(
        self,
        destination: str,
        preference: str,
        category: str,
        warnings: list[str],
        days: int = 1,
        budget: float | None = None,
    ) -> list[dict]:
        normalized_destination = display_destination_name(destination)

        verified_cache_places = self.verified_cache.get_verified_places(
            normalized_destination,
            preference=preference,
        )
        if verified_cache_places:
            return verified_cache_places

        static_places = self.fallback_provider.get_places(
            normalized_destination,
            preference=preference,
            use_default_if_missing=False,
        )
        if static_places:
            return static_places

        logger.info("Static fallback missing for %s preference=%s", normalized_destination, preference)
        warnings.append(
            f"Static fallback places were unavailable for {normalized_destination}; trying OpenStreetMap."
        )
        osm_places = await self.osm_places_provider.discover_places(
            normalized_destination,
            preference=preference,
            limit=8,
        )
        logger.info(
            "OpenStreetMap discovered %s places for %s preference=%s",
            len(osm_places),
            normalized_destination,
            preference,
        )
        if osm_places:
            self.verified_cache.save_verified_places(normalized_destination, osm_places)
            return osm_places

        warnings.append(
            f"OpenStreetMap did not return usable places for {normalized_destination}; trying verified AI candidates."
        )
        candidates = await self.candidate_provider.generate_candidates(
            normalized_destination,
            preference=preference or category,
            limit=12,
        )
        logger.info(
            "Generated %s Ollama candidates for %s preference=%s",
            len(candidates),
            normalized_destination,
            preference,
        )
        verified_places = await self.place_verifier.verify_candidates(
            normalized_destination,
            candidates,
            preference=preference or category,
        )
        logger.info(
            "Verified %s/%s fallback candidates for %s",
            len(verified_places),
            len(candidates),
            normalized_destination,
        )
        if verified_places:
            self.verified_cache.save_verified_places(normalized_destination, verified_places)
            return verified_places

        curated_places = self.fallback_provider.get_places_for_preferences(
            normalized_destination,
            preferences=[preference],
            days=days,
            budget=budget,
            limit=8,
        )
        if curated_places:
            warnings.append(
                f"Using curated fallback tourist places for {normalized_destination}."
            )
            return curated_places

        warnings.append(
            "Unable to verify attractions for this destination right now. "
            "Please enable Maps API or try a more specific destination."
        )
        return []

    async def get_ranked_attractions(
        self,
        request: TripRequest,
        selected_hotel: HotelOption | None,
    ) -> tuple[list[Attraction], list[str]]:
        warnings: list[str] = []
        unique: dict[str, Attraction] = {}
        destination = display_destination_name(request.destination)

        for preference in request.preferences[:4]:
            category = PLACE_TYPE_MAP.get(preference, "tourist_attraction")

            try:
                places = await self.maps_mcp.search_nearby_places(
                    destination,
                    category,
                )
            except Exception as exc:
                logger.warning("Maps provider failed for %s/%s: %s", destination, preference, exc)
                warnings.append(
                    f"Maps provider failed for {preference}; using fallback cached places."
                )
                places = await self._fallback_places(
                    destination,
                    preference,
                    category,
                    warnings,
                    days=request.days,
                    budget=request.budget,
                )

                if not places:
                    warnings.append(
                        f"Fallback places were unavailable for {preference}; attraction ranking is limited."
                    )
                    continue

            if not places:
                warnings.append(
                    f"Maps provider returned no {preference} places; using fallback cached places."
                )
                places = await self._fallback_places(
                    destination,
                    preference,
                    category,
                    warnings,
                    days=request.days,
                    budget=request.budget,
                )

            for item in places:
                attraction = Attraction(**item)

                route_feasibility = 1.0
                if (
                    selected_hotel
                    and attraction.latitude
                    and attraction.longitude
                    and selected_hotel.latitude
                    and selected_hotel.longitude
                ):
                    route_feasibility = max(
                        0.2,
                        1 - ((selected_hotel.distance_to_center_km or 2.0) / 10),
                    )

                preference_match = 1.0 if preference == attraction.category else 0.7
                attraction.relevance_score = score_attraction(
                    attraction,
                    preference_match,
                    route_feasibility,
                )

                unique[attraction.name] = attraction

        attractions = list(unique.values())
        attractions.sort(key=lambda item: item.relevance_score or 0, reverse=True)

        if attractions:
            prompt = (
                f"Destination: {destination}\n"
                f"Preferences: {', '.join(request.preferences)}\n"
                "In 3 short lines, describe the destination style and why these attractions suit the traveler."
            )
            llm_note = await self.ollama_client.generate_text(prompt)

            if llm_note:
                warnings.append(f"LLM destination insight: {llm_note}")

        return attractions[: request.days * 3], warnings
