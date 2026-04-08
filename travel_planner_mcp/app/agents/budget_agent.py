from __future__ import annotations

from app.models.schemas import BudgetBreakdown, DailyPlan, HotelOption, TripRequest


class BudgetAgent:
    def estimate(
        self,
        request: TripRequest,
        hotel: HotelOption | None,
        daily_plans: list[DailyPlan],
    ) -> BudgetBreakdown:
        lodging_cost = hotel.nightly_price * request.days if hotel else 0.0
        transport_cost = sum(sum(leg.duration_minutes for leg in plan.route_legs) * 1.5 for plan in daily_plans)
        food_cost = 700.0 * request.travelers * request.days
        misc_cost = 400.0 * request.days
        total = round(lodging_cost + transport_cost + food_cost + misc_cost, 2)
        within_budget = total <= request.budget
        return BudgetBreakdown(
            lodging_cost=round(lodging_cost, 2),
            transport_cost=round(transport_cost, 2),
            food_cost=round(food_cost, 2),
            misc_cost=round(misc_cost, 2),
            total_estimated_cost=total,
            budget=request.budget,
            within_budget=within_budget,
            over_budget_amount=round(max(total - request.budget, 0), 2),
        )
