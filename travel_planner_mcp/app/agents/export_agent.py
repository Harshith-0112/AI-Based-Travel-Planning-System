from __future__ import annotations

from app.models.schemas import TripPlanResponse
from app.services.export_service import plan_to_ics, plan_to_json


class ExportAgent:
    def export_json(self, plan: TripPlanResponse) -> str:
        return plan_to_json(plan)

    def export_ics(self, plan: TripPlanResponse) -> str:
        return plan_to_ics(plan)
