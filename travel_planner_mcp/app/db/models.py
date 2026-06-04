from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import SQLModel, Field


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    full_name: str
    email: str = Field(index=True, unique=True)
    hashed_password: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SavedItinerary(SQLModel, table=True):
    __tablename__ = "saved_itineraries"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")

    title: str
    destination: str
    days: int
    budget: float
    travelers: int
    preferences: str

    itinerary_json: str

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Trip(SQLModel, table=True):
    __tablename__ = "trips"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    destination: str = Field(index=True)
    request_json: str
    response_json: str
    selected_hotel_json: str = "{}"
    budget_breakdown_json: str = "{}"
    is_favorite: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class VerifiedPlaceCache(SQLModel, table=True):
    __tablename__ = "verified_place_cache"

    id: Optional[int] = Field(default=None, primary_key=True)
    destination_slug: str = Field(index=True)
    name: str
    category: str = "tourist_attraction"
    description: str = ""
    latitude: float | None = None
    longitude: float | None = None
    image_url: str | None = None
    source: str = "verified_ai"
    verification_source: str = "google_maps"
    verified: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
