from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlmodel import SQLModel, Session, select

from app.db.database import engine
from app.db.models import VerifiedPlaceCache
from app.utils.destination_normalizer import destination_slug, display_destination_name


class VerifiedPlacesCache:
    """Small DB-backed cache for AI candidates that were verified near a destination."""

    def __init__(self) -> None:
        self._table_ready = False

    def get_verified_places(
        self,
        destination: str,
        preference: str | None = None,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        self._ensure_table()
        slug = destination_slug(destination)
        with Session(engine) as session:
            statement = (
                select(VerifiedPlaceCache)
                .where(VerifiedPlaceCache.destination_slug == slug)
                .where(VerifiedPlaceCache.verified == True)  # noqa: E712
                .limit(limit * 2)
            )
            rows = list(session.exec(statement))

        if preference:
            matching = [row for row in rows if row.category == preference]
            rows = matching or rows

        return [self._row_to_place(row) for row in rows[:limit]]

    def save_verified_places(self, destination: str, places: list[dict[str, Any]]) -> None:
        verified_places = [place for place in places if place.get("verified") is True]
        if not verified_places:
            return

        self._ensure_table()
        slug = destination_slug(destination)
        with Session(engine) as session:
            existing_names = {
                row.name.strip().lower()
                for row in session.exec(
                    select(VerifiedPlaceCache).where(VerifiedPlaceCache.destination_slug == slug)
                )
            }
            for place in verified_places:
                name = str(place.get("name", "")).strip()
                if not name or name.lower() in existing_names:
                    continue
                session.add(
                    VerifiedPlaceCache(
                        destination_slug=slug,
                        name=name,
                        category=place.get("category") or "tourist_attraction",
                        description=place.get("description") or "",
                        latitude=place.get("latitude"),
                        longitude=place.get("longitude"),
                        image_url=place.get("image_url"),
                        source=place.get("source") or "verified_ai",
                        verification_source=place.get("verification_source") or "google_maps",
                        verified=True,
                    )
                )
            session.commit()

    def get_image_url(self, destination: str, place_name: str) -> str | None:
        self._ensure_table()
        slug = destination_slug(destination)
        with Session(engine) as session:
            row = session.exec(
                select(VerifiedPlaceCache)
                .where(VerifiedPlaceCache.destination_slug == slug)
                .where(VerifiedPlaceCache.name == place_name)
            ).first()
        return row.image_url if row and row.image_url else None

    def cache_image_url(
        self,
        destination: str,
        place: dict[str, Any],
        image_url: str,
        source: str = "image_lookup",
    ) -> None:
        if not image_url:
            return

        self._ensure_table()
        slug = destination_slug(destination)
        name = str(place.get("name", "")).strip()
        if not name:
            return

        with Session(engine) as session:
            row = session.exec(
                select(VerifiedPlaceCache)
                .where(VerifiedPlaceCache.destination_slug == slug)
                .where(VerifiedPlaceCache.name == name)
            ).first()
            if row:
                row.image_url = image_url
            else:
                session.add(
                    VerifiedPlaceCache(
                        destination_slug=slug,
                        name=name,
                        category=place.get("category") or "tourist_attraction",
                        description=place.get("description") or "",
                        latitude=place.get("latitude"),
                        longitude=place.get("longitude"),
                        image_url=image_url,
                        source=place.get("source") or source,
                        verification_source=place.get("verification_source") or source,
                        verified=place.get("verified") is not False,
                    )
                )
            session.commit()

    def _ensure_table(self) -> None:
        if not self._table_ready:
            SQLModel.metadata.create_all(engine)
            self._ensure_image_url_column()
            self._table_ready = True

    @staticmethod
    def _ensure_image_url_column() -> None:
        with engine.begin() as connection:
            columns = connection.execute(text("PRAGMA table_info(verified_place_cache)")).fetchall()
            column_names = {row[1] for row in columns}
            if "image_url" not in column_names:
                connection.execute(text("ALTER TABLE verified_place_cache ADD COLUMN image_url TEXT NULL"))

    @staticmethod
    def _row_to_place(row: VerifiedPlaceCache) -> dict[str, Any]:
        return {
            "name": row.name,
            "category": row.category,
            "address": display_destination_name(row.destination_slug.replace("_", " ")),
            "description": row.description,
            "estimated_visit_hours": 2.0,
            "rating": None,
            "review_count": None,
            "latitude": row.latitude,
            "longitude": row.longitude,
            "image_url": row.image_url,
            "source": "verified_cache",
            "verification_source": row.verification_source,
            "verified": row.verified,
        }
