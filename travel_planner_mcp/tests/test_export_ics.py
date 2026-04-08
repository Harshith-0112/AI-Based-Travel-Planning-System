from datetime import date

from app.models.schemas import BudgetBreakdown, DailyActivity, DailyPlan, ProviderStatus, TripPlanResponse, TripRequest
from app.services.export_service import plan_to_ics


def test_ics_generation() -> None:
    plan = TripPlanResponse(
        trip_request=TripRequest(destination="Mysore", budget=10000, days=2, preferences=["history"], start_date=date(2026, 4, 10), travelers=2),
        provider_status=ProviderStatus(
            ollama_reachable=False,
            google_maps_api_key_set=False,
            serpapi_api_key_set=False,
            active_hotel_provider="mock",
            active_maps_provider="mock",
        ),
        hotel=None,
        alternative_hotels=[],
        attractions=[],
        daily_plans=[
            DailyPlan(
                day_number=1,
                date=date(2026, 4, 10),
                theme="History Focus",
                activities=[
                    DailyActivity(time_slot="morning", title="Palace Visit", description="Explore palace", place_name="Mysore Palace")
                ],
                estimated_cost=1000,
            )
        ],
        budget_breakdown=BudgetBreakdown(
            lodging_cost=0,
            transport_cost=100,
            food_cost=1000,
            misc_cost=200,
            total_estimated_cost=1300,
            budget=10000,
            within_budget=True,
        ),
        summary="Sample summary",
        hotel_selection_reason="Sample hotel reason",
        notes=[],
        generated_at="2026-04-05T00:00:00",
    )
    ics_text = plan_to_ics(plan)
    assert "BEGIN:VCALENDAR" in ics_text
    assert "SUMMARY:Day 1 - History Focus" in ics_text
    assert "Mysore Palace" in ics_text
