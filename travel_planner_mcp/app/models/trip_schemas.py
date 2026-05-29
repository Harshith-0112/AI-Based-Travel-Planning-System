from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TripCreate(BaseModel):
    destination: str
    request_json: dict[str, Any] = Field(default_factory=dict)
    response_json: dict[str, Any] = Field(default_factory=dict)
    selected_hotel_json: dict[str, Any] | None = None
    budget_breakdown_json: dict[str, Any] | None = None


class TripRead(BaseModel):
    id: int
    user_id: int
    destination: str
    request_json: dict[str, Any]
    response_json: dict[str, Any]
    selected_hotel_json: dict[str, Any]
    budget_breakdown_json: dict[str, Any]
    is_favorite: bool
    created_at: datetime
    updated_at: datetime
