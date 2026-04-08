from __future__ import annotations

from collections import defaultdict

from app.models.schemas import Attraction, DailyActivity, DailyPlan, HotelOption, RouteLeg, TripRequest
from app.mcp_servers.google_maps_mcp import GoogleMapsMCPServer
from app.utils.helpers import daterange


class RouteAgent:
    def __init__(self, maps_mcp: GoogleMapsMCPServer) -> None:
        self.maps_mcp = maps_mcp

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
            for idx, slot in enumerate(slots):
                if idx < len(picks):
                    place = picks[idx]
                    travel_minutes = route_legs[idx].duration_minutes if idx < len(route_legs) else None
                    activities.append(
                        DailyActivity(
                            time_slot=slot,
                            title=place.name,
                            description=f"Visit a {place.category.replace('_', ' ')} attraction with a relaxed pace.",
                            place_name=place.name,
                            estimated_cost=350.0,
                            travel_time_from_previous_minutes=travel_minutes,
                            buffer_note="Keep 30-45 minutes buffer for meals and rest.",
                        )
                    )
                else:
                    activities.append(
                        DailyActivity(
                            time_slot=slot,
                            title="Free exploration",
                            description="Use this slot for a local cafe, rest, or flexible exploration.",
                            estimated_cost=250.0,
                            buffer_note="Light buffer slot to avoid overpacking the schedule.",
                        )
                    )

            warnings = []
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
