from __future__ import annotations

from app.models.schemas import MCPToolInfo, HotelOption
from app.providers.hotel_provider_base import BaseHotelProvider


class HotelSearchMCPServer:
    """MCP-style hotel search wrapper backed by a pluggable provider."""

    def __init__(self, provider: BaseHotelProvider) -> None:
        self.provider = provider

    def list_tools(self) -> list[MCPToolInfo]:
        return [
            MCPToolInfo(
                name="search_hotels",
                description="Search hotels by destination, dates, traveler count, and budget.",
                input_schema={"type": "object"},
            )
        ]

    async def search_hotels(
        self,
        destination: str,
        check_in: str | None,
        check_out: str | None,
        adults: int = 1,
        budget: float | None = None,
    ) -> list[HotelOption]:
        return await self.provider.search_hotels(destination, check_in, check_out, adults, budget)
