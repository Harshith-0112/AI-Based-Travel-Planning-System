from __future__ import annotations

from datetime import date

from app.models.schemas import SUPPORTED_PREFERENCES, TripRequest
from app.utils.destination_normalizer import display_destination_name


class InputAgent:
    """Validates and normalizes incoming trip inputs."""

    def normalize(self, request: TripRequest) -> TripRequest:
        preferences = [item for item in request.preferences if item in SUPPORTED_PREFERENCES]
        if not preferences:
            preferences = ["relaxation"]
        start_date = request.start_date or date.today()
        return TripRequest(
            destination=display_destination_name(request.destination),
            budget=max(request.budget, 1000),
            days=min(max(request.days, 1), 14),
            preferences=preferences,
            start_date=start_date,
            travelers=max(request.travelers, 1),
            starting_location=request.starting_location,
            hotel_preference=request.hotel_preference,
            transport_mode=request.transport_mode,
        )
