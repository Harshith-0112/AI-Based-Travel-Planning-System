from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.auth.dependencies import get_current_user
from app.db.database import get_session
from app.db.models import Trip, User
from app.models.trip_schemas import TripCreate, TripRead


router = APIRouter(prefix="/trips", tags=["trips"])


def _to_json_text(value: dict[str, Any] | None) -> str:
    return json.dumps(value or {}, default=str)


def _from_json_text(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _trip_to_read(trip: Trip) -> TripRead:
    return TripRead(
        id=trip.id,
        user_id=trip.user_id,
        destination=trip.destination,
        request_json=_from_json_text(trip.request_json),
        response_json=_from_json_text(trip.response_json),
        selected_hotel_json=_from_json_text(trip.selected_hotel_json),
        budget_breakdown_json=_from_json_text(trip.budget_breakdown_json),
        is_favorite=trip.is_favorite,
        created_at=trip.created_at,
        updated_at=trip.updated_at,
    )


def _get_user_trip(trip_id: int, current_user: User, session: Session) -> Trip:
    trip = session.exec(
        select(Trip)
        .where(Trip.id == trip_id)
        .where(Trip.user_id == current_user.id)
    ).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


@router.post("", response_model=TripRead)
def save_trip(
    trip: TripCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    db_trip = Trip(
        user_id=current_user.id,
        destination=trip.destination,
        request_json=_to_json_text(trip.request_json),
        response_json=_to_json_text(trip.response_json),
        selected_hotel_json=_to_json_text(trip.selected_hotel_json),
        budget_breakdown_json=_to_json_text(trip.budget_breakdown_json),
    )
    session.add(db_trip)
    session.commit()
    session.refresh(db_trip)
    return _trip_to_read(db_trip)


@router.get("/recent", response_model=list[TripRead])
def recent_trips(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    trips = session.exec(
        select(Trip)
        .where(Trip.user_id == current_user.id)
        .order_by(Trip.created_at.desc())
        .limit(20)
    ).all()
    return [_trip_to_read(trip) for trip in trips]


@router.get("/favourites", response_model=list[TripRead])
def favourite_trips(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    trips = session.exec(
        select(Trip)
        .where(Trip.user_id == current_user.id)
        .where(Trip.is_favorite == True)  # noqa: E712
        .order_by(Trip.updated_at.desc())
    ).all()
    return [_trip_to_read(trip) for trip in trips]


@router.get("/{trip_id}", response_model=TripRead)
def get_trip(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return _trip_to_read(_get_user_trip(trip_id, current_user, session))


@router.post("/{trip_id}/favorite", response_model=TripRead)
def favorite_trip(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    trip = _get_user_trip(trip_id, current_user, session)
    trip.is_favorite = True
    trip.updated_at = datetime.now(timezone.utc)
    session.add(trip)
    session.commit()
    session.refresh(trip)
    return _trip_to_read(trip)


@router.post("/{trip_id}/unfavorite", response_model=TripRead)
def unfavorite_trip(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    trip = _get_user_trip(trip_id, current_user, session)
    trip.is_favorite = False
    trip.updated_at = datetime.now(timezone.utc)
    session.add(trip)
    session.commit()
    session.refresh(trip)
    return _trip_to_read(trip)


@router.delete("/{trip_id}")
def delete_trip(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    trip = _get_user_trip(trip_id, current_user, session)
    session.delete(trip)
    session.commit()
    return {"message": "Trip deleted successfully"}
