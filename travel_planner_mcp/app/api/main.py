from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse

from app.models.schemas import TripPlanResponse, TripRequest
from app.services.planning_service import PlanningService
from app.utils.config import get_settings


settings = get_settings()
planning_service = PlanningService(settings)
app = FastAPI(title="AI-Based Travel Planning System Using Multi-Agent Architecture and MCP Integration")


@app.get("/health")
async def health() -> dict:
    provider_status = await planning_service.get_provider_status()
    return {"status": "ok", "providers": provider_status.model_dump()}


@app.get("/config-status")
async def config_status() -> dict:
    return (await planning_service.get_provider_status()).model_dump()


@app.post("/plan-trip", response_model=TripPlanResponse)
async def plan_trip(request: TripRequest) -> TripPlanResponse:
    return await planning_service.plan_trip(request)


@app.post("/export/json")
async def export_json(plan: TripPlanResponse) -> JSONResponse:
    return JSONResponse(content=plan.model_dump())


@app.post("/export/ics")
async def export_ics(plan: TripPlanResponse) -> PlainTextResponse:
    ics_text = planning_service.export_agent.export_ics(plan)
    return PlainTextResponse(content=ics_text, media_type="text/calendar")
