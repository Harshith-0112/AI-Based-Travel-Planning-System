from __future__ import annotations

import copy
from datetime import date
import json

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
HOTEL_PREFERENCES = ["budget", "standard", "luxury"]
TRANSPORT_MODES = ["auto", "flight", "train", "bus", "car"]


st.set_page_config(page_title="AI Travel Planner MCP", layout="wide")
st.title("AI-Based Travel Planning System")
st.caption("Multi-agent itinerary generation with MCP-style tools, Ollama, and graceful fallback providers.")


# -----------------------------
# Session state initialization
# -----------------------------
if "access_token" not in st.session_state:
    st.session_state.access_token = None

if "user" not in st.session_state:
    st.session_state.user = None

if "latest_plan" not in st.session_state:
    st.session_state.latest_plan = None

if "latest_payload" not in st.session_state:
    st.session_state.latest_payload = None

if "latest_response_text" not in st.session_state:
    st.session_state.latest_response_text = None

if "latest_base_summary" not in st.session_state:
    st.session_state.latest_base_summary = None

if "latest_selected_hotel_key" not in st.session_state:
    st.session_state.latest_selected_hotel_key = None

if "latest_hotel_options" not in st.session_state:
    st.session_state.latest_hotel_options = []


# -----------------------------
# Backend helpers
# -----------------------------
def get_auth_headers() -> dict:
    token = st.session_state.access_token
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


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


def signup_user(full_name: str, email: str, password: str) -> tuple[bool, str]:
    try:
        response = httpx.post(
            f"{FASTAPI_URL}/auth/signup",
            json={
                "full_name": full_name,
                "email": email,
                "password": password,
            },
            timeout=15.0,
        )
        if response.status_code == 200:
            return True, "Signup successful. Please log in."
        detail = response.json().get("detail", "Signup failed")
        return False, detail
    except httpx.HTTPError as exc:
        return False, f"Backend error: {exc}"


def login_user(email: str, password: str) -> tuple[bool, str]:
    try:
        # OAuth2PasswordRequestForm expects form data with username/password
        response = httpx.post(
            f"{FASTAPI_URL}/auth/login",
            data={
                "username": email,
                "password": password,
            },
            timeout=15.0,
        )
        if response.status_code != 200:
            detail = response.json().get("detail", "Login failed")
            return False, detail

        token_data = response.json()
        st.session_state.access_token = token_data["access_token"]

        me_response = httpx.get(
            f"{FASTAPI_URL}/auth/me",
            headers=get_auth_headers(),
            timeout=15.0,
        )
        me_response.raise_for_status()
        st.session_state.user = me_response.json()

        return True, "Login successful."
    except httpx.HTTPError as exc:
        return False, f"Backend error: {exc}"


def logout_user():
    st.session_state.access_token = None
    st.session_state.user = None
    st.session_state.latest_plan = None
    st.session_state.latest_payload = None
    st.session_state.latest_base_summary = None
    st.session_state.latest_selected_hotel_key = None
    st.session_state.latest_hotel_options = []


def save_latest_itinerary() -> tuple[bool, str]:
    if not st.session_state.access_token:
        return False, "Please log in first."

    plan = st.session_state.latest_plan
    payload = st.session_state.latest_payload

    if not plan or not payload:
        return False, "No itinerary available to save."

    title = f"{payload['destination']} Trip - {payload['days']} Days"

    preferences_value = payload.get("preferences", [])
    preferences_str = ", ".join(preferences_value) if isinstance(preferences_value, list) else str(preferences_value)

    save_payload = {
        "title": title,
        "destination": payload["destination"],
        "days": payload["days"],
        "budget": payload["budget"],
        "travelers": payload["travelers"],
        "preferences": preferences_str,
        "itinerary_json": json.dumps(plan),
    }

    try:
        response = httpx.post(
            f"{FASTAPI_URL}/itineraries/",
            json=save_payload,
            headers=get_auth_headers(),
            timeout=20.0,
        )
        if response.status_code not in (200, 201):
            detail = response.json().get("detail", "Failed to save itinerary")
            return False, detail
        return True, "Itinerary saved successfully."
    except httpx.HTTPError as exc:
        return False, f"Backend error: {exc}"


def fetch_my_itineraries() -> tuple[bool, list | str]:
    if not st.session_state.access_token:
        return False, "Please log in first."

    try:
        response = httpx.get(
            f"{FASTAPI_URL}/itineraries/",
            headers=get_auth_headers(),
            timeout=20.0,
        )
        if response.status_code != 200:
            detail = response.json().get("detail", "Failed to fetch itineraries")
            return False, detail
        return True, response.json()
    except httpx.HTTPError as exc:
        return False, f"Backend error: {exc}"


def fetch_itinerary_detail(itinerary_id: int) -> tuple[bool, dict | str]:
    try:
        response = httpx.get(
            f"{FASTAPI_URL}/itineraries/{itinerary_id}",
            headers=get_auth_headers(),
            timeout=20.0,
        )
        if response.status_code != 200:
            detail = response.json().get("detail", "Failed to fetch itinerary")
            return False, detail
        return True, response.json()
    except httpx.HTTPError as exc:
        return False, f"Backend error: {exc}"


def delete_itinerary(itinerary_id: int) -> tuple[bool, str]:
    try:
        response = httpx.delete(
            f"{FASTAPI_URL}/itineraries/{itinerary_id}",
            headers=get_auth_headers(),
            timeout=20.0,
        )
        if response.status_code != 200:
            detail = response.json().get("detail", "Failed to delete itinerary")
            return False, detail
        return True, "Itinerary deleted successfully."
    except httpx.HTTPError as exc:
        return False, f"Backend error: {exc}"


def hotel_key(hotel: dict | None) -> str:
    if not hotel:
        return ""
    return f"{hotel.get('name', '')}|{hotel.get('address', '')}"


def hotel_label(hotel: dict) -> str:
    rating = hotel.get("rating", "N/A")
    total = hotel_lodging_cost(hotel, _current_plan_days(), fallback_cost=None)
    total_text = format_price(total)
    return f"{hotel.get('name', 'Hotel')} | Total: {total_text} | Rating: {rating}"


def hotel_lodging_cost(hotel: dict | None, days: int, fallback_cost: float | None = None) -> float | None:
    if not hotel:
        return fallback_cost
    total_price = hotel.get("total_price")
    if total_price:
        return round(float(total_price), 2)
    nightly_price = hotel.get("nightly_price")
    if nightly_price:
        nights = max(days - 1, 1)
        return round(float(nightly_price) * nights, 2)
    return fallback_cost


def format_price(value: float | int | None) -> str:
    if value is None:
        return "Not available"
    return f"₹ {float(value):,.2f}"


def build_user_facing_hotel_reason(hotel: dict | None, trip_request: dict, lodging_cost: float | None) -> str:
    if not hotel:
        return "No hotel could be selected, so the itinerary continues without a lodging recommendation."

    preference = trip_request.get("hotel_preference", "standard")
    budget = float(trip_request.get("budget", 0.0))
    lodging_shares = {"budget": 0.30, "standard": 0.45, "luxury": 0.60}
    lodging_allocation = budget * lodging_shares.get(preference, 0.45)
    nightly = hotel.get("nightly_price")
    rating = hotel.get("rating")
    rating_text = f"a strong {float(rating):.1f} rating" if rating else "limited rating information"

    if lodging_cost is None:
        fit_text = "The hotel price is not available, so the lodging cost is treated as an estimate."
    elif lodging_cost <= lodging_allocation:
        fit_text = "The total stay cost fits within your lodging allocation."
    elif lodging_cost <= lodging_allocation * 1.15:
        fit_text = "The total stay cost is slightly above your lodging allocation but still close."
    else:
        fit_text = "The total stay cost is above your lodging allocation."

    return (
        f"This hotel matches your {preference} preference, has {rating_text}, "
        f"a nightly price of {format_price(nightly)}, and a total stay cost of "
        f"{format_price(lodging_cost)}. {fit_text}"
    )


def _current_plan_days() -> int:
    plan = st.session_state.latest_plan or {}
    trip_request = plan.get("trip_request", {})
    return int(trip_request.get("days") or 1)


def hotel_options(plan: dict) -> list[dict]:
    saved_options = plan.get("_hotel_options") or st.session_state.latest_hotel_options
    if saved_options:
        return saved_options

    options: list[dict] = []
    seen: set[str] = set()
    for hotel in [plan.get("hotel"), *plan.get("alternative_hotels", [])]:
        if not hotel:
            continue
        key = hotel_key(hotel)
        if key and key not in seen:
            options.append(hotel)
            seen.add(key)
    return options


def apply_selected_hotel(plan: dict, selected_hotel: dict, base_summary: str | None) -> dict:
    updated = copy.deepcopy(plan)
    days = int(updated.get("trip_request", {}).get("days") or 1)
    budget_info = copy.deepcopy(updated.get("budget_breakdown", {}))
    fallback_lodging = float(budget_info.get("lodging_cost", 0.0))
    lodging_cost = hotel_lodging_cost(selected_hotel, days, fallback_cost=fallback_lodging)
    lodging_cost = float(lodging_cost or fallback_lodging)

    total = round(
        lodging_cost
        + float(budget_info.get("transport_cost", 0.0))
        + float(budget_info.get("food_cost", 0.0))
        + float(budget_info.get("misc_cost", 0.0)),
        2,
    )
    budget = float(budget_info.get("budget", updated.get("trip_request", {}).get("budget", 0.0)))

    budget_info["lodging_cost"] = round(lodging_cost, 2)
    budget_info["total_estimated_cost"] = total
    budget_info["within_budget"] = total <= budget
    budget_info["over_budget_amount"] = round(max(total - budget, 0.0), 2)
    budget_info["budget_status"] = "within_budget" if total <= budget else "over_budget"
    budget_info["budget_warning"] = (
        None
        if total <= budget
        else f"This plan exceeds your budget by {format_price(budget_info['over_budget_amount'])}."
    )

    updated["hotel"] = selected_hotel
    updated["_hotel_options"] = plan.get("_hotel_options") or st.session_state.latest_hotel_options
    updated["budget_breakdown"] = budget_info
    updated["hotel_selection_reason"] = build_user_facing_hotel_reason(
        selected_hotel,
        updated.get("trip_request", {}),
        lodging_cost,
    )

    summary_body = base_summary or updated.get("summary", "")
    hotel_name = selected_hotel.get("name", "the selected hotel")
    if summary_body.lower().startswith("selected hotel:"):
        summary_body = summary_body.split(".", 1)[-1].strip()
    updated["summary"] = f"Selected hotel: {hotel_name}. {summary_body}"
    return updated


def render_plan(plan: dict, response_text: str):
    options = hotel_options(plan)
    if options:
        option_map = {hotel_key(option): option for option in options}
        option_keys = list(option_map)
        current_key = st.session_state.latest_selected_hotel_key or hotel_key(plan.get("hotel"))
        selected_index = option_keys.index(current_key) if current_key in option_keys else 0
        selected_key = st.selectbox(
            "Choose Hotel",
            option_keys,
            index=selected_index,
            format_func=lambda key: hotel_label(option_map[key]),
            key=f"hotel_selector_{plan.get('generated_at', 'current')}",
        )
        selected_hotel = option_map[selected_key]
        st.session_state.latest_selected_hotel_key = selected_key
        plan = apply_selected_hotel(plan, selected_hotel, st.session_state.latest_base_summary)
        st.session_state.latest_hotel_options = options
        st.session_state.latest_plan = plan

    st.subheader("Selected Hotel")
    hotel = plan.get("hotel")

    if hotel:
        days = int(plan.get("trip_request", {}).get("days") or 1)
        hotel_price = format_price(hotel.get("nightly_price"))
        total_lodging = format_price(hotel_lodging_cost(hotel, days, fallback_cost=None))

        st.markdown(
            f"""
            **{hotel['name']}**  
            Address: {hotel['address']}  
            Nightly Price: {hotel_price}  
            Total Lodging Cost: {total_lodging}  
            Rating: {hotel.get('rating', 'N/A')}  
            Reason: {plan.get('hotel_selection_reason', '')}
            """
        )
    else:
        st.warning("No hotel could be selected. The itinerary was still generated.")

    st.subheader("Trip Summary")
    st.write(plan["summary"])

    attractions = plan.get("attractions", [])
    attraction_sources = {item.get("source") for item in attractions}
    verification_sources = {item.get("verification_source") for item in attractions}
    if not attractions:
        st.warning(
            "Unable to verify attractions for this destination right now. "
            "Please enable Maps API or try a more specific destination."
        )
    elif "verified_ai" in attraction_sources and "openstreetmap" in verification_sources:
        st.info("Places were generated using AI and verified near your destination using OpenStreetMap.")
    elif "verified_ai" in attraction_sources:
        st.info("Places were generated using AI and verified near your destination.")
    elif "openstreetmap" in attraction_sources:
        st.info("Places loaded from OpenStreetMap fallback data.")
    elif "verified_cache" in attraction_sources:
        st.info("Places loaded from verified cache.")
    elif "fallback_cache" in attraction_sources:
        st.info("Places loaded from offline fallback data.")

    st.subheader("Budget Breakdown")
    budget_info = plan["budget_breakdown"]
    if budget_info.get("budget_warning"):
        if budget_info.get("within_budget"):
            st.success(budget_info["budget_warning"])
        else:
            st.warning(budget_info["budget_warning"])

    budget_delta = float(budget_info["budget"]) - float(budget_info["total_estimated_cost"])
    if budget_delta >= 0:
        st.success(f"Remaining budget: {format_price(budget_delta)}")
    else:
        st.warning(f"This plan exceeds your budget by {format_price(abs(budget_delta))}.")

    cols = st.columns(6)
    cols[0].metric("Budget", format_price(budget_info["budget"]))
    cols[1].metric("Lodging", format_price(budget_info["lodging_cost"]))
    cols[2].metric("Transport", format_price(budget_info["transport_cost"]))
    cols[3].metric("Food", format_price(budget_info["food_cost"]))
    cols[4].metric("Misc", format_price(budget_info["misc_cost"]))
    cols[5].metric("Estimated Total", format_price(budget_info["total_estimated_cost"]))

    if plan.get("transport"):
        transport = plan["transport"]
        st.subheader("Transport Estimate")
        st.write(
            f"{transport['mode'].title()} | Cost: {transport['estimated_cost']:.2f} | "
            f"Duration: {transport['estimated_duration_hours']:.1f} hours | {transport['reason']}"
        )

    st.subheader("Day-wise Itinerary")
    for day in plan["daily_plans"]:
        with st.expander(f"Day {day['day_number']} - {day['theme']}", expanded=True):
            if day.get("date"):
                st.caption(f"Date: {day['date']}")

            for activity in day["activities"]:
                cost_label = (
                    "Estimated activity cost"
                    if activity.get("cost_source") == "estimated"
                    else "Activity cost"
                )
                st.write(
                    f"{activity['time_slot'].title()}: {activity['title']} | "
                    f"Travel: {activity.get('travel_time_from_previous_minutes', 'N/A')} min | "
                    f"{cost_label}: {format_price(activity['estimated_cost'])}"
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

    st.subheader("Downloads")
    response_text = json.dumps(plan, indent=2)
    json_bytes = response_text.encode("utf-8")

    try:
        ics_response = httpx.post(
            f"{FASTAPI_URL}/export/ics",
            json=plan,
            headers=get_auth_headers(),
            timeout=30.0,
        )
        ics_text = ics_response.text if ics_response.status_code == 200 else ""
    except httpx.HTTPError:
        ics_text = ""

    st.download_button(
        "Download JSON",
        data=json_bytes,
        file_name="trip_plan.json",
        mime="application/json",
    )

    st.download_button(
        "Download ICS",
        data=ics_text.encode("utf-8"),
        file_name="trip_plan.ics",
        mime="text/calendar",
    )


# -----------------------------
# Auth sidebar
# -----------------------------
with st.sidebar:
    st.subheader("Account")

    if st.session_state.user:
        st.success(f"Logged in as {st.session_state.user['full_name']}")
        st.caption(st.session_state.user["email"])
        if st.button("Logout"):
            logout_user()
            st.rerun()
    else:
        auth_tab = st.radio("Choose action", ["Login", "Sign Up"], horizontal=True)

        if auth_tab == "Login":
            login_email = st.text_input("Email", key="login_email")
            login_password = st.text_input("Password", type="password", key="login_password")
            if st.button("Login", use_container_width=True):
                ok, message = login_user(login_email, login_password)
                if ok:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

        else:
            signup_name = st.text_input("Full Name", key="signup_name")
            signup_email = st.text_input("Email Address", key="signup_email")
            signup_password = st.text_input("Create Password", type="password", key="signup_password")
            if st.button("Create Account", use_container_width=True):
                ok, message = signup_user(signup_name, signup_email, signup_password)
                if ok:
                    st.success(message)
                else:
                    st.error(message)

    st.divider()
    st.subheader("Trip Inputs")
    destination = st.text_input("Destination", value="Mysore")
    budget = st.number_input("Total Budget", min_value=1000.0, value=15000.0, step=500.0)
    days = st.slider("Number of Days", min_value=1, max_value=7, value=3)
    preferences = st.multiselect("Travel Preferences", PREFERENCES, default=["history", "food"])
    hotel_preference = st.selectbox("Hotel Preference", HOTEL_PREFERENCES, index=1)
    transport_mode = st.selectbox("Transport Mode", TRANSPORT_MODES, index=0)
    start_date = st.date_input("Trip Start Date", value=date.today())
    travelers = st.number_input("Travelers", min_value=1, max_value=10, value=2)
    starting_location = st.text_input("Starting Location (Optional)", value="")
    generate = st.button("Generate Itinerary", type="primary", use_container_width=True)


# -----------------------------
# Main tabs
# -----------------------------
tab_plan, tab_saved = st.tabs(["Plan Trip", "My Saved Trips"])


with tab_plan:
    if generate:
        payload = {
            "destination": destination,
            "budget": budget,
            "days": days,
            "preferences": preferences,
            "start_date": start_date.isoformat() if start_date else None,
            "travelers": travelers,
            "starting_location": starting_location or None,
            "hotel_preference": hotel_preference,
            "transport_mode": transport_mode,
        }

        try:
            with st.spinner("Generating itinerary..."):
                response = httpx.post(
                f"{FASTAPI_URL}/plan-trip",
                json=payload,
                headers=get_auth_headers(),
                timeout=180.0,
                )
                response.raise_for_status()
                plan = response.json()

            st.session_state.latest_plan = plan
            st.session_state.latest_payload = payload
            st.session_state.latest_response_text = response.text
            st.session_state.latest_base_summary = plan.get("summary")
            st.session_state.latest_selected_hotel_key = hotel_key(plan.get("hotel"))
            st.session_state.latest_hotel_options = []
            st.session_state.latest_hotel_options = hotel_options(plan)
            st.session_state.latest_plan["_hotel_options"] = st.session_state.latest_hotel_options

        except httpx.HTTPError as exc:
            st.error(f"Failed to contact backend: {exc}")
            st.stop()

    if st.session_state.latest_plan:
        render_plan(
            st.session_state.latest_plan,
            st.session_state.get("latest_response_text", json.dumps(st.session_state.latest_plan)),
        )

        if st.session_state.user:
            if st.button("Save This Itinerary", type="primary"):
                ok, message = save_latest_itinerary()
                if ok:
                    st.success(message)
                else:
                    st.error(message)
        else:
            st.info("Log in to save this itinerary.")


with tab_saved:
    if not st.session_state.user:
        st.info("Please log in to view your saved itineraries.")
    else:
        if st.button("Refresh My Trips"):
            st.rerun()

        ok, result = fetch_my_itineraries()
        if not ok:
            st.error(result)
        else:
            itineraries = result
            if not itineraries:
                st.info("No saved itineraries yet.")
            else:
                for item in itineraries:
                    with st.expander(f"{item['title']} | {item['destination']}"):
                        st.write(f"Days: {item['days']}")
                        st.write(f"Budget: {item['budget']}")
                        st.write(f"Created At: {item['created_at']}")

                        col1, col2 = st.columns(2)

                        with col1:
                            if st.button("View Details", key=f"view_{item['id']}"):
                                ok_detail, detail_result = fetch_itinerary_detail(item["id"])
                                if ok_detail:
                                    try:
                                        saved_plan = json.loads(detail_result["itinerary_json"])
                                        st.session_state.latest_plan = saved_plan
                                        st.session_state.latest_response_text = json.dumps(saved_plan, indent=2)
                                        st.session_state.latest_base_summary = saved_plan.get("summary")
                                        st.session_state.latest_selected_hotel_key = hotel_key(saved_plan.get("hotel"))
                                        st.session_state.latest_hotel_options = []
                                        st.session_state.latest_hotel_options = hotel_options(saved_plan)
                                        st.session_state.latest_payload = {
                                            "destination": detail_result["destination"],
                                            "days": detail_result["days"],
                                            "budget": detail_result["budget"],
                                            "travelers": detail_result["travelers"],
                                            "preferences": detail_result.get("preferences", ""),
                                        }
                                        st.success("Loaded itinerary into Plan Trip tab.")
                                    except json.JSONDecodeError:
                                        st.error("Could not decode saved itinerary JSON.")
                                else:
                                    st.error(detail_result)

                        with col2:
                            if st.button("Delete", key=f"delete_{item['id']}"):
                                ok_delete, delete_message = delete_itinerary(item["id"])
                                if ok_delete:
                                    st.success(delete_message)
                                    st.rerun()
                                else:
                                    st.error(delete_message)
