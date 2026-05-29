from __future__ import annotations

from datetime import timedelta

from app.models.schemas import HotelOption, TripRequest
from app.mcp_servers.hotel_mcp import HotelSearchMCPServer
from app.services.scoring_service import score_hotel


class HotelAgent:
    def __init__(self, hotel_mcp: HotelSearchMCPServer) -> None:
        self.hotel_mcp = hotel_mcp

    async def select_hotels(self, request: TripRequest) -> tuple[HotelOption | None, list[HotelOption], list[str]]:
        check_in = request.start_date.isoformat() if request.start_date else None
        check_out = (request.start_date + timedelta(days=request.days)).isoformat() if request.start_date else None
        hotels = await self.hotel_mcp.search_hotels(
            destination=request.destination,
            check_in=check_in,
            check_out=check_out,
            adults=request.travelers,
            budget=request.budget,
        )
        warnings: list[str] = []
        if not hotels:
            warnings.append("No hotel results were found. Planning will continue without a selected hotel.")
            return None, [], warnings

        scored: list[HotelOption] = []
        for hotel in hotels:
            preference_bonus = (
                0.8
                if "family" in request.preferences and any("family" in amenity.lower() for amenity in hotel.amenities)
                else 0.5
            )
            score, reason = score_hotel(hotel, request, preference_bonus)
            hotel.ranking_score = score
            hotel.ranking_reason = reason
            scored.append(hotel)
        scored.sort(key=lambda item: item.ranking_score or 0, reverse=True)
        return scored[0], scored[1:4], warnings
