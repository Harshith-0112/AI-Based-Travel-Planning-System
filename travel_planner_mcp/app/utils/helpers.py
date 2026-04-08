from __future__ import annotations

import math
from datetime import date, timedelta


def geodesic_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(radius * c, 2)


def estimate_drive_minutes(distance_km: float) -> float:
    average_city_speed_kmph = 24.0
    return round((distance_km / average_city_speed_kmph) * 60, 1)


def daterange(start_date: date | None, total_days: int) -> list[date | None]:
    if not start_date:
        return [None for _ in range(total_days)]
    return [start_date + timedelta(days=offset) for offset in range(total_days)]
