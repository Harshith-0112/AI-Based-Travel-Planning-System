from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.schemas import HotelOption


class BaseHotelProvider(ABC):
    """Abstract provider for hotel search sources."""

    provider_name: str = "base"

    @abstractmethod
    async def search_hotels(
        self,
        destination: str,
        check_in: str | None,
        check_out: str | None,
        adults: int = 1,
        budget: float | None = None,
    ) -> list[HotelOption]:
        raise NotImplementedError
