from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.auth.dependencies import get_current_user
from app.db.database import get_session
from app.db.models import SavedItinerary, User
from app.models.itinerary_schemas import (
    SavedItineraryCreate,
    SavedItineraryListItem,
    SavedItineraryRead,
)

router = APIRouter(prefix="/itineraries", tags=["itineraries"])


@router.post("/", response_model=SavedItineraryRead)
def save_itinerary(
    itinerary: SavedItineraryCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    db_itinerary = SavedItinerary(
        user_id=current_user.id,
        title=itinerary.title,
        destination=itinerary.destination,
        days=itinerary.days,
        budget=itinerary.budget,
        travelers=itinerary.travelers,
        preferences=itinerary.preferences,
        itinerary_json=itinerary.itinerary_json,
    )

    session.add(db_itinerary)
    session.commit()
    session.refresh(db_itinerary)

    return db_itinerary


@router.get("/", response_model=list[SavedItineraryListItem])
def list_my_itineraries(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    itineraries = session.exec(
        select(SavedItinerary).where(SavedItinerary.user_id == current_user.id)
    ).all()

    return itineraries


@router.get("/{itinerary_id}", response_model=SavedItineraryRead)
def get_itinerary(
    itinerary_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    itinerary = session.exec(
        select(SavedItinerary)
        .where(SavedItinerary.id == itinerary_id)
        .where(SavedItinerary.user_id == current_user.id)
    ).first()

    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")

    return itinerary


@router.delete("/{itinerary_id}")
def delete_itinerary(
    itinerary_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    itinerary = session.exec(
        select(SavedItinerary)
        .where(SavedItinerary.id == itinerary_id)
        .where(SavedItinerary.user_id == current_user.id)
    ).first()

    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")

    session.delete(itinerary)
    session.commit()

    return {"message": "Itinerary deleted successfully"}
