from __future__ import annotations

from app.models.schemas import BudgetBreakdown, DailyPlan, HotelOption, TripRequest
from app.services.ollama_client import OllamaClient


class ItineraryAgent:
    def __init__(self, ollama_client: OllamaClient) -> None:
        self.ollama_client = ollama_client

    async def summarize(
        self,
        request: TripRequest,
        hotel: HotelOption | None,
        daily_plans: list[DailyPlan],
        budget: BudgetBreakdown,
    ) -> tuple[str, str]:
        hotel_name = hotel.name if hotel else "No hotel selected"
        prompt = (
            f"Destination: {request.destination}\n"
            f"Days: {request.days}\n"
            f"Preferences: {', '.join(request.preferences)}\n"
            f"Hotel preference: {request.hotel_preference}\n"
            f"Transport mode: {request.transport_mode}\n"
            f"Hotel: {hotel_name}\n"
            f"Budget status: {'within budget' if budget.within_budget else 'over budget'}\n"
            "Write a concise academic-demo-friendly itinerary summary in 5-6 lines."
        )
        summary = await self.ollama_client.generate_text(prompt)
        if not summary:
            summary = (
                f"This {request.days}-day itinerary for {request.destination} balances "
                f"{', '.join(request.preferences)} while keeping travel times practical."
            )

        hotel_prompt = (
            f"Hotel: {hotel_name}\n"
            f"Hotel preference: {request.hotel_preference}\n"
            "Explain in 3 lines why this hotel is a sensible recommendation for the trip."
        )
        hotel_reason = await self.ollama_client.generate_text(hotel_prompt)
        if not hotel_reason:
            hotel_reason = (
                f"{hotel_name} was selected for its balance of price, connectivity, and user suitability."
                if hotel
                else "The system continued without a hotel because no reliable hotel result was available."
            )
        return summary, hotel_reason
