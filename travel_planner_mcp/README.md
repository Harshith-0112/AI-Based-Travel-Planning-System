# AI-Based Travel Planning System Using Multi-Agent Architecture and MCP Integration

## 1. Project Overview
This mini-project is a local-first AI travel planner that builds a day-by-day itinerary from destination, budget, trip duration, and user preferences. It combines a FastAPI backend, Streamlit frontend, Ollama-powered local LLM support, MCP-style tool wrappers, and provider abstractions for hotels and maps.

## 2. Problem Statement
Students and travelers often need a simple planning assistant that can combine itinerary generation, hotel selection, route estimation, and budget reasoning in one workflow. Many solutions depend fully on cloud APIs and break during demos. This project is designed to remain usable even when APIs are unavailable.

## 3. Why MCP Is Used
MCP-style wrappers make external tools easy to explain and reuse. Instead of allowing the LLM to directly invent data, the application calls explicit tools for hotel search and maps operations. This keeps the architecture modular, testable, and viva-friendly.

## 4. Why Ollama Is Used Instead of OpenAI
Ollama runs fully on the local machine, avoids cloud dependency, and supports free local inference with configurable open models like `qwen2.5:7b-instruct`, `llama3.1:8b`, and `mistral:7b`. This satisfies the academic requirement of a local-first demo without using the OpenAI API.

## 5. Architecture Explanation
- `InputAgent` normalizes and validates the trip request.
- `HotelAgent` queries the hotel MCP wrapper and ranks hotels using a transparent weighted score.
- `PlacesAgent` gets attractions from maps tools and uses Ollama only for light ranking/description support.
- `RouteAgent` builds day-wise plans and computes commute information.
- `BudgetAgent` estimates lodging, transport, food, and miscellaneous costs.
- `ItineraryAgent` creates the final human-readable summary and hotel reasoning.
- `ExportAgent` exports the final itinerary into JSON and ICS formats.

The project follows a tools-first, LLM-second strategy:
- tools provide prices, locations, routes, and structured data
- Ollama provides natural-language interpretation and summaries

## 6. Folder Structure
```text
travel_planner_mcp/
  app/
    agents/
    api/
    mcp_servers/
    models/
    providers/
    services/
    utils/
  frontend/
    streamlit_app.py
  tests/
  .env.example
  requirements.txt
  README.md
```

## 7. Setup Instructions
```bash
cd travel_planner_mcp
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## 8. How to Install and Run Ollama
1. Install Ollama from [https://ollama.com/download](https://ollama.com/download)
2. Start Ollama:
```bash
ollama serve
```

## 9. How to Pull the Default Model
```bash
ollama pull qwen2.5:7b-instruct
```
Optional models:
```bash
ollama pull llama3.1:8b
ollama pull mistral:7b
```

## 10. How to Enable Google Maps APIs
1. Create a Google Cloud project.
2. Enable:
   - Geocoding API
   - Places API
   - Routes API
3. Create an API key.
4. Put the key in `.env` as `GOOGLE_MAPS_API_KEY=...`

## 11. How to Get a SerpAPI Key
1. Create an account at [https://serpapi.com](https://serpapi.com)
2. Copy the API key from the dashboard.
3. Add it to `.env` as `SERPAPI_API_KEY=...`

## 12. How Fallback Mode Works
- If `SERPAPI_API_KEY` is missing, the app uses `MockHotelProvider`
- If `GOOGLE_MAPS_API_KEY` is missing, the app uses `MockMapsProvider`
- If Ollama is not reachable, the app uses deterministic summary text

This means the project still works offline for demos and viva.

## 13. Run Instructions
Start the backend:
```bash
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Start the frontend in a second terminal:
```bash
streamlit run frontend/streamlit_app.py
```

Run tests:
```bash
pytest
```

## 14. Sample API Requests
### `POST /plan-trip`
```json
{
  "destination": "Mysore",
  "budget": 15000,
  "days": 3,
  "preferences": ["history", "food"],
  "start_date": "2026-04-10",
  "travelers": 2,
  "starting_location": "Bengaluru"
}
```

### Example Response Shape
```json
{
  "trip_request": {
    "destination": "Mysore",
    "budget": 15000,
    "days": 3,
    "preferences": ["history", "food"],
    "start_date": "2026-04-10",
    "travelers": 2,
    "starting_location": "Bengaluru"
  },
  "hotel": {
    "name": "Mysore Central Stay",
    "nightly_price": 2500.0,
    "source": "mock"
  },
  "daily_plans": [
    {
      "day_number": 1,
      "theme": "History Focus"
    }
  ]
}
```

## 15. Sample UI Screenshot Placeholders
- `docs/screenshots/home.png`
- `docs/screenshots/generated-plan.png`

## 16. Sample Itinerary Output
Day 1 may include Mysore Palace in the morning, a heritage museum in the afternoon, and a local food street in the evening, with travel time and cost estimates shown for each step.

## 17. Sample ICS Output
```ics
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//TravelPlannerMCP//EN
BEGIN:VEVENT
SUMMARY:Day 1 - History Focus
DESCRIPTION:Hotel: Mysore Central Stay\nHotel nightly price: 2500.0\nAttractions: Mysore Palace, Museum Visit\nEstimated travel time: 45.0 minutes\nDaily estimated cost: 1350.0
END:VEVENT
END:VCALENDAR
```

## 18. Limitations
- Live hotel pricing depends on SerpAPI quota and availability.
- Live routes and places depend on Google Maps APIs being enabled.
- Ollama model quality depends on local machine resources.
- Budgeting uses reasonable heuristics for food and transport, not real receipts.

## 19. Future Scope
- Add more travel modes like walking and transit optimization
- Add restaurant recommendation scoring
- Add PDF export
- Add user login and trip history
- Add weather and seasonal recommendations

## 20. Viva / Demo Talking Points
- Explain the tools-first principle and why the LLM is not trusted for prices and distances.
- Show the provider abstraction and how fallback mode prevents demo failure.
- Explain the MCP-style tool layer as a reusable interface for maps and hotel search.
- Show how multi-agent separation improves clarity and modularity.
- Explain why Ollama was chosen for local inference and academic reproducibility.

## 21. Academic Notes
This project is intentionally designed as a clear MVP. The code favors modularity, type hints, transparent scoring, and graceful degradation so it is easy to defend in a viva and easy to extend in future.
