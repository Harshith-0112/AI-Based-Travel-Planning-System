from __future__ import annotations

from app.models.schemas import Attraction, HotelOption, TripRequest


HOTEL_BUDGET_SHARE = {
    "budget": 0.30,
    "standard": 0.45,
    "luxury": 0.60,
}


def allocated_hotel_budget(request: TripRequest) -> float:
    return round(request.budget * HOTEL_BUDGET_SHARE[request.hotel_preference], 2)


def hotel_stay_price(hotel: HotelOption, days: int) -> float | None:
    if hotel.total_price is not None and hotel.total_price > 0:
        return hotel.total_price
    if hotel.nightly_price is not None and hotel.nightly_price > 0:
        return hotel.nightly_price * max(days, 1)
    return None


def format_currency(value: float | None) -> str:
    if value is None:
        return "not available"
    return f"₹{value:,.0f}"


def build_user_facing_hotel_reason(hotel: HotelOption | None, request: TripRequest) -> str:
    if not hotel:
        return "No hotel could be selected, so the itinerary continues without a lodging recommendation."

    stay_price = hotel_stay_price(hotel, request.days)
    lodging_budget = allocated_hotel_budget(request)
    nightly = hotel.nightly_price if hotel.nightly_price and hotel.nightly_price > 0 else None
    rating_text = f"a strong {hotel.rating:.1f} rating" if hotel.rating else "limited rating information"
    preference = request.hotel_preference

    if stay_price is None:
        fit_text = "The hotel price is not available, so the lodging cost is treated as an estimate."
    elif stay_price <= lodging_budget:
        fit_text = "The total stay cost fits within your lodging allocation."
    elif stay_price <= lodging_budget * 1.15:
        fit_text = "The total stay cost is slightly above your lodging allocation but still close."
    else:
        fit_text = "The total stay cost is above your lodging allocation."

    return (
        f"This hotel matches your {preference} preference, has {rating_text}, "
        f"a nightly price of {format_currency(nightly)}, and a total stay cost of "
        f"{format_currency(stay_price)}. {fit_text}"
    )


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _review_score(review_count: int | None) -> float:
    if not review_count:
        return 0.45
    return _clamp(review_count / 1000)


def score_hotel(
    hotel: HotelOption,
    request: TripRequest,
    preference_bonus: float = 0.5,
) -> tuple[float, str]:
    """Transparent, budget-aware hotel score for viva-friendly explanation."""

    allocated_budget = allocated_hotel_budget(request)
    stay_price = hotel_stay_price(hotel, request.days)
    target = max(allocated_budget, 1.0)

    if stay_price is None:
        affordability_score = 0.45
        fit_score = 0.30
        utilization_score = 0.25
        price_label = "unknown"
    else:
        affordability_score = (
            1.0 if stay_price <= target else _clamp(1 - ((stay_price - target) / target))
        )
        fit_score = _clamp(1 - (abs(stay_price - target) / target))
        utilization_score = _clamp(stay_price / target)
        price_label = f"{stay_price:.0f}"

    distance_value = hotel.distance_to_center_km if hotel.distance_to_center_km is not None else 4.0
    distance_score = _clamp(1 - (distance_value / 10))
    rating_score = _clamp((hotel.rating or 3.5) / 5)
    preference_score = _clamp(preference_bonus)
    review_score = _review_score(hotel.review_count)

    if request.hotel_preference == "luxury":
        score = (
            0.40 * rating_score
            + 0.30 * fit_score
            + 0.15 * utilization_score
            + 0.05 * distance_score
            + 0.05 * preference_score
            + 0.05 * review_score
        )
    elif request.hotel_preference == "budget":
        score = (
            0.42 * affordability_score
            + 0.28 * rating_score
            + 0.15 * distance_score
            + 0.10 * preference_score
            + 0.05 * review_score
        )
        if hotel.rating is not None and hotel.rating < 3.5:
            score -= 0.15
    else:
        score = (
            0.35 * fit_score
            + 0.30 * rating_score
            + 0.15 * affordability_score
            + 0.10 * distance_score
            + 0.05 * preference_score
            + 0.05 * review_score
        )

    score = round(_clamp(score), 4)
    reason = (
        f"{request.hotel_preference} preference; allocated lodging budget={allocated_budget:.0f}; "
        f"hotel stay price={price_label}; affordability={affordability_score:.2f}; "
        f"budget_fit={fit_score:.2f}; rating={rating_score:.2f}; distance={distance_score:.2f}"
    )
    return score, reason


def score_attraction(attraction: Attraction, preference_match: float, route_feasibility: float) -> float:
    popularity = (attraction.rating or 3.8) / 5
    score = 0.45 * preference_match + 0.30 * popularity + 0.15 * route_feasibility + 0.10 * 0.8
    return round(score, 4)
