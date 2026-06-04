from __future__ import annotations

import json
import re
import random
from pathlib import Path
from typing import Any

from app.utils.destination_normalizer import destination_slug, normalize_destination_name


GENERIC_PLACE_NAMES = {
    "central museum",
    "city heritage walk",
    "evening promenade",
    "family activity center",
    "flexible local break",
    "free exploration",
    "local attraction",
    "local break",
    "main local market",
    "nearby cafe",
    "popular temple area",
    "public garden",
    "regional food street",
    "shopping area",
    "unknown place",
}


class FallbackPlacesProvider:
    """Reads curated local places when maps search is unavailable."""

    def __init__(self, data_dir: Path | None = None, data_root: Path | None = None) -> None:
        self.data_root = data_root or Path(__file__).resolve().parents[1] / "data"
        self.data_dir = data_dir or self.data_root / "fallback_places"
        self._dataset_cache: dict[str, dict[str, Any]] = {}

    def get_places(
        self,
        destination: str,
        preference: str | None = None,
        limit: int = 8,
        use_default_if_missing: bool = True,
    ) -> list[dict[str, Any]]:
        path = self._destination_path(destination)
        if not path.exists() and use_default_if_missing:
            path = self._default_path()

        places = self._valid_places(self._read_places(path))
        if preference:
            matching = [place for place in places if place.get("category") == preference]
            places = matching or places

        return [self._normalize_place(place, destination, preference) for place in places[:limit]]

    def get_default_places(self, preference: str | None = None, limit: int = 8) -> list[dict[str, Any]]:
        places = self._valid_places(self._read_places(self._default_path()))
        if preference:
            matching = [place for place in places if place.get("category") == preference]
            places = matching or places
        return [self._normalize_place(place, "India", preference) for place in places[:limit]]

    def get_destination_categories(self, destination: str) -> list[str]:
        destination_data = self._curated_destination_data(destination)
        return sorted(destination_data.keys())

    def get_places_for_preferences(
        self,
        destination: str,
        preferences: list[str],
        days: int = 1,
        budget: float | None = None,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        destination_data = self._curated_destination_data(destination)
        if not destination_data:
            return []

        selected: list[dict[str, Any]] = []
        seen: set[str] = set()
        categories = preferences or list(destination_data)
        for category in categories:
            places = destination_data.get(category, [])
            for place in self._budget_sorted_places(places, budget, days):
                name = place.get("name")
                normalized_name = str(name).strip().lower()
                if normalized_name in seen or not self.is_valid_place_name(name):
                    continue
                seen.add(normalized_name)
                selected.append(self._normalize_curated_place(place, destination, category))
                if len(selected) >= limit:
                    return selected

        if len(selected) < limit:
            for category, places in destination_data.items():
                for place in self._budget_sorted_places(places, budget, days):
                    normalized_name = str(place.get("name", "")).strip().lower()
                    if normalized_name in seen or not self.is_valid_place_name(place.get("name")):
                        continue
                    seen.add(normalized_name)
                    selected.append(self._normalize_curated_place(place, destination, category))
                    if len(selected) >= limit:
                        return selected

        return selected

    def get_randomized_day_plan(
        self,
        destination: str,
        preferences: list[str],
        days: int,
        budget: float | None = None,
    ) -> list[list[dict[str, Any]]]:
        places = self.get_places_for_preferences(
            destination,
            preferences=preferences,
            days=days,
            budget=budget,
            limit=max(days * 3, 3),
        )
        rng = random.Random(destination_slug(destination))
        places = places[:]
        rng.shuffle(places)
        return [places[index * 3 : (index + 1) * 3] for index in range(days)]

    def _destination_path(self, destination: str) -> Path:
        return self.data_dir / f"{destination_slug(destination)}.json"

    def _default_path(self) -> Path:
        return self.data_dir / "default_india.json"

    def _curated_destination_data(self, destination: str) -> dict[str, list[dict[str, Any]]]:
        slug = destination_slug(destination)
        for dataset_name in ("india_places", "international_places"):
            dataset = self._read_dataset(dataset_name)
            destination_data = dataset.get(slug)
            if isinstance(destination_data, dict):
                return {
                    category: [item for item in places if isinstance(item, dict)]
                    for category, places in destination_data.items()
                    if isinstance(places, list)
                }
        return {}

    def _read_dataset(self, dataset_name: str) -> dict[str, Any]:
        if dataset_name not in self._dataset_cache:
            path = self.data_root / f"{dataset_name}.json"
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                data = {}
            self._dataset_cache[dataset_name] = data if isinstance(data, dict) else {}
        return self._dataset_cache[dataset_name]

    @staticmethod
    def _read_places(path: Path) -> list[dict[str, Any]]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(data, list):
            return []
        return [item for item in data if isinstance(item, dict)]

    @classmethod
    def _valid_places(cls, places: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [place for place in places if cls.is_valid_place_name(place.get("name"))]

    @staticmethod
    def is_valid_place_name(name: Any) -> bool:
        if not isinstance(name, str):
            return False

        normalized = re.sub(r"[^a-z0-9]+", " ", name.strip().lower()).strip()
        if not normalized or normalized in GENERIC_PLACE_NAMES:
            return False

        blocked_fragments = [
            "free exploration",
            "flexible local",
            "local break",
            "nearby cafe",
            "nearby attraction",
            "shopping area",
        ]
        if any(fragment in normalized for fragment in blocked_fragments):
            return False
        if normalized.startswith(("local ", "nearby ", "generic ")):
            return False
        return True

    @staticmethod
    def _normalize_place(
        item: dict[str, Any],
        destination: str,
        preference: str | None,
    ) -> dict[str, Any]:
        duration = item.get("estimated_duration_hours", item.get("estimated_visit_hours", 2.0))
        return {
            "name": item["name"],
            "category": item.get("category") or preference or "tourist_attraction",
            "address": item.get("address", destination),
            "description": item.get("description") or item.get("short_description", ""),
            "image_url": item.get("image_url"),
            "tags": item.get("tags", []),
            "best_time": item.get("best_time"),
            "estimated_cost": item.get("estimated_cost"),
            "estimated_visit_hours": duration,
            "rating": item.get("rating"),
            "review_count": item.get("review_count"),
            "latitude": item.get("latitude"),
            "longitude": item.get("longitude"),
            "source": item.get("source", "fallback_cache"),
        }

    @staticmethod
    def _budget_sorted_places(
        places: list[dict[str, Any]],
        budget: float | None,
        days: int,
    ) -> list[dict[str, Any]]:
        if not budget:
            return places
        daily_activity_budget = max(float(budget) * 0.18 / max(days, 1), 300)
        return sorted(
            places,
            key=lambda place: (
                float(place.get("estimated_cost") or 0) > daily_activity_budget,
                float(place.get("estimated_cost") or 0),
            ),
        )

    @staticmethod
    def _normalize_curated_place(
        item: dict[str, Any],
        destination: str,
        category: str,
    ) -> dict[str, Any]:
        return {
            "name": item["name"],
            "category": category,
            "address": normalize_destination_name(destination).replace("_", " ").title(),
            "description": item.get("description", ""),
            "image_url": item.get("image_url"),
            "tags": item.get("tags", []),
            "best_time": item.get("best_time") or item.get("recommended_visit_time"),
            "estimated_cost": item.get("estimated_cost"),
            "estimated_visit_hours": item.get("estimated_duration_hours", 2.0),
            "rating": None,
            "review_count": None,
            "latitude": None,
            "longitude": None,
            "source": "curated_fallback",
            "verified": True,
        }
