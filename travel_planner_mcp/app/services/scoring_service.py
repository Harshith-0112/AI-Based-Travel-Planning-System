from __future__ import annotations

from app.models.schemas import Attraction, HotelOption


def score_hotel(
    hotel: HotelOption,
    budget_per_night: float,
    preference_bonus: float = 0.5,
) -> tuple[float, str]:
    """Transparent weighted hotel score for viva-friendly explanation.

    affordability_score rewards hotels below the user's per-night budget.
    distance_score rewards hotels closer to the city center or attraction hub.
    rating_score captures guest satisfaction.
    preference_score is a light bonus when amenities roughly match travel style.
    """

    affordability_score = max(0.0, min(1.0, 1 - (hotel.nightly_price / max(budget_per_night, 1))))
    distance_value = hotel.distance_to_center_km if hotel.distance_to_center_km is not None else 4.0
    distance_score = max(0.0, min(1.0, 1 - (distance_value / 10)))
    rating_score = max(0.0, min(1.0, (hotel.rating or 3.5) / 5))
    preference_score = max(0.0, min(1.0, preference_bonus))

    score = round(
        0.40 * affordability_score
        + 0.30 * distance_score
        + 0.20 * rating_score
        + 0.10 * preference_score,
        4,
    )
    reason = (
        f"affordability={affordability_score:.2f}, distance={distance_score:.2f}, "
        f"rating={rating_score:.2f}, preference={preference_score:.2f}"
    )
    return score, reason


def score_attraction(attraction: Attraction, preference_match: float, route_feasibility: float) -> float:
    popularity = (attraction.rating or 3.8) / 5
    score = 0.45 * preference_match + 0.30 * popularity + 0.15 * route_feasibility + 0.10 * 0.8
    return round(score, 4)
