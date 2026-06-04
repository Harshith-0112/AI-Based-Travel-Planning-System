from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from app.db.database import create_db_and_tables
from app.models.schemas import TripPlanResponse, TripRequest
from app.services.planning_service import PlanningService
from app.utils.config import get_settings

from app.api.routes import auth
from app.api.routes.auth import router as auth_router

from app.api.routes.itineraries import router as itinerary_router
from app.api.routes.trips import router as trips_router

from app.auth.dependencies import get_current_user
from app.db.models import User


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="AI-Based Travel Planning System Using Multi-Agent Architecture and MCP Integration",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings = get_settings()
planning_service = PlanningService(settings)
app.include_router(auth.router)
app.include_router(auth_router)
app.include_router(itinerary_router)
app.include_router(trips_router)


@app.get("/health")
async def health() -> dict:
    provider_status = await planning_service.get_provider_status()
    return {"status": "ok", "providers": provider_status.model_dump()}


@app.get("/config-status")
async def config_status() -> dict:
    return (await planning_service.get_provider_status()).model_dump()


@app.post("/plan-trip", response_model=TripPlanResponse)
async def plan_trip(
    request: TripRequest,
    current_user: User = Depends(get_current_user),
) -> TripPlanResponse:
    return await planning_service.plan_trip(request)


@app.post("/export/json")
async def export_json(
    plan: TripPlanResponse,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    return JSONResponse(content=plan.model_dump())


@app.post("/export/ics")
async def export_ics(
    plan: TripPlanResponse,
    current_user: User = Depends(get_current_user),
) -> PlainTextResponse:
    ics_text = planning_service.export_agent.export_ics(plan)
    return PlainTextResponse(content=ics_text, media_type="text/calendar")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
