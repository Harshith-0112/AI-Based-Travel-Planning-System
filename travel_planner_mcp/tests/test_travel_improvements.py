from __future__ import annotations

import asyncio
from datetime import date
import json
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.agents.budget_agent import recalculate_budget_for_selected_hotel, rebalance_budget_to_fit
from app.agents.hotel_agent import HotelAgent
from app.agents.input_agent import InputAgent
from app.agents.places_agent import PlacesAgent
from app.agents.route_agent import RouteAgent
from app.agents.transport_agent import TransportAgent
from app.api.routes.itineraries import list_my_itineraries
from app.api.routes.trips import delete_trip, favourite_trips, favorite_trip, get_trip, recent_trips, save_trip
from app.mcp_servers.hotel_mcp import HotelSearchMCPServer
from app.db.models import SavedItinerary, Trip, User
from app.models.schemas import Attraction, BudgetBreakdown, HotelOption, TripRequest
from app.models.trip_schemas import TripCreate
from app.providers.fallback_places_provider import FallbackPlacesProvider
from app.providers.place_verifier import PlaceVerifier
from app.providers.hotel_provider_base import BaseHotelProvider
from app.services.place_image_service import PlaceImageService
from app.services.scoring_service import build_user_facing_hotel_reason
from app.utils.destination_normalizer import normalize_destination_name


class StaticHotelProvider(BaseHotelProvider):
    provider_name = "static"

    async def search_hotels(
        self,
        destination: str,
        check_in: str | None,
        check_out: str | None,
        adults: int = 1,
        budget: float | None = None,
    ) -> list[HotelOption]:
        return [
            HotelOption(
                name="Clean Budget Stay",
                address=destination,
                nightly_price=2000,
                total_price=4000,
                rating=3.8,
                review_count=300,
                source="test",
                distance_to_center_km=4.0,
            ),
            HotelOption(
                name="Balanced City Hotel",
                address=destination,
                nightly_price=4000,
                total_price=8000,
                rating=4.2,
                review_count=600,
                source="test",
                distance_to_center_km=3.0,
            ),
            HotelOption(
                name="Premium Palace Hotel",
                address=destination,
                nightly_price=7500,
                total_price=15000,
                rating=4.8,
                review_count=900,
                source="test",
                distance_to_center_km=1.0,
            ),
        ]


class FailingMapsMCP:
    async def search_nearby_places(self, destination: str, category: str) -> list[dict]:
        raise RuntimeError("maps down")

    async def geocode_location(self, query: str) -> dict:
        raise RuntimeError("geocode down")

    async def compute_route_matrix(
        self,
        origins: list[dict],
        destinations: list[dict],
        travel_mode: str = "DRIVE",
    ) -> list[dict]:
        raise RuntimeError("routes down")


class EmptyOllamaClient:
    async def generate_text(self, prompt: str, timeout: int = 20) -> str:
        return ""


class MysoreOllamaClient:
    def __init__(self) -> None:
        self.called = False

    async def generate_text(self, prompt: str, timeout: int = 20) -> str:
        self.called = True
        return """
[
  {
    "name": "Mysore Palace",
    "category": "history",
    "short_description": "A real royal palace in Mysore.",
    "estimated_duration_hours": 2,
    "confidence": 0.95
  },
  {
    "name": "Flexible local break",
    "category": "relaxation",
    "short_description": "Generic placeholder.",
    "estimated_duration_hours": 1,
    "confidence": 0.99
  }
]
"""


class VizagOllamaClient:
    def __init__(self) -> None:
        self.called = False

    async def generate_text(self, prompt: str, timeout: int = 20) -> str:
        self.called = True
        return """
[
  {
    "name": "RK Beach",
    "category": "beaches",
    "short_description": "A real beach in Visakhapatnam.",
    "estimated_duration_hours": 2,
    "confidence": 0.95
  },
  {
    "name": "Taj Mahal",
    "category": "history",
    "short_description": "Wrong city landmark.",
    "estimated_duration_hours": 2,
    "confidence": 0.95
  }
]
"""


class WrongCityOllamaClient:
    async def generate_text(self, prompt: str, timeout: int = 20) -> str:
        return """
[
  {"name": "Taj Mahal", "category": "history", "short_description": "Agra", "estimated_duration_hours": 2, "confidence": 0.95},
  {"name": "Mysore Palace", "category": "history", "short_description": "Mysore", "estimated_duration_hours": 2, "confidence": 0.95}
]
"""


class MemoryVerifiedCache:
    def __init__(self, places: list[dict] | None = None) -> None:
        self.places = places or []
        self.saved_places: list[dict] = []

    def get_verified_places(
        self,
        destination: str,
        preference: str | None = None,
        limit: int = 8,
    ) -> list[dict]:
        if preference:
            matching = [place for place in self.places if place.get("category") == preference]
            return (matching or self.places)[:limit]
        return self.places[:limit]

    def save_verified_places(self, destination: str, places: list[dict]) -> None:
        self.saved_places.extend(places)
        self.places.extend({**place, "source": "verified_cache"} for place in places)


class CoordinateMapsMCP:
    coordinates = {
        "rk beach": {"latitude": 17.7140, "longitude": 83.3237},
        "rushikonda beach": {"latitude": 17.7828, "longitude": 83.3848},
        "taj mahal": {"latitude": 27.1751, "longitude": 78.0421},
        "mysore palace": {"latitude": 12.3052, "longitude": 76.6552},
        "gateway of india": {"latitude": 18.9220, "longitude": 72.8347},
        "qutub minar": {"latitude": 28.5245, "longitude": 77.1855},
        "hawa mahal": {"latitude": 26.9239, "longitude": 75.8267},
        "bangalore palace": {"latitude": 12.9987, "longitude": 77.5920},
        "visakhapatnam": {"latitude": 17.6868, "longitude": 83.2185},
    }

    async def search_nearby_places(self, destination: str, category: str) -> list[dict]:
        raise RuntimeError("maps search down")

    async def geocode_location(self, query: str) -> dict:
        query_lower = query.lower()
        for name, coordinates in self.coordinates.items():
            if name in query_lower:
                return coordinates
        raise RuntimeError("not found")

    async def compute_route_matrix(
        self,
        origins: list[dict],
        destinations: list[dict],
        travel_mode: str = "DRIVE",
    ) -> list[dict]:
        raise RuntimeError("routes down")


class FakeOSMProvider:
    coordinates = {
        "visakhapatnam": {"latitude": 17.6868, "longitude": 83.2185},
        "rk beach": {"latitude": 17.7140, "longitude": 83.3237},
        "taj mahal": {"latitude": 27.1751, "longitude": 78.0421},
    }

    async def geocode_destination(self, query: str) -> dict | None:
        return self.coordinates.get(query.lower())

    async def geocode_place(self, place_name: str, destination: str) -> dict | None:
        return self.coordinates.get(place_name.lower())


class EmptyOSMProvider:
    async def geocode_destination(self, query: str) -> dict | None:
        return None

    async def geocode_place(self, place_name: str, destination: str) -> dict | None:
        return None


class FakeOSMPlacesProvider:
    def __init__(self, places: list[dict] | None = None) -> None:
        self.places = places or [
            {
                "name": "Kashi Vishwanath Temple",
                "category": "history",
                "address": "Varanasi",
                "description": "OpenStreetMap-listed historic temple in Varanasi.",
                "estimated_visit_hours": 2.0,
                "latitude": 25.3109,
                "longitude": 83.0107,
                "source": "openstreetmap",
                "verification_source": "openstreetmap",
                "verified": True,
            }
        ]
        self.called = False

    async def discover_places(
        self,
        destination: str,
        preference: str | None = None,
        limit: int = 8,
    ) -> list[dict]:
        self.called = True
        return self.places[:limit]


class EmptyOSMPlacesProvider:
    def __init__(self) -> None:
        self.called = False

    async def discover_places(
        self,
        destination: str,
        preference: str | None = None,
        limit: int = 8,
    ) -> list[dict]:
        self.called = True
        return []


class FakeImageMapsMCP:
    def __init__(self, photo_url: str | None = None) -> None:
        self.photo_url = photo_url
        self.called = False

    async def get_place_details(self, place_id: str) -> dict:
        self.called = True
        if not self.photo_url:
            raise RuntimeError("no google photo")
        return {"place_id": place_id, "photo_url": self.photo_url}


class FakeImageCache:
    def __init__(self, image_url: str | None = None) -> None:
        self.image_url = image_url
        self.cached: list[tuple[str, str]] = []

    def get_image_url(self, destination: str, place_name: str) -> str | None:
        return self.image_url

    def cache_image_url(
        self,
        destination: str,
        place: dict,
        image_url: str,
        source: str = "image_lookup",
    ) -> None:
        self.cached.append((place["name"], image_url))


class FakeWikimediaImageService(PlaceImageService):
    def __init__(
        self,
        maps_mcp: FakeImageMapsMCP,
        verified_cache: FakeImageCache,
        wikimedia_url: str | None = None,
    ) -> None:
        super().__init__(maps_mcp, verified_cache=verified_cache)
        self.wikimedia_url = wikimedia_url
        self.wikimedia_called = False

    async def _wikimedia_image_search(self, place_name: str, destination: str) -> str | None:
        self.wikimedia_called = True
        return self.wikimedia_url


def _select_hotel(hotel_preference: str) -> HotelOption:
    request = TripRequest(
        destination="Hyderabad",
        budget=30000,
        days=2,
        preferences=["history"],
        start_date=date(2026, 4, 10),
        travelers=2,
        hotel_preference=hotel_preference,
    )
    agent = HotelAgent(HotelSearchMCPServer(StaticHotelProvider()))
    hotel, _, _ = asyncio.run(agent.select_hotels(request))
    assert hotel is not None
    return hotel


def test_luxury_hotel_preference_selects_higher_quality_and_price() -> None:
    budget_hotel = _select_hotel("budget")
    luxury_hotel = _select_hotel("luxury")

    assert luxury_hotel.total_price is not None
    assert budget_hotel.total_price is not None
    assert luxury_hotel.total_price > budget_hotel.total_price
    assert (luxury_hotel.rating or 0) >= (budget_hotel.rating or 0)
    assert luxury_hotel.ranking_reason


def test_maps_failure_does_not_return_free_exploration() -> None:
    request = TripRequest(destination="Hyderabad", budget=12000, days=3, preferences=["history"])
    places_agent = PlacesAgent(
        FailingMapsMCP(),
        EmptyOllamaClient(),
        verified_cache=MemoryVerifiedCache(),
    )
    attractions, _ = asyncio.run(places_agent.get_ranked_attractions(request, selected_hotel=None))
    daily_plans = asyncio.run(RouteAgent(FailingMapsMCP()).build_daily_skeleton(request, None, attractions))

    titles = [activity.title.lower() for day in daily_plans for activity in day.activities]
    assert all("free exploration" not in title for title in titles)
    assert all("flexible local break" not in title for title in titles)


def test_fallback_places_are_returned_when_maps_fails() -> None:
    request = TripRequest(destination="Hyderabad", budget=12000, days=2, preferences=["history"])
    agent = PlacesAgent(
        FailingMapsMCP(),
        EmptyOllamaClient(),
        verified_cache=MemoryVerifiedCache(),
    )
    attractions, notes = asyncio.run(agent.get_ranked_attractions(request, selected_hotel=None))

    assert attractions
    assert attractions[0].source == "fallback_cache"
    assert any(place.name == "Charminar" for place in attractions)
    assert any("fallback cached places" in note for note in notes)


def test_transport_mode_auto_returns_valid_transport_option() -> None:
    option = asyncio.run(
        TransportAgent(FailingMapsMCP()).estimate_transport(
            starting_location="Warangal",
            destination="Hyderabad",
            travelers=2,
            transport_mode="auto",
            budget=12000,
        )
    )

    assert option.mode in {"bus", "car", "train", "flight"}
    assert option.estimated_cost > 0
    assert option.estimated_duration_hours > 0
    assert option.source == "estimated"


def test_itinerary_description_uses_place_context_not_generic_phrase() -> None:
    request = TripRequest(destination="Varanasi", budget=12000, days=1, preferences=["history"])
    attractions = [
        Attraction(
            name="Kashi Vishwanath Temple",
            category="history",
            description="A major temple in Varanasi's old city and a significant pilgrimage stop.",
            source="openstreetmap",
        )
    ]

    plans = asyncio.run(RouteAgent(FailingMapsMCP()).build_daily_skeleton(request, None, attractions))
    description = plans[0].activities[0].description or ""

    assert "Visit a history attraction with a relaxed pace" not in description
    assert "major temple" in description
    assert plans[0].activities[0].highlights
    assert plans[0].activities[0].visit_tips


def test_place_image_service_uses_google_photo_before_cache() -> None:
    cache = FakeImageCache(image_url="https://cache.example/kashi.jpg")
    service = FakeWikimediaImageService(
        FakeImageMapsMCP(photo_url="https://maps.example/kashi.jpg"),
        verified_cache=cache,
        wikimedia_url="https://commons.example/kashi.jpg",
    )
    attraction = Attraction(
        name="Kashi Vishwanath Temple",
        category="temples",
        place_id="places/kashi",
    )

    image_url = asyncio.run(service.get_image_url(attraction, "Varanasi"))

    assert image_url == "https://maps.example/kashi.jpg"
    assert cache.cached == [("Kashi Vishwanath Temple", "https://maps.example/kashi.jpg")]
    assert service.wikimedia_called is False


def test_place_image_service_uses_cached_image_before_wikimedia() -> None:
    cache = FakeImageCache(image_url="https://cache.example/palace.jpg")
    service = FakeWikimediaImageService(
        FakeImageMapsMCP(photo_url=None),
        verified_cache=cache,
        wikimedia_url="https://commons.example/palace.jpg",
    )
    attraction = Attraction(name="Mysore Palace", category="history", place_id="places/mysore")

    image_url = asyncio.run(service.get_image_url(attraction, "Mysore"))

    assert image_url == "https://cache.example/palace.jpg"
    assert cache.cached == []
    assert service.wikimedia_called is False


def test_place_image_service_returns_none_when_no_reliable_image_exists() -> None:
    service = FakeWikimediaImageService(
        FakeImageMapsMCP(photo_url=None),
        verified_cache=FakeImageCache(image_url=None),
        wikimedia_url=None,
    )
    attraction = Attraction(name="Unknown Place", category="history", place_id="places/unknown")

    image_url = asyncio.run(service.get_image_url(attraction, "Unknownville"))

    assert image_url is None


def test_selecting_alternative_hotel_changes_lodging_and_total_cost() -> None:
    original_budget = BudgetBreakdown(
        lodging_cost=4000,
        transport_cost=1200,
        food_cost=3000,
        misc_cost=800,
        total_estimated_cost=9000,
        budget=12000,
        within_budget=True,
    )
    selected_hotel = HotelOption(
        name="Better Hotel",
        address="City Center",
        nightly_price=3500,
        total_price=7000,
        rating=4.5,
        source="test",
    )

    updated = recalculate_budget_for_selected_hotel(original_budget, selected_hotel, days=3)

    assert updated.lodging_cost == 7000
    assert updated.total_estimated_cost == 12000
    assert updated.total_estimated_cost != original_budget.total_estimated_cost
    assert updated.within_budget is True


def test_user_facing_hotel_reason_hides_internal_scoring_values() -> None:
    request = TripRequest(
        destination="Mysore",
        budget=15000,
        days=3,
        preferences=["history"],
        hotel_preference="luxury",
    )
    hotel = HotelOption(
        name="Good Hotel",
        address="Mysore",
        nightly_price=2500,
        total_price=7500,
        rating=4.7,
        source="test",
        ranking_reason="affordability=1.00, budget_fit=0.98, distance=0.60",
    )

    reason = build_user_facing_hotel_reason(hotel, request)

    assert "luxury preference" in reason
    assert "4.7 rating" in reason
    assert "affordability=" not in reason
    assert "budget_fit=" not in reason
    assert "distance=" not in reason


def test_normal_streamlit_ui_does_not_show_hotel_score_details() -> None:
    root = Path(__file__).resolve().parents[1]
    streamlit_source = (root / "frontend" / "streamlit_app.py").read_text(encoding="utf-8")
    page_source = (root / "frontend" / "page.py").read_text(encoding="utf-8")

    assert "ranking_score" not in streamlit_source
    assert "ranking_score" not in page_source
    assert "affordability=" not in streamlit_source
    assert "budget_fit=" not in streamlit_source


def test_rebalance_keeps_total_within_budget_when_cheaper_hotel_available() -> None:
    request = TripRequest(
        destination="Mysore",
        budget=15000,
        days=3,
        preferences=["history"],
        hotel_preference="standard",
    )
    expensive = HotelOption(
        name="Expensive Hotel",
        address="Mysore",
        nightly_price=6500,
        total_price=13000,
        rating=4.8,
        ranking_score=0.9,
        source="test",
    )
    cheaper = HotelOption(
        name="Cheaper Hotel",
        address="Mysore",
        nightly_price=3500,
        total_price=7000,
        rating=4.2,
        ranking_score=0.7,
        source="test",
    )
    budget = BudgetBreakdown(
        lodging_cost=13000,
        transport_cost=1500,
        food_cost=2500,
        misc_cost=800,
        total_estimated_cost=17800,
        budget=15000,
        within_budget=False,
        over_budget_amount=2800,
    )

    hotel, _, updated, _ = rebalance_budget_to_fit(
        request,
        budget,
        expensive,
        [expensive, cheaper],
    )

    assert hotel is not None
    assert hotel.name == "Cheaper Hotel"
    assert updated.total_estimated_cost <= request.budget
    assert updated.budget_warning == "Adjusted recommendations to stay within your budget."


def test_luxury_preference_returns_warning_when_budget_cannot_fit() -> None:
    request = TripRequest(
        destination="Mysore",
        budget=9000,
        days=3,
        preferences=["history"],
        hotel_preference="luxury",
    )
    luxury = HotelOption(
        name="Luxury Hotel",
        address="Mysore",
        nightly_price=6000,
        total_price=12000,
        rating=4.8,
        ranking_score=0.9,
        source="test",
    )
    budget = BudgetBreakdown(
        lodging_cost=12000,
        transport_cost=2000,
        food_cost=4500,
        misc_cost=1200,
        total_estimated_cost=19700,
        budget=9000,
        within_budget=False,
        over_budget_amount=10700,
    )

    _, _, updated, _ = rebalance_budget_to_fit(request, budget, luxury, [luxury])

    assert updated.within_budget is False
    assert updated.budget_status == "preference_exceeds_budget"
    assert updated.budget_warning is not None
    assert "Luxury hotels may exceed this budget" in updated.budget_warning


def test_fake_fallback_names_are_rejected(tmp_path) -> None:
    fallback_file = tmp_path / "test_city.json"
    fallback_file.write_text(
        json.dumps(
            [
                {"name": "City Heritage Walk", "category": "history"},
                {"name": "Flexible local break", "category": "relaxation"},
                {"name": "Bangalore Palace", "category": "history"},
            ]
        ),
        encoding="utf-8",
    )
    provider = FallbackPlacesProvider(data_dir=tmp_path)
    places = provider.get_places("Test City", use_default_if_missing=False)

    assert [place["name"] for place in places] == ["Bangalore Palace"]
    assert not provider.is_valid_place_name("Free exploration")
    assert not provider.is_valid_place_name("Nearby cafe")


def test_maps_failure_missing_city_fallback_triggers_ollama(tmp_path) -> None:
    ollama = VizagOllamaClient()
    provider = FallbackPlacesProvider(data_dir=tmp_path)
    cache = MemoryVerifiedCache()
    request = TripRequest(destination="vizag", budget=12000, days=1, preferences=["beaches"])
    agent = PlacesAgent(
        CoordinateMapsMCP(),
        ollama,
        fallback_provider=provider,
        osm_places_provider=EmptyOSMPlacesProvider(),
        verified_cache=cache,
    )

    attractions, _ = asyncio.run(agent.get_ranked_attractions(request, selected_hotel=None))

    assert ollama.called is True
    assert attractions
    assert attractions[0].name == "RK Beach"
    assert attractions[0].source == "verified_ai"
    assert cache.saved_places
    assert all("taj mahal" not in item.name.lower() for item in attractions)


def test_vizag_normalizes_to_visakhapatnam() -> None:
    assert normalize_destination_name("vizag") == "visakhapatnam"


def test_common_destination_aliases_normalize() -> None:
    assert normalize_destination_name("benaras") == "varanasi"
    assert normalize_destination_name("bombay") == "mumbai"
    assert normalize_destination_name("bengaluru") == "bangalore"


def test_wrong_city_landmarks_are_rejected_for_vizag() -> None:
    verifier = PlaceVerifier(CoordinateMapsMCP())
    candidates = [
        {"name": "Taj Mahal", "category": "history"},
        {"name": "Mysore Palace", "category": "history"},
        {"name": "Gateway of India", "category": "history"},
        {"name": "Qutub Minar", "category": "history"},
        {"name": "Hawa Mahal", "category": "history"},
    ]

    verified = asyncio.run(verifier.verify_candidates("vizag", candidates, preference="history"))

    assert verified == []


def test_verified_candidate_near_destination_is_accepted() -> None:
    verifier = PlaceVerifier(CoordinateMapsMCP())
    candidates = [
        {
            "name": "RK Beach",
            "category": "beaches",
            "description": "A real Visakhapatnam beach.",
            "estimated_visit_hours": 2,
        }
    ]

    verified = asyncio.run(verifier.verify_candidates("vizag", candidates, preference="beaches"))

    assert len(verified) == 1
    assert verified[0]["name"] == "RK Beach"
    assert verified[0]["source"] == "verified_ai"
    assert verified[0]["verified"] is True


def test_osm_verifies_candidate_when_google_geocoding_fails() -> None:
    verifier = PlaceVerifier(FailingMapsMCP(), osm_provider=FakeOSMProvider())
    candidates = [
        {
            "name": "RK Beach",
            "category": "beaches",
            "description": "A real Visakhapatnam beach.",
            "estimated_visit_hours": 2,
        }
    ]

    verified = asyncio.run(verifier.verify_candidates("vizag", candidates, preference="beaches"))

    assert len(verified) == 1
    assert verified[0]["name"] == "RK Beach"
    assert verified[0]["verification_source"] == "openstreetmap"


def test_taj_mahal_still_rejected_for_vizag_with_osm_available() -> None:
    verifier = PlaceVerifier(FailingMapsMCP(), osm_provider=FakeOSMProvider())
    candidates = [{"name": "Taj Mahal", "category": "history"}]

    verified = asyncio.run(verifier.verify_candidates("vizag", candidates, preference="history"))

    assert verified == []


def test_far_candidate_is_rejected_by_distance() -> None:
    verifier = PlaceVerifier(CoordinateMapsMCP())
    candidates = [{"name": "Bangalore Palace", "category": "history"}]

    verified = asyncio.run(verifier.verify_candidates("vizag", candidates, preference="history"))

    assert verified == []


def test_all_rejected_candidates_show_warning_instead_of_fake_places(tmp_path) -> None:
    request = TripRequest(destination="Unknownville", budget=12000, days=1, preferences=["history"])
    agent = PlacesAgent(
        FailingMapsMCP(),
        WrongCityOllamaClient(),
        fallback_provider=FallbackPlacesProvider(data_dir=tmp_path),
        osm_places_provider=EmptyOSMPlacesProvider(),
        place_verifier=PlaceVerifier(FailingMapsMCP(), osm_provider=EmptyOSMProvider()),
        verified_cache=MemoryVerifiedCache(),
    )

    attractions, notes = asyncio.run(agent.get_ranked_attractions(request, selected_hotel=None))
    daily_plans = asyncio.run(RouteAgent(FailingMapsMCP()).build_daily_skeleton(request, None, attractions))

    assert attractions == []
    assert any("Unable to verify attractions" in note for note in notes)
    assert daily_plans[0].activities == []
    assert any("Unable to verify attractions" in warning for warning in daily_plans[0].warnings)


def test_curated_fallback_loads_when_verification_sources_fail(tmp_path) -> None:
    request = TripRequest(destination="Varanasi", budget=12000, days=1, preferences=["temples"])
    agent = PlacesAgent(
        FailingMapsMCP(),
        EmptyOllamaClient(),
        fallback_provider=FallbackPlacesProvider(data_dir=tmp_path),
        osm_places_provider=EmptyOSMPlacesProvider(),
        place_verifier=PlaceVerifier(FailingMapsMCP(), osm_provider=EmptyOSMProvider()),
        verified_cache=MemoryVerifiedCache(),
    )

    attractions, notes = asyncio.run(agent.get_ranked_attractions(request, selected_hotel=None))

    assert attractions
    assert attractions[0].name == "Kashi Vishwanath Temple"
    assert attractions[0].source == "curated_fallback"
    assert attractions[0].description
    assert attractions[0].tags
    assert attractions[0].best_time == "Morning"
    assert any("curated fallback" in note.lower() for note in notes)


def test_curated_fallback_prevents_duplicates_and_filters_category() -> None:
    provider = FallbackPlacesProvider()

    places = provider.get_places_for_preferences(
        "Delhi",
        preferences=["history", "history"],
        days=2,
        budget=15000,
        limit=6,
    )
    names = [place["name"] for place in places]

    assert len(names) == len(set(names))
    assert "Red Fort" in names
    assert all(place["source"] == "curated_fallback" for place in places)

    temple_places = provider.get_places_for_preferences("Varanasi", preferences=["temples"], limit=3)
    assert temple_places[0]["name"] == "Kashi Vishwanath Temple"
    assert temple_places[0]["category"] == "temples"


def test_both_google_and_osm_failure_show_warning(tmp_path) -> None:
    request = TripRequest(destination="Unknownville", budget=12000, days=1, preferences=["history"])
    agent = PlacesAgent(
        FailingMapsMCP(),
        WrongCityOllamaClient(),
        fallback_provider=FallbackPlacesProvider(data_dir=tmp_path),
        osm_places_provider=EmptyOSMPlacesProvider(),
        place_verifier=PlaceVerifier(FailingMapsMCP(), osm_provider=EmptyOSMProvider()),
        verified_cache=MemoryVerifiedCache(),
    )

    attractions, notes = asyncio.run(agent.get_ranked_attractions(request, selected_hotel=None))

    assert attractions == []
    assert any("Unable to verify attractions" in note for note in notes)


def test_varanasi_missing_static_fallback_uses_osm_places(tmp_path) -> None:
    osm_provider = FakeOSMPlacesProvider()
    cache = MemoryVerifiedCache()
    request = TripRequest(destination="varanasi", budget=12000, days=1, preferences=["history"])
    agent = PlacesAgent(
        FailingMapsMCP(),
        EmptyOllamaClient(),
        fallback_provider=FallbackPlacesProvider(data_dir=tmp_path),
        osm_places_provider=osm_provider,
        verified_cache=cache,
    )

    attractions, notes = asyncio.run(agent.get_ranked_attractions(request, selected_hotel=None))

    assert osm_provider.called is True
    assert attractions
    assert attractions[0].name == "Kashi Vishwanath Temple"
    assert attractions[0].source == "openstreetmap"
    assert attractions[0].verified is True
    assert cache.saved_places
    assert not any("Unable to verify attractions" in note for note in notes)


def test_overpass_empty_and_ollama_verification_failure_still_warns(tmp_path) -> None:
    request = TripRequest(destination="Unknownville", budget=12000, days=1, preferences=["history"])
    agent = PlacesAgent(
        FailingMapsMCP(),
        WrongCityOllamaClient(),
        fallback_provider=FallbackPlacesProvider(data_dir=tmp_path),
        osm_places_provider=EmptyOSMPlacesProvider(),
        place_verifier=PlaceVerifier(FailingMapsMCP(), osm_provider=EmptyOSMProvider()),
        verified_cache=MemoryVerifiedCache(),
    )

    attractions, notes = asyncio.run(agent.get_ranked_attractions(request, selected_hotel=None))

    assert attractions == []
    assert any("Unable to verify attractions" in note for note in notes)


def test_mysore_fallback_returns_real_places() -> None:
    provider = FallbackPlacesProvider()
    places = provider.get_places("Mysore", limit=12, use_default_if_missing=False)
    names = {place["name"] for place in places}

    assert "Mysore Palace" in names
    assert "Chamundi Hill" in names
    assert "Rail Museum Mysore" in names


def test_visakhapatnam_static_fallback_returns_real_places() -> None:
    provider = FallbackPlacesProvider()
    places = provider.get_places("vizag", limit=12, use_default_if_missing=False)
    names = {place["name"] for place in places}

    assert "RK Beach" in names
    assert "INS Kurusura Submarine Museum" in names
    assert "Borra Caves" in names


def test_saved_trips_are_filtered_by_current_user() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            SavedItinerary(
                user_id=1,
                title="Mine",
                destination="Hyderabad",
                days=2,
                budget=10000,
                travelers=1,
                preferences="history",
                itinerary_json="{}",
            )
        )
        session.add(
            SavedItinerary(
                user_id=2,
                title="Not Mine",
                destination="Goa",
                days=3,
                budget=20000,
                travelers=2,
                preferences="beaches",
                itinerary_json="{}",
            )
        )
        session.commit()

        current_user = User(
            id=1,
            full_name="User One",
            email="user1@example.com",
            hashed_password="test",
        )
        itineraries = list_my_itineraries(current_user=current_user, session=session)

    assert len(itineraries) == 1
    assert itineraries[0].title == "Mine"
    assert itineraries[0].user_id == 1


def test_database_trips_are_filtered_by_current_user() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        user_one = User(id=1, full_name="User One", email="one@example.com", hashed_password="test")
        user_two = User(id=2, full_name="User Two", email="two@example.com", hashed_password="test")

        own_trip = save_trip(
            TripCreate(
                destination="Varanasi",
                request_json={"destination": "Varanasi", "days": 2, "budget": 12000},
                response_json={"summary": "User one trip"},
                selected_hotel_json={"name": "Hotel A"},
                budget_breakdown_json={"total_estimated_cost": 9000},
            ),
            current_user=user_one,
            session=session,
        )
        other_trip = Trip(
            user_id=2,
            destination="Goa",
            request_json='{"destination": "Goa"}',
            response_json='{"summary": "User two trip"}',
            selected_hotel_json="{}",
            budget_breakdown_json="{}",
            is_favorite=True,
        )
        session.add(other_trip)
        session.commit()
        session.refresh(other_trip)

        visible_recent = recent_trips(current_user=user_one, session=session)
        visible_favourites = favourite_trips(current_user=user_one, session=session)

        assert len(visible_recent) == 1
        assert visible_recent[0].destination == "Varanasi"
        assert visible_favourites == []

        favorite_trip(own_trip.id, current_user=user_one, session=session)
        assert len(favourite_trips(current_user=user_one, session=session)) == 1

        assert get_trip(own_trip.id, current_user=user_one, session=session).id == own_trip.id
        with pytest.raises(Exception):
            get_trip(other_trip.id, current_user=user_one, session=session)
        delete_trip(own_trip.id, current_user=user_one, session=session)
        assert recent_trips(current_user=user_one, session=session) == []


def test_old_requests_without_new_fields_still_work() -> None:
    request = TripRequest(destination="Mysore", budget=15000, days=3, preferences=["history"])
    normalized = InputAgent().normalize(request)

    assert normalized.hotel_preference == "standard"
    assert normalized.transport_mode == "auto"
