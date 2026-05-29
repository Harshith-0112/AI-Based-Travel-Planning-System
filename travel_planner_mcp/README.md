# AI Travel Planner

AI Travel Planner is a full-stack trip planning application built with FastAPI, React, SQLite, SQLModel, Ollama, and MCP-style provider wrappers. It generates budget-aware travel plans with hotels, transport estimates, day-wise itineraries, verified places, recent trips, and favourites.

The project is designed for local-first demos: Google Maps and SerpAPI can improve live data quality, but the app still produces realistic itineraries through OpenStreetMap, verified cache, Ollama-assisted candidate generation, and curated fallback tourist datasets.



## Current Status

- React + Vite + Tailwind frontend
- FastAPI backend with protected auth routes
- SQLite database using SQLModel
- JWT-based login and registration
- Database-backed Recent Trips and Favourites
- Selectable hotels with budget recalculation
- Budget-aware hotel ranking and rebalance warnings
- Transport mode support
- Verified place fallback pipeline
- Curated India and international tourist place datasets
- Ollama integration for local LLM summaries and safe enrichment
- Streamlit app preserved as a legacy interface

## Architecture

The backend uses a modular multi-agent flow:

- `InputAgent` validates and normalizes user trip requests.
- `HotelAgent` fetches hotel options and ranks them by budget fit, quality, and preference.
- `TransportAgent` estimates practical transport options based on distance and mode.
- `PlacesAgent` retrieves and verifies attractions through maps, cache, OSM, Ollama candidates, and curated fallback data.
- `RouteAgent` builds day-wise itinerary activities from verified or curated attractions.
- `BudgetAgent` estimates lodging, transport, food, misc cost, and rebalances when possible.
- `ItineraryAgent` assembles the final trip response.
- `ExportAgent` supports itinerary export formats.

The core principle is tools first, LLM second. The LLM is not trusted as the source of truth for place existence, prices, coordinates, or ownership of user data.

## Verified Place Pipeline

When attractions are needed, the app follows this order:

1. Google Maps Places search
2. Verified places cache from SQLite
3. Destination-specific static fallback JSON in `app/data/fallback_places/`
4. OpenStreetMap discovery through Overpass
5. Ollama candidate generation plus Google Maps or OpenStreetMap verification
6. Curated tourist place datasets:
   - `app/data/india_places.json`
   - `app/data/international_places.json`
7. User-facing warning if no reliable places are available

Unverified Ollama places are never shown as normal itinerary items. Wrong-city landmarks and generic placeholder names are rejected before display.

## Curated Fallback Dataset

The curated fallback system provides realistic places when live APIs fail. It supports India and international destinations, destination aliases, user preference matching, budget-aware ordering, duplicate prevention, and deterministic descriptions.

Example dataset shape:

```json
{
  "varanasi": {
    "temples": [
      {
        "name": "Kashi Vishwanath Temple",
        "description": "One of the most sacred Hindu temples dedicated to Lord Shiva.",
        "tags": ["temple", "spiritual", "old city"],
        "estimated_cost": 300,
        "best_time": "Morning"
      }
    ]
  }
}
```

Supported curated India examples include Delhi, Mumbai, Hyderabad, Bangalore, Chennai, Kolkata, Jaipur, Udaipur, Mysore, Kochi, Goa, Varanasi, Amritsar, Agra, Visakhapatnam, Ooty, Manali, Shimla, Darjeeling, Srinagar, Pondicherry, Rishikesh, Hampi, Mahabalipuram, Tirupati, Madurai, Andaman, and Leh-Ladakh.

Supported international examples include Paris, London, Rome, Dubai, Singapore, Tokyo, Bangkok, Bali, New York, Los Angeles, Istanbul, Sydney, Zurich, Barcelona, Amsterdam, Seoul, Hong Kong, and Maldives.

## Frontend

The main frontend is in `frontend/` and uses:

- React
- Vite
- Tailwind CSS
- React Router
- Axios
- React Hot Toast

Main pages:

- `Login`
- `Register`
- `Dashboard`
- `Create Trip`
- `Trip Result`
- `Trips` with Recent and Favourites tabs

Frontend features:

- Dark glassmorphism UI
- Multi-step trip creation form
- Protected routes
- JWT token storage
- Current trip recovery through localStorage
- Database-backed recent and favourite trips
- Selectable hotel cards without reordering
- Budget cards and progress bars
- Itinerary descriptions, tags, best-time badges, and source badges

## Backend API Routes

Common routes include:

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `POST /plan-trip`
- `POST /trips`
- `GET /trips/recent`
- `GET /trips/favourites`
- `GET /trips/{trip_id}`
- `POST /trips/{trip_id}/favorite`
- `POST /trips/{trip_id}/unfavorite`
- `DELETE /trips/{trip_id}`
- Legacy itinerary routes under `/itineraries`

All trip persistence endpoints are protected and filter by `current_user.id`.

## Project Structure

```text
travel_planner_mcp/
  app/
    agents/                 # Trip planning agents
    api/                    # FastAPI app and route modules
    data/
      fallback_places/      # Destination-specific offline fallback JSON
      india_places.json     # Curated India tourist places
      international_places.json
    db/                     # SQLModel models and database setup
    mcp_servers/            # MCP-style maps and hotel wrappers
    models/                 # Pydantic/SQLModel schemas
    providers/              # Hotel, OSM, verifier, fallback providers
    services/               # Ollama and scoring services
    utils/                  # Normalization and helpers
  frontend/
    src/
      api/
      components/
      context/
      pages/
      utils/
  tests/
  frontend/streamlit_app.py # Legacy Streamlit UI, kept for compatibility
  requirements.txt
  README.md
```

## Setup

Create a virtual environment and install backend dependencies:

```bash
cd travel_planner_mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Start the backend:

```bash
./.venv/bin/uvicorn app.api.main:app --reload --host 127.0.0.1 --port 8000
```

Install and run the React frontend:

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

Open:

```text
http://127.0.0.1:5173
```

The FastAPI backend runs at:

```text
http://127.0.0.1:8000
```

## Ollama Setup

Install Ollama from:

```text
https://ollama.com/download
```

Start Ollama:

```bash
ollama serve
```

Pull a local model:

```bash
ollama pull qwen2.5:7b-instruct
```

Optional models:

```bash
ollama pull llama3.1:8b
ollama pull mistral:7b
```

Ollama is used for destination summaries, safe description enrichment for already verified places, and candidate generation only when stronger place sources fail.

## Optional API Keys

Google Maps:

```env
GOOGLE_MAPS_API_KEY=your_key_here
```

Enable Geocoding API, Places API, and Routes API in Google Cloud.

SerpAPI:

```env
SERPAPI_API_KEY=your_key_here
```

Without these keys, the app falls back to mock hotels, OpenStreetMap, verified cache, Ollama candidates with verification, and curated fallback datasets.

## Database

The app uses SQLite through SQLModel. The database stores:

- Users
- Saved/generated trips
- Recent trips
- Favourite trips
- Selected hotels
- Budget breakdown JSON
- Verified places cache

Trip records are always scoped by `user_id`, so User A cannot read, favourite, delete, or list User B's trips.

## Testing

Run backend tests:

```bash
./.venv/bin/pytest -q
```

Validate the React build:

```bash
cd frontend
npm install
npm run build
```

Useful manual checks:

- Register two users and confirm trips do not leak across accounts.
- Generate a trip with Google Maps disabled and verify fallback places still appear.
- Try aliases such as `vizag`, `benaras`, `bombay`, and `banglore`.
- Select alternative hotels and confirm the hotel card order stays stable.
- Mark a trip as favourite, refresh, and confirm it persists.

## UI Screenshots

Add screenshots here when preparing a report or portfolio:

- `docs/screenshots/dashboard.png`
- `docs/screenshots/create-trip.png`
- `docs/screenshots/trip-result.png`
- `docs/screenshots/trips-library.png`

## Limitations

- Live prices depend on external provider availability and quotas.
- OpenStreetMap coverage varies by destination and tag quality.
- Curated fallback data covers popular destinations, not every town.
- Ollama output quality depends on the local model and machine resources.
- Budget estimates are planning estimates, not guaranteed real-world costs.
- International curated costs are approximate and normalized for itinerary comparison.

## Future Scope

- Add weather-aware planning.
- Add live restaurant discovery and booking links.
- Add PDF export.
- Add route map visualization in React.
- Expand curated datasets by country and season.
- Add admin tools for managing fallback tourist data.
- Add background refresh jobs for verified place cache.

## Demo Talking Points

- The app preserves user trust by verifying places before display.
- Curated fallback data prevents API failures from breaking demos.
- Database-backed Recent and Favourites prove authenticated persistence.
- MCP-style wrappers keep external services isolated from agent logic.
- Ollama is used as a local assistant, not as an unchecked source of truth.
