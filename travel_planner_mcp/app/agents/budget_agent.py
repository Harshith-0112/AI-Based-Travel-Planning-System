from __future__ import annotations

from app.models.schemas import BudgetBreakdown, DailyPlan, HotelOption, TransportOption, TripRequest
from app.services.scoring_service import allocated_hotel_budget


def selected_hotel_lodging_cost(
    hotel: HotelOption | None,
    days: int,
    fallback_cost: float | None = None,
) -> float | None:
    if not hotel:
        return fallback_cost
    if hotel.total_price is not None and hotel.total_price > 0:
        return round(hotel.total_price, 2)
    if hotel.nightly_price is not None and hotel.nightly_price > 0:
        nights = max(days - 1, 1)
        return round(hotel.nightly_price * nights, 2)
    return fallback_cost


def recalculate_budget_for_selected_hotel(
    budget: BudgetBreakdown,
    selected_hotel: HotelOption | None,
    days: int,
) -> BudgetBreakdown:
    lodging_cost = selected_hotel_lodging_cost(
        selected_hotel,
        days,
        fallback_cost=budget.lodging_cost,
    )
    lodging_cost = lodging_cost if lodging_cost is not None else budget.lodging_cost
    total = round(
        lodging_cost + budget.transport_cost + budget.food_cost + budget.misc_cost,
        2,
    )
    return BudgetBreakdown(
        lodging_cost=round(lodging_cost, 2),
        transport_cost=budget.transport_cost,
        food_cost=budget.food_cost,
        misc_cost=budget.misc_cost,
        total_estimated_cost=total,
        budget=budget.budget,
        within_budget=total <= budget.budget,
        over_budget_amount=round(max(total - budget.budget, 0), 2),
        budget_warning=budget.budget_warning,
        budget_status="within_budget" if total <= budget.budget else "over_budget",
    )


def _build_budget(
    lodging_cost: float,
    transport_cost: float,
    food_cost: float,
    misc_cost: float,
    budget: float,
    warning: str | None = None,
    preference_exceeds_budget: bool = False,
) -> BudgetBreakdown:
    total = round(lodging_cost + transport_cost + food_cost + misc_cost, 2)
    within_budget = total <= budget
    status = "within_budget" if within_budget else "over_budget"
    if preference_exceeds_budget and not within_budget:
        status = "preference_exceeds_budget"
    return BudgetBreakdown(
        lodging_cost=round(lodging_cost, 2),
        transport_cost=round(transport_cost, 2),
        food_cost=round(food_cost, 2),
        misc_cost=round(misc_cost, 2),
        total_estimated_cost=total,
        budget=budget,
        within_budget=within_budget,
        over_budget_amount=round(max(total - budget, 0), 2),
        budget_warning=warning,
        budget_status=status,
    )


def rebalance_budget_to_fit(
    request: TripRequest,
    budget: BudgetBreakdown,
    selected_hotel: HotelOption | None,
    hotel_options: list[HotelOption],
    transport: TransportOption | None = None,
    cheaper_transport_options: list[TransportOption] | None = None,
) -> tuple[HotelOption | None, TransportOption | None, BudgetBreakdown, list[HotelOption]]:
    current_hotel = selected_hotel
    current_transport = transport
    current_budget = budget
    warnings: list[str] = []

    if current_budget.within_budget:
        return current_hotel, current_transport, current_budget, hotel_options

    fixed_cost_without_lodging = (
        current_budget.transport_cost + current_budget.food_cost + current_budget.misc_cost
    )
    affordable_hotels = [
        hotel
        for hotel in hotel_options
        if (selected_hotel_lodging_cost(hotel, request.days) or float("inf"))
        + fixed_cost_without_lodging
        <= request.budget
    ]
    if affordable_hotels:
        affordable_hotels.sort(key=lambda item: item.ranking_score or 0, reverse=True)
        current_hotel = affordable_hotels[0]
        lodging_cost = selected_hotel_lodging_cost(
            current_hotel,
            request.days,
            fallback_cost=current_budget.lodging_cost,
        )
        current_budget = _build_budget(
            lodging_cost or current_budget.lodging_cost,
            current_budget.transport_cost,
            current_budget.food_cost,
            current_budget.misc_cost,
            request.budget,
            warning="Adjusted recommendations to stay within your budget.",
        )
        if request.hotel_preference == "luxury" and current_hotel != selected_hotel:
            current_budget.budget_warning = (
                "Luxury hotels may exceed this budget. Showing the best available option within your budget."
            )
        if current_budget.within_budget:
            return current_hotel, current_transport, current_budget, hotel_options

    if request.transport_mode == "auto" and cheaper_transport_options:
        for option in sorted(cheaper_transport_options, key=lambda item: item.estimated_cost):
            local_transport = max(current_budget.transport_cost - (current_transport.estimated_cost if current_transport else 0), 0)
            candidate_transport_cost = local_transport + option.estimated_cost
            candidate_budget = _build_budget(
                current_budget.lodging_cost,
                candidate_transport_cost,
                current_budget.food_cost,
                current_budget.misc_cost,
                request.budget,
                warning="Adjusted recommendations to stay within your budget.",
            )
            if candidate_budget.total_estimated_cost < current_budget.total_estimated_cost:
                current_transport = option
                current_budget = candidate_budget
            if current_budget.within_budget:
                return current_hotel, current_transport, current_budget, hotel_options

    min_misc = {"budget": 150.0, "standard": 250.0, "luxury": 400.0}[request.hotel_preference] * request.days
    if current_budget.misc_cost > min_misc:
        new_misc = max(
            min_misc,
            current_budget.misc_cost - current_budget.over_budget_amount,
        )
        current_budget = _build_budget(
            current_budget.lodging_cost,
            current_budget.transport_cost,
            current_budget.food_cost,
            new_misc,
            request.budget,
            warning="Adjusted recommendations to stay within your budget.",
        )
        if current_budget.within_budget:
            return current_hotel, current_transport, current_budget, hotel_options

    min_food = {"budget": 350.0, "standard": 500.0, "luxury": 750.0}[request.hotel_preference] * request.travelers * request.days
    if current_budget.food_cost > min_food:
        new_food = max(
            min_food,
            current_budget.food_cost - current_budget.over_budget_amount,
        )
        current_budget = _build_budget(
            current_budget.lodging_cost,
            current_budget.transport_cost,
            new_food,
            current_budget.misc_cost,
            request.budget,
            warning="Adjusted recommendations to stay within your budget.",
        )
        if current_budget.within_budget:
            return current_hotel, current_transport, current_budget, hotel_options

    warnings.append(f"This plan exceeds your budget by ₹{current_budget.over_budget_amount:,.0f}.")
    warning = " ".join(warnings)
    if request.hotel_preference == "luxury":
        warning = (
            "Luxury hotels may exceed this budget. Showing the best available option, "
            f"but this plan exceeds your budget by ₹{current_budget.over_budget_amount:,.0f}."
        )
    current_budget.budget_warning = warning
    current_budget.budget_status = "preference_exceeds_budget"
    return current_hotel, current_transport, current_budget, hotel_options


class BudgetAgent:
    def estimate(
        self,
        request: TripRequest,
        hotel: HotelOption | None,
        daily_plans: list[DailyPlan],
        transport: TransportOption | None = None,
    ) -> BudgetBreakdown:
        known_lodging_cost = selected_hotel_lodging_cost(hotel, request.days) if hotel else None
        if known_lodging_cost is not None:
            lodging_cost = known_lodging_cost
        elif hotel:
            lodging_cost = allocated_hotel_budget(request)
        else:
            lodging_cost = 0.0

        local_transport_cost = sum(
            sum(leg.duration_minutes for leg in plan.route_legs) * 1.5
            for plan in daily_plans
        )
        intercity_transport_cost = transport.estimated_cost if transport else 0.0
        transport_cost = local_transport_cost + intercity_transport_cost

        food_rates = {"budget": 600.0, "standard": 900.0, "luxury": 1400.0}
        misc_rates = {"budget": 300.0, "standard": 500.0, "luxury": 800.0}
        food_cost = food_rates[request.hotel_preference] * request.travelers * request.days
        misc_cost = misc_rates[request.hotel_preference] * request.days

        if request.hotel_preference in {"standard", "luxury"}:
            target_ratio = 0.86 if request.hotel_preference == "standard" else 0.92
            target_total = request.budget * target_ratio
            current_total = lodging_cost + transport_cost + food_cost + misc_cost
            if current_total < target_total:
                extra = target_total - current_total
                food_cost += extra * 0.55
                misc_cost += extra * 0.45

        return _build_budget(
            lodging_cost,
            transport_cost,
            food_cost,
            misc_cost,
            request.budget,
        )
