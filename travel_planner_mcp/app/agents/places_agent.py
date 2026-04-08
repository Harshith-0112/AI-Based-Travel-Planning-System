from __future__ import annotations

from app.models.schemas import Attraction, HotelOption, TripRequest
from app.mcp_servers.google_maps_mcp import GoogleMapsMCPServer
from app.services.ollama_client import OllamaClient
from app.services.scoring_service import score_attraction


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
    def __init__(self, maps_mcp: GoogleMapsMCPServer, ollama_client: OllamaClient) -> None:
        self.maps_mcp = maps_mcp
        self.ollama_client = ollama_client

    async def get_ranked_attractions(
        self,
        request: TripRequest,
        selected_hotel: HotelOption | None,
    ) -> tuple[list[Attraction], list[str]]:
        warnings: list[str] = []
        unique: dict[str, Attraction] = {}
        for preference in request.preferences[:4]:
            category = PLACE_TYPE_MAP.get(preference, "tourist_attraction")
            try:
                places = await self.maps_mcp.search_nearby_places(request.destination, category)
            except Exception:
                warnings.append(f"Maps provider failed for {preference}; fallback attraction ranking is limited.")
                continue

            for item in places:
                attraction = Attraction(**item)
                route_feasibility = 1.0
                if selected_hotel and attraction.latitude and attraction.longitude and selected_hotel.latitude and selected_hotel.longitude:
                    route_feasibility = max(0.2, 1 - ((selected_hotel.distance_to_center_km or 2.0) / 10))
                preference_match = 1.0 if preference == attraction.category else 0.7
                attraction.relevance_score = score_attraction(attraction, preference_match, route_feasibility)
                unique[attraction.name] = attraction

        attractions = list(unique.values())
        attractions.sort(key=lambda item: item.relevance_score or 0, reverse=True)

        if attractions:
            prompt = (
                f"Destination: {request.destination}\n"
                f"Preferences: {', '.join(request.preferences)}\n"
                "In 3 short lines, describe the destination style and why these attractions suit the traveler."
            )
            llm_note = await self.ollama_client.generate_text(prompt)
            if llm_note:
                warnings.append(f"LLM destination insight: {llm_note}")
        return attractions[: request.days * 3], warnings
