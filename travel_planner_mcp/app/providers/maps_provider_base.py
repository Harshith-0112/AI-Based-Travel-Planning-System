from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseMapsProvider(ABC):
    provider_name: str = "base"

    @abstractmethod
    async def geocode_location(self, query: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def search_nearby_places(self, destination: str, category: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def compute_route_matrix(
        self,
        origins: list[dict[str, Any]],
        destinations: list[dict[str, Any]],
        travel_mode: str = "DRIVE",
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def get_place_details(self, place_id: str) -> dict[str, Any]:
        raise NotImplementedError
