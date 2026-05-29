from __future__ import annotations

import json
import re
from typing import Any

from app.providers.fallback_places_provider import FallbackPlacesProvider
from app.services.ollama_client import OllamaClient
from app.utils.destination_normalizer import display_destination_name


class OllamaCandidateProvider:
    """Asks Ollama for candidate place names, not trusted itinerary places."""

    def __init__(self, ollama_client: OllamaClient) -> None:
        self.ollama_client = ollama_client

    async def generate_candidates(
        self,
        destination: str,
        preference: str | None = None,
        limit: int = 12,
    ) -> list[dict[str, Any]]:
        normalized_destination = display_destination_name(destination)
        prompt = f"""
Return only real tourist places located in or near {normalized_destination}, India.
Do not return famous places from other Indian cities.
Do not return generic placeholders like city walk, local break, nearby cafe, free exploration.
If unsure, do not include the place.
Preference: {preference or "tourist attractions"}
Return only JSON.
Ask for up to {limit} candidates.
Fields: name, category, short_description, estimated_duration_hours, confidence, day_trip.
"""
        text = await self.ollama_client.generate_text(prompt, timeout=12)
        return self._parse_candidates(text, limit)

    @staticmethod
    def _parse_candidates(text: str | None, limit: int) -> list[dict[str, Any]]:
        if not text:
            return []
        try:
            match = re.search(r"\[.*\]", text, re.DOTALL)
            if not match:
                return []
            data = json.loads(match.group(0))
        except (json.JSONDecodeError, TypeError):
            return []

        if not isinstance(data, list):
            return []

        candidates: list[dict[str, Any]] = []
        for item in data[:limit]:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            normalized_name = _normalized_place_name(name)
            if normalized_name != "central museum" and not FallbackPlacesProvider.is_valid_place_name(name):
                continue
            try:
                confidence = float(item.get("confidence", 0.0))
            except (TypeError, ValueError):
                confidence = 0.0
            if confidence < 0.55:
                continue
            candidates.append(
                {
                    "name": name,
                    "category": item.get("category") or "tourist_attraction",
                    "description": item.get("short_description") or item.get("description", ""),
                    "estimated_visit_hours": item.get("estimated_duration_hours", 2.0),
                    "confidence": confidence,
                    "day_trip": bool(item.get("day_trip", False)),
                    "source": "ollama_candidate",
                }
            )
        return candidates


def _normalized_place_name(name: Any) -> str:
    if not isinstance(name, str):
        return ""
    return re.sub(r"[^a-z0-9]+", " ", name.strip().lower()).strip()
