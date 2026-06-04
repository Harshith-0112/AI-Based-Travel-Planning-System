from __future__ import annotations

from collections import defaultdict
import json
import re

from app.models.schemas import Attraction, DailyActivity, DailyPlan, HotelOption, RouteLeg, TripRequest
from app.mcp_servers.google_maps_mcp import GoogleMapsMCPServer
from app.services.ollama_client import OllamaClient
from app.utils.helpers import daterange


CATEGORY_COST_ESTIMATES = {
    "adventure": 1200.0,
    "bar": 900.0,
    "beaches": 350.0,
    "family": 600.0,
    "food": 500.0,
    "hindu_temple": 150.0,
    "history": 350.0,
    "museum": 400.0,
    "nature": 250.0,
    "park": 200.0,
    "relaxation": 700.0,
    "restaurant": 500.0,
    "shopping": 800.0,
    "shopping_mall": 800.0,
    "spa": 1200.0,
    "temples": 150.0,
    "tourist_attraction": 350.0,
}


def estimate_activity_cost(category: str) -> float:
    return CATEGORY_COST_ESTIMATES.get(category, 350.0)


DESCRIPTION_CACHE: dict[str, dict] = {}


def build_place_description(place: Attraction, destination: str, category: str) -> dict:
    category_text = category.replace("_", " ")
    tag_text = ", ".join(place.tags[:3]) if place.tags else category_text
    base_description = (
        place.description
        or f"A recommended {category_text} stop in {destination}, suitable for this part of the day."
    )
    if place.best_time:
        base_description = f"{base_description} Best experienced around {place.best_time.lower()}."
    return {
        "description": base_description,
        "highlights": [
            f"Known for {tag_text}.",
            f"Good fit for a {category_text} focused itinerary.",
        ],
        "visit_tips": [
            f"Best time to visit: {place.best_time}." if place.best_time else "Check current opening hours before visiting.",
            "Keep some buffer time for local travel and meals.",
        ],
    }


class RouteAgent:
    def __init__(self, maps_mcp: GoogleMapsMCPServer, ollama_client: OllamaClient | None = None) -> None:
        self.maps_mcp = maps_mcp
        self.ollama_client = ollama_client

    async def _description_details(self, place: Attraction, destination: str) -> dict:
        cache_key = f"{destination.lower()}::{place.name.lower()}"
        if cache_key in DESCRIPTION_CACHE:
            return DESCRIPTION_CACHE[cache_key]

        details = build_place_description(place, destination, place.category)
        if not place.description and self.ollama_client:
            prompt = f"""
The place below is already verified for {destination}. Do not invent places.
Place: {place.name}
Category: {place.category}
Generate 2-3 short useful visitor points.
Do not invent exact ticket prices or timings.
Return only JSON:
{{
  "description": "...",
  "highlights": ["...", "..."],
  "visit_tips": ["..."]
}}
"""
            try:
                text = await self.ollama_client.generate_text(prompt, timeout=10)
                match = re.search(r"\{.*\}", text or "", re.DOTALL)
                if match:
                    parsed = json.loads(match.group(0))
                    if isinstance(parsed, dict):
                        details = {
                            "description": parsed.get("description") or details["description"],
                            "highlights": [
                                str(item) for item in parsed.get("highlights", [])[:3] if item
                            ]
                            or details["highlights"],
                            "visit_tips": [
                                str(item) for item in parsed.get("visit_tips", [])[:3] if item
                            ]
                            or details["visit_tips"],
                        }
            except Exception:
                details = build_place_description(place, destination, place.category)

        DESCRIPTION_CACHE[cache_key] = details
        return details

    async def build_daily_skeleton(
        self,
        request: TripRequest,
        hotel: HotelOption | None,
        attractions: list[Attraction],
    ) -> list[DailyPlan]:
        by_day: dict[int, list[Attraction]] = defaultdict(list)
        for index, attraction in enumerate(attractions):
            day = (index % request.days) + 1
            if len(by_day[day]) < 3:
                by_day[day].append(attraction)

        dated_days = daterange(request.start_date, request.days)
        daily_plans: list[DailyPlan] = []
        for day_number in range(1, request.days + 1):
            picks = by_day.get(day_number, [])
            route_legs: list[RouteLeg] = []
            if hotel and picks:
                origins = [{"name": hotel.name, "latitude": hotel.latitude, "longitude": hotel.longitude}]
                destinations = [
                    {"name": item.name, "latitude": item.latitude, "longitude": item.longitude}
                    for item in picks
                    if item.latitude is not None and item.longitude is not None
                ]
                if destinations:
                    try:
                        raw_legs = await self.maps_mcp.compute_route_matrix(origins, destinations)
                        route_legs = [RouteLeg(**leg) for leg in raw_legs]
                    except Exception:
                        route_legs = []

            activities: list[DailyActivity] = []
            slots = ["morning", "afternoon", "evening"]
            for idx, place in enumerate(picks[: len(slots)]):
                slot = slots[idx]
                travel_minutes = route_legs[idx].duration_minutes if idx < len(route_legs) else None
                details = await self._description_details(place, request.destination)
                activities.append(
                    DailyActivity(
                        time_slot=slot,
                        title=place.name,
                        description=details["description"],
                        highlights=details["highlights"],
                        visit_tips=details["visit_tips"],
                        image_url=place.image_url,
                        tags=place.tags,
                        best_time=place.best_time,
                        place_name=place.name,
                        estimated_cost=place.estimated_cost or estimate_activity_cost(place.category),
                        cost_source="estimated",
                        travel_time_from_previous_minutes=travel_minutes,
                        buffer_note="Keep 30-45 minutes buffer for meals and rest.",
                    )
                )

            warnings = []
            if not picks:
                warnings.append(
                    "Unable to verify attractions for this destination right now. Please enable Maps API or try a more specific destination."
                )
            if any((leg.duration_minutes > 60 for leg in route_legs)):
                warnings.append("One or more commutes are longer than 60 minutes.")

            daily_plans.append(
                DailyPlan(
                    day_number=day_number,
                    date=dated_days[day_number - 1],
                    theme=f"{request.preferences[(day_number - 1) % len(request.preferences)].title()} Focus",
                    activities=activities,
                    route_legs=route_legs,
                    estimated_cost=sum(item.estimated_cost for item in activities),
                    warnings=warnings,
                )
            )
        return daily_plans
