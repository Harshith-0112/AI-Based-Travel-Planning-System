from __future__ import annotations

from app.models.schemas import MCPToolInfo
from app.providers.maps_provider_base import BaseMapsProvider


class GoogleMapsMCPServer:
    """MCP-style wrapper exposing maps tools through a reusable interface."""

    def __init__(self, provider: BaseMapsProvider) -> None:
        self.provider = provider

    def list_tools(self) -> list[MCPToolInfo]:
        return [
            MCPToolInfo(
                name="geocode_location",
                description="Resolve a human-readable location into coordinates.",
                input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
            ),
            MCPToolInfo(
                name="search_nearby_places",
                description="Find nearby attractions for a destination and category.",
                input_schema={
                    "type": "object",
                    "properties": {"destination": {"type": "string"}, "category": {"type": "string"}},
                },
            ),
            MCPToolInfo(
                name="compute_route_matrix",
                description="Compute travel distances and durations between origin and destination points.",
                input_schema={"type": "object"},
            ),
            MCPToolInfo(
                name="get_place_details",
                description="Fetch place metadata by place ID.",
                input_schema={"type": "object", "properties": {"place_id": {"type": "string"}}},
            ),
        ]

    async def geocode_location(self, query: str):
        return await self.provider.geocode_location(query)

    async def search_nearby_places(self, destination: str, category: str):
        return await self.provider.search_nearby_places(destination, category)

    async def compute_route_matrix(self, origins: list[dict], destinations: list[dict], travel_mode: str = "DRIVE"):
        return await self.provider.compute_route_matrix(origins, destinations, travel_mode)

    async def get_place_details(self, place_id: str):
        return await self.provider.get_place_details(place_id)
