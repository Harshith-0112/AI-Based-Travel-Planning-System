from __future__ import annotations

from datetime import date

import httpx
import streamlit as st


FASTAPI_URL = "http://localhost:8000"
PREFERENCES = [
    "nature",
    "food",
    "shopping",
    "adventure",
    "history",
    "temples",
    "beaches",
    "nightlife",
    "family",
    "relaxation",
]


st.set_page_config(page_title="AI Travel Planner MCP", layout="wide")
st.title("AI-Based Travel Planning System")
st.caption("Multi-agent itinerary generation with MCP-style tools, Ollama, and graceful fallback providers.")

with st.sidebar:
    st.subheader("Trip Inputs")
    destination = st.text_input("Destination", value="Mysore")
    budget = st.number_input("Total Budget", min_value=1000.0, value=15000.0, step=500.0)
    days = st.slider("Number of Days", min_value=1, max_value=7, value=3)
    preferences = st.multiselect("Travel Preferences", PREFERENCES, default=["history", "food"])
    start_date = st.date_input("Trip Start Date", value=date.today())
    travelers = st.number_input("Travelers", min_value=1, max_value=10, value=2)
    starting_location = st.text_input("Starting Location (Optional)", value="")
    generate = st.button("Generate Itinerary", type="primary")


def get_config_status() -> dict:
    try:
        response = httpx.get(f"{FASTAPI_URL}/config-status", timeout=10.0)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError:
        return {
            "ollama_reachable": False,
            "active_hotel_provider": "unknown",
            "active_maps_provider": "unknown",
            "notes": ["FastAPI backend is not reachable."],
        }


status = get_config_status()
st.info(
    f"Ollama: {'Connected' if status.get('ollama_reachable') else 'Fallback text mode'} | "
    f"Hotel provider: {status.get('active_hotel_provider')} | "
    f"Maps provider: {status.get('active_maps_provider')}"
)
for note in status.get("notes", []):
    st.warning(note)

if generate:
    payload = {
        "destination": destination,
        "budget": budget,
        "days": days,
        "preferences": preferences,
        "start_date": start_date.isoformat() if start_date else None,
        "travelers": travelers,
        "starting_location": starting_location or None,
    }
    try:
        with st.spinner("Generating itinerary..."):
            response = httpx.post(f"{FASTAPI_URL}/plan-trip", json=payload, timeout=90.0)
            response.raise_for_status()
            plan = response.json()
    except httpx.HTTPError as exc:
        st.error(f"Failed to contact backend: {exc}")
        st.stop()

    st.subheader("Recommended Hotel")
    hotel = plan.get("hotel")
    if hotel:
        st.markdown(
            f"""
            **{hotel['name']}**  
            Address: {hotel['address']}  
            Nightly Price: {hotel['nightly_price']}  
            Rating: {hotel.get('rating', 'N/A')}  
            Score: {hotel.get('ranking_score', 'N/A')}  
            Reason: {plan.get('hotel_selection_reason', '')}
            """
        )
    else:
        st.warning("No hotel could be selected. The itinerary was still generated.")

    if plan.get("alternative_hotels"):
        st.subheader("Alternative Hotels")
        for alt in plan["alternative_hotels"]:
            st.write(
                f"{alt['name']} | Nightly: {alt['nightly_price']} | Rating: {alt.get('rating', 'N/A')} | Source: {alt['source']}"
            )

    st.subheader("Trip Summary")
    st.write(plan["summary"])

    st.subheader("Budget Breakdown")
    budget_info = plan["budget_breakdown"]
    cols = st.columns(5)
    cols[0].metric("Lodging", f"{budget_info['lodging_cost']:.2f}")
    cols[1].metric("Transport", f"{budget_info['transport_cost']:.2f}")
    cols[2].metric("Food", f"{budget_info['food_cost']:.2f}")
    cols[3].metric("Misc", f"{budget_info['misc_cost']:.2f}")
    cols[4].metric("Total", f"{budget_info['total_estimated_cost']:.2f}")

    st.subheader("Day-wise Itinerary")
    for day in plan["daily_plans"]:
        with st.expander(f"Day {day['day_number']} - {day['theme']}", expanded=True):
            if day.get("date"):
                st.caption(f"Date: {day['date']}")
            for activity in day["activities"]:
                st.write(
                    f"{activity['time_slot'].title()}: {activity['title']} | "
                    f"Travel: {activity.get('travel_time_from_previous_minutes', 'N/A')} min | "
                    f"Cost: {activity['estimated_cost']}"
                )
                st.caption(activity["description"])
                if activity.get("buffer_note"):
                    st.caption(activity["buffer_note"])
            if day["route_legs"]:
                st.write("Route details:")
                for leg in day["route_legs"]:
                    st.write(
                        f"{leg['origin_name']} -> {leg['destination_name']} | "
                        f"{leg['distance_km']} km | {leg['duration_minutes']} minutes"
                    )
            for warning in day.get("warnings", []):
                st.warning(warning)

    if plan.get("notes"):
        st.subheader("System Notes")
        for note in plan["notes"]:
            st.warning(note)

    json_bytes = response.text.encode("utf-8")
    ics_response = httpx.post(f"{FASTAPI_URL}/export/ics", json=plan, timeout=30.0)
    ics_text = ics_response.text if ics_response.status_code == 200 else ""
    st.download_button("Download JSON", data=json_bytes, file_name="trip_plan.json", mime="application/json")
    st.download_button("Download ICS", data=ics_text.encode("utf-8"), file_name="trip_plan.ics", mime="text/calendar")
