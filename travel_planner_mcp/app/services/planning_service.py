from __future__ import annotations

from datetime import datetime, timezone

from app.agents.budget_agent import BudgetAgent, rebalance_budget_to_fit
from app.agents.export_agent import ExportAgent
from app.agents.hotel_agent import HotelAgent
from app.agents.input_agent import InputAgent
from app.agents.itinerary_agent import ItineraryAgent
from app.agents.places_agent import PlacesAgent
from app.agents.route_agent import RouteAgent
from app.agents.transport_agent import TransportAgent
from app.mcp_servers.google_maps_mcp import GoogleMapsMCPServer
from app.mcp_servers.hotel_mcp import HotelSearchMCPServer
from app.models.schemas import ProviderStatus, TripPlanResponse, TripRequest
from app.providers.google_maps_provider import GoogleMapsProvider
from app.providers.mock_hotel_provider import MockHotelProvider
from app.providers.mock_maps_provider import MockMapsProvider
from app.providers.serpapi_hotel_provider import SerpApiHotelProvider
from app.services.ollama_client import OllamaClient
from app.services.place_image_service import PlaceImageService
from app.services.scoring_service import build_user_facing_hotel_reason
from app.utils.config import Settings


class PlanningService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.ollama_client = OllamaClient(settings)
        self.maps_provider = self._build_maps_provider()
        self.hotel_provider = self._build_hotel_provider()
        self.maps_mcp = GoogleMapsMCPServer(self.maps_provider)
        self.hotel_mcp = HotelSearchMCPServer(self.hotel_provider)

        self.input_agent = InputAgent()
        self.hotel_agent = HotelAgent(self.hotel_mcp)
        self.places_agent = PlacesAgent(self.maps_mcp, self.ollama_client)
        self.place_image_service = PlaceImageService(self.maps_mcp)
        self.route_agent = RouteAgent(self.maps_mcp, self.ollama_client)
        self.transport_agent = TransportAgent(self.maps_mcp)
        self.budget_agent = BudgetAgent()
        self.itinerary_agent = ItineraryAgent(self.ollama_client)
        self.export_agent = ExportAgent()

    def _build_hotel_provider(self):
        if self.settings.hotel_provider.lower() == "serpapi" and self.settings.serpapi_api_key:
            return SerpApiHotelProvider(self.settings.serpapi_api_key)
        return MockHotelProvider()

    def _build_maps_provider(self):
        if self.settings.maps_provider.lower() == "google" and self.settings.google_maps_api_key:
            return GoogleMapsProvider(self.settings.google_maps_api_key)
        return MockMapsProvider()

    async def get_provider_status(self) -> ProviderStatus:
        notes: list[str] = []
        ollama_ok = await self.ollama_client.health_check()
        if not ollama_ok:
            notes.append("Ollama is not reachable. The system will use deterministic fallback text where needed.")
        if self.hotel_provider.provider_name == "mock":
            notes.append("Hotel search is running in fallback mock mode.")
        if self.maps_provider.provider_name == "mock":
            notes.append("Maps and route calculations are running in fallback mock mode.")
        return ProviderStatus(
            ollama_reachable=ollama_ok,
            google_maps_api_key_set=bool(self.settings.google_maps_api_key),
            serpapi_api_key_set=bool(self.settings.serpapi_api_key),
            active_hotel_provider=self.hotel_provider.provider_name,
            active_maps_provider=self.maps_provider.provider_name,
            notes=notes,
        )

    async def plan_trip(self, request: TripRequest) -> TripPlanResponse:
        normalized_request = self.input_agent.normalize(request)
        provider_status = await self.get_provider_status()

        notes = list(provider_status.notes)
        hotel, alternative_hotels, hotel_notes = await self.hotel_agent.select_hotels(normalized_request)
        notes.extend(hotel_notes)

        transport = await self.transport_agent.estimate_transport(
            starting_location=normalized_request.starting_location,
            destination=normalized_request.destination,
            travelers=normalized_request.travelers,
            transport_mode=normalized_request.transport_mode,
            budget=normalized_request.budget,
        )

        attractions, attraction_notes = await self.places_agent.get_ranked_attractions(normalized_request, hotel)
        attractions = await self.place_image_service.enrich_attractions(attractions, normalized_request.destination)
        notes.extend(attraction_notes)

        daily_plans = await self.route_agent.build_daily_skeleton(normalized_request, hotel, attractions)
        budget_breakdown = self.budget_agent.estimate(normalized_request, hotel, daily_plans, transport)
        hotel_options = [item for item in [hotel, *alternative_hotels] if item is not None]
        cheaper_transport_options = await self.transport_agent.cheaper_practical_options(
            starting_location=normalized_request.starting_location,
            destination=normalized_request.destination,
            travelers=normalized_request.travelers,
            current_mode=transport.mode,
        )
        hotel, transport, budget_breakdown, hotel_options = rebalance_budget_to_fit(
            normalized_request,
            budget_breakdown,
            hotel,
            hotel_options,
            transport,
            cheaper_transport_options,
        )
        alternative_hotels = [
            item for item in hotel_options
            if hotel is None or item.name != hotel.name or item.address != hotel.address
        ][:3]
        if not budget_breakdown.within_budget:
            notes.append(
                f"Estimated cost exceeds budget by {budget_breakdown.over_budget_amount:.2f}. "
                "The itinerary is still generated for comparison."
            )
        if normalized_request.budget / normalized_request.days < 1500:
            notes.append("Budget is very tight for a multi-day trip; expect reduced hotel quality or fewer activities.")

        summary, hotel_reason = await self.itinerary_agent.summarize(
            normalized_request,
            hotel,
            daily_plans,
            budget_breakdown,
        )
        hotel_reason = build_user_facing_hotel_reason(hotel, normalized_request)
        return TripPlanResponse(
            trip_request=normalized_request,
            provider_status=provider_status,
            hotel=hotel,
            alternative_hotels=alternative_hotels,
            transport=transport,
            attractions=attractions,
            daily_plans=daily_plans,
            budget_breakdown=budget_breakdown,
            summary=summary,
            hotel_selection_reason=hotel_reason,
            notes=notes,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
