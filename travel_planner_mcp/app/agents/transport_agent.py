from __future__ import annotations

from app.mcp_servers.google_maps_mcp import GoogleMapsMCPServer
from app.models.schemas import TransportOption
from app.utils.helpers import geodesic_distance_km


KNOWN_CITY_DISTANCES_KM: dict[tuple[str, str], float] = {
    ("hyderabad", "warangal"): 150.0,
    ("bangalore", "hyderabad"): 570.0,
    ("bengaluru", "hyderabad"): 570.0,
    ("hyderabad", "goa"): 660.0,
    ("bangalore", "goa"): 560.0,
    ("bengaluru", "goa"): 560.0,
    ("hyderabad", "mysore"): 720.0,
    ("bangalore", "mysore"): 145.0,
    ("bengaluru", "mysore"): 145.0,
}


class TransportAgent:
    def __init__(self, maps_mcp: GoogleMapsMCPServer) -> None:
        self.maps_mcp = maps_mcp

    async def estimate_transport(
        self,
        starting_location: str | None,
        destination: str,
        travelers: int,
        transport_mode: str,
        budget: float,
    ) -> TransportOption:
        distance_km, source = await self._estimate_distance(starting_location, destination)
        mode = self._select_mode(transport_mode, distance_km, travelers, budget)
        cost, duration_hours = self._estimate_mode_cost_and_time(mode, distance_km, travelers)
        reason = self._build_reason(mode, distance_km, transport_mode, source)
        return TransportOption(
            mode=mode,
            estimated_cost=round(cost, 2),
            estimated_duration_hours=round(duration_hours, 1),
            reason=reason,
            source=source,
        )

    async def cheaper_practical_options(
        self,
        starting_location: str | None,
        destination: str,
        travelers: int,
        current_mode: str,
    ) -> list[TransportOption]:
        distance_km, source = await self._estimate_distance(starting_location, destination)
        if distance_km < 250:
            modes = ["bus", "car"]
        elif distance_km <= 700:
            modes = ["train", "bus"]
        else:
            modes = ["train", "flight"]

        options: list[TransportOption] = []
        for mode in modes:
            if mode == current_mode:
                continue
            cost, duration_hours = self._estimate_mode_cost_and_time(mode, distance_km, travelers)
            options.append(
                TransportOption(
                    mode=mode,
                    estimated_cost=round(cost, 2),
                    estimated_duration_hours=round(duration_hours, 1),
                    reason=(
                        f"Adjusted to {mode} to help keep the trip within budget. "
                        f"Distance source: {source}."
                    ),
                    source=source,
                )
            )
        return options

    async def _estimate_distance(
        self,
        starting_location: str | None,
        destination: str,
    ) -> tuple[float, str]:
        if not starting_location:
            return 350.0, "estimated"

        provider_name = getattr(getattr(self.maps_mcp, "provider", None), "provider_name", "")
        if provider_name == "mock":
            return self._known_distance(starting_location, destination), "estimated"

        try:
            origin = await self.maps_mcp.geocode_location(starting_location)
            target = await self.maps_mcp.geocode_location(destination)
            distance = geodesic_distance_km(
                origin["latitude"],
                origin["longitude"],
                target["latitude"],
                target["longitude"],
            )
            return max(distance, 25.0), "maps_geocode"
        except Exception:
            fallback = self._known_distance(starting_location, destination)
            return fallback, "estimated"

    @staticmethod
    def _known_distance(starting_location: str, destination: str) -> float:
        origin = starting_location.strip().lower()
        target = destination.strip().lower()
        return (
            KNOWN_CITY_DISTANCES_KM.get((origin, target))
            or KNOWN_CITY_DISTANCES_KM.get((target, origin))
            or 500.0
        )

    @staticmethod
    def _select_mode(
        requested_mode: str,
        distance_km: float,
        travelers: int,
        budget: float,
    ) -> str:
        if requested_mode != "auto":
            return requested_mode

        if distance_km < 250:
            return "car" if travelers >= 3 else "bus"
        if distance_km <= 700:
            return "train"

        flight_cost, _ = TransportAgent._estimate_mode_cost_and_time("flight", distance_km, travelers)
        return "flight" if flight_cost <= budget * 0.35 else "train"

    @staticmethod
    def _estimate_mode_cost_and_time(mode: str, distance_km: float, travelers: int) -> tuple[float, float]:
        safe_travelers = max(travelers, 1)
        if mode == "flight":
            return (
                2500.0 * safe_travelers + distance_km * 5.5 * safe_travelers,
                distance_km / 650 + 3.0,
            )
        if mode == "train":
            return 180.0 * safe_travelers + distance_km * 1.8 * safe_travelers, distance_km / 55 + 1.5
        if mode == "bus":
            return 120.0 * safe_travelers + distance_km * 2.4 * safe_travelers, distance_km / 45 + 1.0
        return 600.0 + distance_km * 12.0, distance_km / 55 + 0.5

    @staticmethod
    def _build_reason(mode: str, distance_km: float, requested_mode: str, source: str) -> str:
        if requested_mode == "auto":
            if distance_km < 250:
                band = "under 250 km, so bus/car is practical"
            elif distance_km <= 700:
                band = "250-700 km, so train/bus is practical"
            else:
                band = "over 700 km, so flight/train is practical"
            return f"Auto selected {mode} for an estimated {distance_km:.0f} km trip; {band}. Distance source: {source}."
        return f"User selected {mode}; cost and duration are estimated for about {distance_km:.0f} km. Distance source: {source}."
