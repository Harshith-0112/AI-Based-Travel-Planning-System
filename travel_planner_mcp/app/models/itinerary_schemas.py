from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SavedItineraryCreate(BaseModel):
    title: str
    destination: str
    days: int
    budget: float
    travelers: int
    preferences: str
    itinerary_json: str


class SavedItineraryRead(BaseModel):
    id: int
    user_id: int
    title: str
    destination: str
    days: int
    budget: float
    travelers: int
    preferences: str
    itinerary_json: str
    created_at: datetime
    updated_at: datetime


class SavedItineraryListItem(BaseModel):
    id: int
    title: str
    destination: str
    days: int
    budget: float
    created_at: datetime