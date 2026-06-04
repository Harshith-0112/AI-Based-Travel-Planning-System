from __future__ import annotations

from datetime import date as dt_date
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


SUPPORTED_PREFERENCES = [
    "nature",
    "food",
    "shopping",
    "adventure",
    "history",
    "temples",
    "beaches",
    "nightlife",
    "family",
    "relaxation",
]


class TripRequest(BaseModel):
    destination: str = Field(..., min_length=2)
    budget: float = Field(..., gt=0)
    days: int = Field(..., ge=1, le=14)
    preferences: list[str] = Field(default_factory=list)
    start_date: dt_date | None = None
    travelers: int = Field(default=1, ge=1, le=10)
    starting_location: str | None = None
    hotel_preference: Literal["budget", "standard", "luxury"] = "standard"
    transport_mode: Literal["auto", "flight", "train", "bus", "car"] = "auto"

    @field_validator("destination")
    @classmethod
    def normalize_destination(cls, value: str) -> str:
        return value.strip()

    @field_validator("preferences")
    @classmethod
    def normalize_preferences(cls, value: list[str]) -> list[str]:
        cleaned = []
        for item in value:
            normalized = item.strip().lower()
            if normalized and normalized not in cleaned:
                cleaned.append(normalized)
        return cleaned or ["relaxation"]

    @field_validator("hotel_preference", "transport_mode", mode="before")
    @classmethod
    def normalize_choice_fields(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip().lower()
        return value


class HotelOption(BaseModel):
    name: str
    address: str
    nightly_price: float | None = None
    total_price: float | None = None
    rating: float | None = None
    review_count: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    booking_link: HttpUrl | None = None
    source: str
    amenities: list[str] = Field(default_factory=list)
    distance_to_center_km: float | None = None
    ranking_score: float | None = None
    ranking_reason: str | None = None

    @field_validator("nightly_price", "total_price", mode="before")
    @classmethod
    def zero_price_is_unknown(cls, value: float | int | str | None) -> float | None:
        if value is None or value == "":
            return None
        try:
            price = float(value)
        except (TypeError, ValueError):
            return None
        return price if price > 0 else None


class Attraction(BaseModel):
    name: str
    category: str
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    rating: float | None = None
    review_count: int | None = None
    estimated_visit_hours: float = 2.0
    source: str = "maps"
    verification_source: str | None = None
    verified: bool | None = None
    place_id: str | None = None
    description: str | None = None
    image_url: str | None = None
    tags: list[str] = Field(default_factory=list)
    best_time: str | None = None
    estimated_cost: float | None = None
    relevance_score: float | None = None


class RouteLeg(BaseModel):
    origin_name: str
    destination_name: str
    travel_mode: Literal["DRIVE", "WALK", "TRANSIT"] = "DRIVE"
    distance_km: float
    duration_minutes: float
    provider: str


class DailyActivity(BaseModel):
    time_slot: Literal["morning", "afternoon", "evening"]
    title: str
    description: str | None = None
    highlights: list[str] = Field(default_factory=list)
    visit_tips: list[str] = Field(default_factory=list)
    image_url: str | None = None
    tags: list[str] = Field(default_factory=list)
    best_time: str | None = None
    place_name: str | None = None
    estimated_cost: float = 0.0
    cost_source: Literal["estimated", "provider"] = "estimated"
    travel_time_from_previous_minutes: float | None = None
    buffer_note: str | None = None


class DailyPlan(BaseModel):
    day_number: int
    date: dt_date | None = None
    theme: str
    activities: list[DailyActivity]
    route_legs: list[RouteLeg] = Field(default_factory=list)
    estimated_cost: float = 0.0
    warnings: list[str] = Field(default_factory=list)


class TransportOption(BaseModel):
    mode: Literal["flight", "train", "bus", "car"]
    estimated_cost: float
    estimated_duration_hours: float
    reason: str
    source: str


class BudgetBreakdown(BaseModel):
    lodging_cost: float
    transport_cost: float
    food_cost: float
    misc_cost: float
    total_estimated_cost: float
    budget: float
    within_budget: bool
    over_budget_amount: float = 0.0
    budget_warning: str | None = None
    budget_status: Literal["within_budget", "over_budget", "preference_exceeds_budget"] = "within_budget"


class ProviderStatus(BaseModel):
    ollama_reachable: bool
    google_maps_api_key_set: bool
    serpapi_api_key_set: bool
    active_hotel_provider: str
    active_maps_provider: str
    notes: list[str] = Field(default_factory=list)


class MCPToolInfo(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]


class TripPlanResponse(BaseModel):
    trip_request: TripRequest
    provider_status: ProviderStatus
    hotel: HotelOption | None = None
    alternative_hotels: list[HotelOption] = Field(default_factory=list)
    transport: TransportOption | None = None
    attractions: list[Attraction] = Field(default_factory=list)
    daily_plans: list[DailyPlan] = Field(default_factory=list)
    budget_breakdown: BudgetBreakdown
    summary: str
    hotel_selection_reason: str
    notes: list[str] = Field(default_factory=list)
    generated_at: str
