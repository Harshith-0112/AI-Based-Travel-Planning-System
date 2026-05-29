from __future__ import annotations

from datetime import date
from typing import Any
from urllib.parse import quote_plus

import httpx
import pandas as pd
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


st.set_page_config(
    page_title="AI Travel Planner MCP",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)


if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "Dark"


def inject_theme_css(theme_mode: str) -> None:
    if theme_mode == "Light":
        css = """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(99,102,241,0.20), transparent 28%),
                radial-gradient(circle at top right, rgba(56,189,248,0.18), transparent 24%),
                linear-gradient(135deg, #eef4ff 0%, #f7faff 48%, #edf2ff 100%);
            color: #0f172a;
        }

        .main > div {
            padding-top: 1.2rem;
        }

        [data-testid="stSidebar"] {
            background: rgba(255, 255, 255, 0.64);
            border-right: 1px solid rgba(15, 23, 42, 0.08);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
        }

        [data-testid="stSidebar"] * {
            color: #0f172a !important;
        }

        .hero {
            position: relative;
            overflow: hidden;
            padding: 2.2rem 2rem 1.6rem 2rem;
            border-radius: 28px;
            background: linear-gradient(135deg, rgba(255,255,255,0.78), rgba(255,255,255,0.48));
            border: 1px solid rgba(15,23,42,0.08);
            backdrop-filter: blur(22px);
            -webkit-backdrop-filter: blur(22px);
            box-shadow: 0 20px 70px rgba(15, 23, 42, 0.08);
            margin-bottom: 1.25rem;
            animation: fadeUp 0.8s ease-out;
        }

        .hero:before {
            content: "";
            position: absolute;
            inset: -20% auto auto -10%;
            width: 240px;
            height: 240px;
            background: radial-gradient(circle, rgba(59,130,246,0.22), transparent 65%);
            filter: blur(10px);
        }

        .hero:after {
            content: "";
            position: absolute;
            right: -40px;
            top: -30px;
            width: 180px;
            height: 180px;
            background: radial-gradient(circle, rgba(168,85,247,0.18), transparent 68%);
            filter: blur(8px);
        }

        .hero-badge, .status-pill, .pref-chip, .route-chip, .activity-chip {
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
        }

        .hero-badge {
            display: inline-block;
            padding: 0.45rem 0.8rem;
            border-radius: 999px;
            background: rgba(15,23,42,0.05);
            border: 1px solid rgba(15,23,42,0.08);
            color: #1e3a8a;
            font-size: 0.85rem;
            font-weight: 600;
            letter-spacing: 0.02em;
            margin-bottom: 0.85rem;
        }

        .hero h1, .section-title, .hotel-title, .activity-title, .banner-title {
            color: #0f172a;
        }

        .hero h1 {
            margin: 0;
            font-size: 2.6rem;
            line-height: 1.05;
            font-weight: 800;
            letter-spacing: -0.03em;
        }

        .hero p, .muted, .banner-subtitle {
            color: #334155;
        }

        .glass-card, .hotel-card, .timeline-card, .activity-row, .alt-hotel, .banner-card, .skeleton-card {
            background: linear-gradient(135deg, rgba(255,255,255,0.74), rgba(255,255,255,0.46));
            border: 1px solid rgba(15,23,42,0.08);
            box-shadow: 0 12px 40px rgba(15,23,42,0.06);
        }

        .glass-card, .banner-card {
            border-radius: 24px;
            padding: 1.2rem;
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
            animation: fadeUp 0.7s ease-out;
        }

        .section-title {
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 0.9rem;
            letter-spacing: -0.02em;
        }

        .mini-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.9rem;
            margin-top: 0.9rem;
        }

        .mini-stat {
            background: rgba(255,255,255,0.55);
            border: 1px solid rgba(15,23,42,0.08);
            border-radius: 20px;
            padding: 1rem;
            transition: transform 0.25s ease, box-shadow 0.25s ease, background 0.25s ease;
        }

        .mini-stat:hover {
            transform: translateY(-3px);
            box-shadow: 0 18px 34px rgba(15,23,42,0.08);
            background: rgba(255,255,255,0.74);
        }

        .mini-label {
            color: #475569;
            font-size: 0.84rem;
            margin-bottom: 0.35rem;
        }

        .mini-value {
            color: #0f172a;
            font-size: 1.15rem;
            font-weight: 700;
        }

        .hotel-card {
            border-radius: 24px;
            padding: 1.3rem;
        }

        .hotel-title {
            font-size: 1.35rem;
            font-weight: 800;
            margin-bottom: 0.45rem;
            letter-spacing: -0.02em;
        }

        .muted {
            line-height: 1.7;
        }

        .alt-hotel {
            border-radius: 18px;
            padding: 0.95rem 1rem;
            margin-bottom: 0.7rem;
        }

        .timeline-card {
            border-radius: 24px;
            padding: 1rem 1.1rem;
            margin-bottom: 1rem;
        }

        .activity-row {
            border-radius: 18px;
            padding: 0.9rem 1rem;
            margin-top: 0.75rem;
        }

        .activity-title {
            font-weight: 700;
        }

        .route-chip, .pref-chip, .activity-chip {
            display: inline-block;
            margin: 0.35rem 0.35rem 0 0;
            padding: 0.45rem 0.7rem;
            border-radius: 999px;
            background: rgba(15,23,42,0.05);
            border: 1px solid rgba(15,23,42,0.08);
            color: #1e293b;
            font-size: 0.84rem;
        }

        .status-pill {
            display: inline-block;
            padding: 0.4rem 0.72rem;
            border-radius: 999px;
            background: rgba(34,197,94,0.12);
            border: 1px solid rgba(34,197,94,0.20);
            color: #166534;
            font-size: 0.82rem;
            font-weight: 600;
            margin-top: 0.35rem;
        }

        .banner-card {
            position: relative;
            overflow: hidden;
            min-height: 260px;
            display: flex;
            align-items: end;
            padding: 0;
            margin-bottom: 1rem;
        }

        .banner-image {
            width: 100%;
            height: 260px;
            object-fit: cover;
            display: block;
        }

        .banner-overlay {
            position: absolute;
            inset: 0;
            background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.08), rgba(255,255,255,0.68));
            display: flex;
            align-items: end;
            padding: 1.2rem;
        }

        .banner-title {
            font-size: 1.7rem;
            font-weight: 800;
            margin: 0;
        }

        .banner-subtitle {
            margin: 0.35rem 0 0 0;
            font-size: 0.96rem;
        }

        .skeleton-card {
            position: relative;
            overflow: hidden;
            border-radius: 20px;
            height: 92px;
            margin-bottom: 0.85rem;
        }

        .skeleton-card::after {
            content: "";
            position: absolute;
            top: 0;
            left: -150px;
            width: 120px;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.6), transparent);
            animation: shimmer 1.2s infinite;
        }

        .stButton > button {
            width: 100%;
            border: 0;
            border-radius: 16px;
            padding: 0.85rem 1rem;
            font-weight: 700;
            color: white;
            background: linear-gradient(135deg, #2563eb, #7c3aed);
            box-shadow: 0 16px 32px rgba(37,99,235,0.20);
            transition: all 0.25s ease;
        }

        .stButton > button:hover, .stDownloadButton > button:hover {
            transform: translateY(-2px);
        }

        .stDownloadButton > button {
            border-radius: 14px;
            border: 1px solid rgba(15,23,42,0.10);
            background: rgba(255,255,255,0.55);
            color: #0f172a;
            transition: all 0.25s ease;
        }

        div[data-testid="metric-container"] {
            background: linear-gradient(135deg, rgba(255,255,255,0.70), rgba(255,255,255,0.48));
            border: 1px solid rgba(15,23,42,0.08);
            padding: 1rem;
            border-radius: 22px;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            box-shadow: 0 10px 30px rgba(15,23,42,0.06);
        }

        div[data-testid="metric-container"] label,
        div[data-testid="metric-container"] div {
            color: #0f172a !important;
        }

        .stAlert {
            border-radius: 18px;
            border: 1px solid rgba(15,23,42,0.08);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
        }

        [data-testid="stExpander"] {
            background: rgba(255,255,255,0.42);
            border: 1px solid rgba(15,23,42,0.08);
            border-radius: 20px;
            overflow: hidden;
        }

        @keyframes fadeUp {
            from { opacity: 0; transform: translateY(14px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes shimmer {
            0% { transform: translateX(0); }
            100% { transform: translateX(620px); }
        }

        @media (max-width: 1100px) {
            .mini-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
            .hero h1 { font-size: 2rem; }
        }
        </style>
        """
    else:
        css = """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(99,102,241,0.30), transparent 28%),
                radial-gradient(circle at top right, rgba(56,189,248,0.22), transparent 24%),
                radial-gradient(circle at bottom left, rgba(168,85,247,0.18), transparent 22%),
                linear-gradient(135deg, #07111f 0%, #0b1220 45%, #111827 100%);
            color: #e5eefc;
        }

        .main > div {
            padding-top: 1.2rem;
        }

        [data-testid="stSidebar"] {
            background: rgba(10, 18, 32, 0.62);
            border-right: 1px solid rgba(255,255,255,0.10);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
        }

        [data-testid="stSidebar"] * {
            color: #eaf2ff !important;
        }

        .hero {
            position: relative;
            overflow: hidden;
            padding: 2.2rem 2rem 1.6rem 2rem;
            border-radius: 28px;
            background: linear-gradient(135deg, rgba(255,255,255,0.15), rgba(255,255,255,0.06));
            border: 1px solid rgba(255,255,255,0.14);
            backdrop-filter: blur(22px);
            -webkit-backdrop-filter: blur(22px);
            box-shadow: 0 20px 70px rgba(0, 0, 0, 0.28);
            margin-bottom: 1.25rem;
            animation: fadeUp 0.8s ease-out;
        }

        .hero:before {
            content: "";
            position: absolute;
            inset: -20% auto auto -10%;
            width: 240px;
            height: 240px;
            background: radial-gradient(circle, rgba(59,130,246,0.35), transparent 65%);
            filter: blur(10px);
        }

        .hero:after {
            content: "";
            position: absolute;
            right: -40px;
            top: -30px;
            width: 180px;
            height: 180px;
            background: radial-gradient(circle, rgba(168,85,247,0.28), transparent 68%);
            filter: blur(8px);
        }

        .hero-badge {
            display: inline-block;
            padding: 0.45rem 0.8rem;
            border-radius: 999px;
            background: rgba(255,255,255,0.10);
            border: 1px solid rgba(255,255,255,0.14);
            color: #dbeafe;
            font-size: 0.85rem;
            font-weight: 600;
            letter-spacing: 0.02em;
            margin-bottom: 0.85rem;
        }

        .hero h1 {
            margin: 0;
            font-size: 2.6rem;
            line-height: 1.05;
            font-weight: 800;
            letter-spacing: -0.03em;
            color: #f8fbff;
        }

        .hero p {
            margin: 0.85rem 0 0 0;
            max-width: 820px;
            color: #cdd9ee;
            font-size: 1rem;
            line-height: 1.75;
        }

        .glass-card {
            background: linear-gradient(135deg, rgba(255,255,255,0.12), rgba(255,255,255,0.05));
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 24px;
            padding: 1.2rem;
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
            box-shadow: 0 12px 40px rgba(0,0,0,0.18);
            animation: fadeUp 0.7s ease-out;
        }

        .section-title {
            font-size: 1.1rem;
            font-weight: 700;
            color: #f5f9ff;
            margin-bottom: 0.9rem;
            letter-spacing: -0.02em;
        }

        .mini-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.9rem;
            margin-top: 0.9rem;
        }

        .mini-stat {
            background: rgba(255,255,255,0.07);
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 20px;
            padding: 1rem;
            transition: transform 0.25s ease, box-shadow 0.25s ease, background 0.25s ease;
        }

        .mini-stat:hover {
            transform: translateY(-3px);
            box-shadow: 0 18px 34px rgba(0,0,0,0.20);
            background: rgba(255,255,255,0.10);
        }

        .mini-label {
            color: #b8c7e0;
            font-size: 0.84rem;
            margin-bottom: 0.35rem;
        }

        .mini-value {
            color: #ffffff;
            font-size: 1.15rem;
            font-weight: 700;
        }

        .hotel-card {
            background: linear-gradient(135deg, rgba(59,130,246,0.18), rgba(255,255,255,0.06));
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 24px;
            padding: 1.3rem;
            box-shadow: 0 12px 32px rgba(0,0,0,0.18);
        }

        .hotel-title {
            font-size: 1.35rem;
            font-weight: 800;
            color: #ffffff;
            margin-bottom: 0.45rem;
            letter-spacing: -0.02em;
        }

        .muted {
            color: #c7d5ea;
            line-height: 1.7;
        }

        .alt-hotel {
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 18px;
            padding: 0.95rem 1rem;
            margin-bottom: 0.7rem;
        }

        .timeline-card {
            background: linear-gradient(135deg, rgba(255,255,255,0.09), rgba(255,255,255,0.04));
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 24px;
            padding: 1rem 1.1rem;
            margin-bottom: 1rem;
        }

        .activity-row {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 18px;
            padding: 0.9rem 1rem;
            margin-top: 0.75rem;
        }

        .activity-title {
            font-weight: 700;
            color: #f8fbff;
        }

        .route-chip, .pref-chip, .activity-chip {
            display: inline-block;
            margin: 0.35rem 0.35rem 0 0;
            padding: 0.45rem 0.7rem;
            border-radius: 999px;
            background: rgba(148,163,184,0.16);
            border: 1px solid rgba(255,255,255,0.08);
            color: #dbe7f7;
            font-size: 0.84rem;
        }

        .status-pill {
            display: inline-block;
            padding: 0.4rem 0.72rem;
            border-radius: 999px;
            background: rgba(34,197,94,0.14);
            border: 1px solid rgba(34,197,94,0.28);
            color: #d1fae5;
            font-size: 0.82rem;
            font-weight: 600;
            margin-top: 0.35rem;
        }

        .banner-card {
            position: relative;
            overflow: hidden;
            min-height: 260px;
            display: flex;
            align-items: end;
            padding: 0;
            border-radius: 24px;
            border: 1px solid rgba(255,255,255,0.12);
            background: linear-gradient(135deg, rgba(255,255,255,0.12), rgba(255,255,255,0.05));
            box-shadow: 0 12px 40px rgba(0,0,0,0.18);
            margin-bottom: 1rem;
        }

        .banner-image {
            width: 100%;
            height: 260px;
            object-fit: cover;
            display: block;
        }

        .banner-overlay {
            position: absolute;
            inset: 0;
            background: linear-gradient(180deg, rgba(2,6,23,0.06), rgba(2,6,23,0.18), rgba(2,6,23,0.72));
            display: flex;
            align-items: end;
            padding: 1.2rem;
        }

        .banner-title {
            color: #f8fbff;
            font-size: 1.7rem;
            font-weight: 800;
            margin: 0;
        }

        .banner-subtitle {
            margin: 0.35rem 0 0 0;
            font-size: 0.96rem;
            color: #dbeafe;
        }

        .skeleton-card {
            position: relative;
            overflow: hidden;
            background: linear-gradient(135deg, rgba(255,255,255,0.12), rgba(255,255,255,0.05));
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 20px;
            height: 92px;
            margin-bottom: 0.85rem;
        }

        .skeleton-card::after {
            content: "";
            position: absolute;
            top: 0;
            left: -150px;
            width: 120px;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.28), transparent);
            animation: shimmer 1.2s infinite;
        }

        .stButton > button {
            width: 100%;
            border: 0;
            border-radius: 16px;
            padding: 0.85rem 1rem;
            font-weight: 700;
            color: white;
            background: linear-gradient(135deg, #2563eb, #7c3aed);
            box-shadow: 0 16px 32px rgba(37,99,235,0.28);
            transition: all 0.25s ease;
        }

        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 22px 40px rgba(37,99,235,0.34);
        }

        .stDownloadButton > button {
            border-radius: 14px;
            border: 1px solid rgba(255,255,255,0.12);
            background: rgba(255,255,255,0.08);
            color: #f8fbff;
            transition: all 0.25s ease;
        }

        .stDownloadButton > button:hover {
            transform: translateY(-2px);
            background: rgba(255,255,255,0.12);
        }

        div[data-testid="metric-container"] {
            background: linear-gradient(135deg, rgba(255,255,255,0.11), rgba(255,255,255,0.05));
            border: 1px solid rgba(255,255,255,0.10);
            padding: 1rem;
            border-radius: 22px;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.14);
        }

        div[data-testid="metric-container"] label,
        div[data-testid="metric-container"] div {
            color: #e5eefc !important;
        }

        .stAlert {
            border-radius: 18px;
            border: 1px solid rgba(255,255,255,0.10);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
        }

        [data-testid="stExpander"] {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 20px;
            overflow: hidden;
        }

        @keyframes fadeUp {
            from { opacity: 0; transform: translateY(14px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes shimmer {
            0% { transform: translateX(0); }
            100% { transform: translateX(620px); }
        }

        @media (max-width: 1100px) {
            .mini-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
            .hero h1 { font-size: 2rem; }
        }
        </style>
        """
    st.markdown(css, unsafe_allow_html=True)


inject_theme_css(st.session_state.theme_mode)


st.markdown(
    """
    <div class="hero">
        <div class="hero-badge">AI Travel Experience • Premium Planner</div>
        <h1>Plan beautiful trips with a modern glassmorphism dashboard</h1>
        <p>
            Generate itinerary ideas, hotel recommendations, route details, budget insights,
            and downloadable trip exports through a polished, animated travel cockpit.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


with st.sidebar:
    st.markdown("### ✨ Trip Inputs")
    destination = st.text_input("Destination", value="Mysore", placeholder="Where do you want to go?")
    budget = st.number_input("Total Budget", min_value=1000.0, value=15000.0, step=500.0)
    days = st.slider("Number of Days", min_value=1, max_value=10, value=3)
    preferences = st.multiselect("Travel Preferences", PREFERENCES, default=["history", "food"])
    start_date = st.date_input("Trip Start Date", value=date.today())
    travelers = st.number_input("Travelers", min_value=1, max_value=10, value=2)
    starting_location = st.text_input("Starting Location (Optional)", value="", placeholder="e.g. Hyderabad")
    theme_mode = st.segmented_control("Theme", options=["Dark", "Light"], default=st.session_state.theme_mode)
    st.session_state.theme_mode = theme_mode
    st.markdown("---")
    generate = st.button("Generate Premium Itinerary", type="primary")


if st.session_state.theme_mode != theme_mode:
    st.session_state.theme_mode = theme_mode
    st.rerun()


def get_config_status() -> dict[str, Any]:
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


def render_destination_banner(place: str, pref_list: list[str]) -> None:
    clean_place = place.strip() or "Travel Destination"
    image_url = f"https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1400&q=80&{quote_plus(clean_place)}"
    pref_html = "".join([f"<span class='pref-chip'>{p.title()}</span>" for p in pref_list[:6]]) or "<span class='pref-chip'>Flexible Trip</span>"
    st.markdown(
        f"""
        <div class="banner-card">
            <img class="banner-image" src="{image_url}" alt="{clean_place}">
            <div class="banner-overlay">
                <div>
                    <h2 class="banner-title">{clean_place}</h2>
                    <p class="banner-subtitle">Curated itinerary for {days} day(s), {travelers} traveler(s), and a premium planning experience.</p>
                    {pref_html}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


render_destination_banner(destination, preferences)

col_a, col_b, col_c = st.columns([1.15, 1, 1])
with col_a:
    st.markdown(
        f"""
        <div class="glass-card">
            <div class="section-title">Trip Setup</div>
            <div class="mini-grid">
                <div class="mini-stat">
                    <div class="mini-label">Destination</div>
                    <div class="mini-value">{destination}</div>
                </div>
                <div class="mini-stat">
                    <div class="mini-label">Budget</div>
                    <div class="mini-value">₹ {budget:,.0f}</div>
                </div>
                <div class="mini-stat">
                    <div class="mini-label">Travelers</div>
                    <div class="mini-value">{travelers}</div>
                </div>
                <div class="mini-stat">
                    <div class="mini-label">Trip Length</div>
                    <div class="mini-value">{days} days</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col_b:
    st.markdown(
        f"""
        <div class="glass-card">
            <div class="section-title">Budget Snapshot</div>
            <div class="mini-grid" style="grid-template-columns: repeat(2, minmax(0, 1fr));">
                <div class="mini-stat">
                    <div class="mini-label">Budget</div>
                    <div class="mini-value">₹ {budget:,.0f}</div>
                </div>
                <div class="mini-stat">
                    <div class="mini-label">Travelers</div>
                    <div class="mini-value">{travelers}</div>
                </div>
                <div class="mini-stat">
                    <div class="mini-label">Start Date</div>
                    <div class="mini-value">{start_date}</div>
                </div>
                <div class="mini-stat">
                    <div class="mini-label">Theme</div>
                    <div class="mini-value">{st.session_state.theme_mode}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col_c:
    pref_text = ", ".join(preferences[:3]) if preferences else "Flexible"
    st.markdown(
        f"""
        <div class="glass-card">
            <div class="section-title">Preference Focus</div>
            <p class="muted" style="margin:0;">
                Tailoring recommendations around <strong style="color:inherit;">{pref_text}</strong>
                with balanced cost, route-aware planning, and downloadable trip outputs.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
loading_placeholder = st.empty()


def show_loading_skeleton() -> None:
    loading_placeholder.markdown(
        """
        <div class="glass-card" style="margin-top:1rem;">
            <div class="section-title">Generating your itinerary</div>
            <div class="skeleton-card"></div>
            <div class="skeleton-card"></div>
            <div class="skeleton-card"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
        show_loading_skeleton()
        with st.spinner("Crafting your itinerary..."):
            response = httpx.post(f"{FASTAPI_URL}/plan-trip", json=payload, timeout=90.0)
            response.raise_for_status()
            plan = response.json()
        loading_placeholder.empty()
    except httpx.HTTPError as exc:
        loading_placeholder.empty()
        st.error(f"Failed to contact backend: {exc}")
        st.stop()

    st.markdown("<div class='section-title' style='margin-top:1.2rem;'>🏨 Recommended Stay</div>", unsafe_allow_html=True)
    hotel = plan.get("hotel")
    if hotel:
        st.markdown(
            f"""
            <div class="hotel-card">
                <div class="hotel-title">{hotel['name']}</div>
                <div class="muted">
                    <strong>Address:</strong> {hotel['address']}<br>
                    <strong>Nightly Price:</strong> ₹ {hotel['nightly_price']}<br>
                    <strong>Rating:</strong> {hotel.get('rating', 'N/A')}<br>
                    <strong>Why this hotel?</strong><br>
                    {plan.get('hotel_selection_reason', '')}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.warning("No hotel could be selected. The itinerary was still generated.")

    if plan.get("alternative_hotels"):
        st.markdown("<div class='section-title' style='margin-top:1rem;'>Other Options</div>", unsafe_allow_html=True)
        for alt in plan["alternative_hotels"]:
            st.markdown(
                f"""
                <div class="alt-hotel">
                    <strong>{alt['name']}</strong><br>
                    Nightly: ₹ {alt['nightly_price']} &nbsp;&nbsp;•&nbsp;&nbsp;
                    Rating: {alt.get('rating', 'N/A')} &nbsp;&nbsp;•&nbsp;&nbsp;
                    Source: {alt['source']}
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div class='section-title' style='margin-top:1rem;'>🧭 Trip Summary</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='glass-card'><div class='muted'>{plan['summary']}</div></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title' style='margin-top:1rem;'>💸 Budget Breakdown</div>", unsafe_allow_html=True)
    budget_info = plan["budget_breakdown"]
    if budget_info.get("budget_warning"):
        if budget_info.get("within_budget"):
            st.success(budget_info["budget_warning"])
        else:
            st.warning(budget_info["budget_warning"])
    budget_delta = budget_info["budget"] - budget_info["total_estimated_cost"]
    if budget_delta >= 0:
        st.success(f"Remaining budget: ₹ {budget_delta:,.2f}")
    else:
        st.warning(f"This plan exceeds your budget by ₹ {abs(budget_delta):,.2f}.")

    cols = st.columns(6)
    cols[0].metric("Budget", f"₹ {budget_info['budget']:.2f}")
    cols[1].metric("Lodging", f"₹ {budget_info['lodging_cost']:.2f}")
    cols[2].metric("Transport", f"₹ {budget_info['transport_cost']:.2f}")
    cols[3].metric("Food", f"₹ {budget_info['food_cost']:.2f}")
    cols[4].metric("Misc", f"₹ {budget_info['misc_cost']:.2f}")
    cols[5].metric("Estimated Total", f"₹ {budget_info['total_estimated_cost']:.2f}")

    chart_df = pd.DataFrame(
        {
            "Category": ["Lodging", "Transport", "Food", "Misc"],
            "Cost": [
                budget_info["lodging_cost"],
                budget_info["transport_cost"],
                budget_info["food_cost"],
                budget_info["misc_cost"],
            ],
        }
    ).set_index("Category")
    st.bar_chart(chart_df)

    st.markdown("<div class='section-title' style='margin-top:1rem;'>🗓 Day-wise Itinerary</div>", unsafe_allow_html=True)
    for day in plan["daily_plans"]:
        with st.expander(f"Day {day['day_number']} • {day['theme']}", expanded=True):
            activity_tags = []
            for activity in day.get("activities", []):
                time_slot = activity.get("time_slot", "activity")
                if time_slot and time_slot.title() not in activity_tags:
                    activity_tags.append(time_slot.title())
            tags_html = "".join([f"<span class='activity-chip'>{tag}</span>" for tag in activity_tags])
            st.markdown(
                f"""
                <div class="timeline-card">
                    <div class="activity-title">Theme: {day['theme']}</div>
                    <div class="muted">Date: {day.get('date', 'Not specified')}</div>
                    <div>{tags_html}</div>
                """,
                unsafe_allow_html=True,
            )

            for activity in day["activities"]:
                cost_label = "Estimated cost" if activity.get("cost_source") == "estimated" else "Cost"
                st.markdown(
                    f"""
                    <div class="activity-row">
                        <div class="activity-title">{activity['time_slot'].title()} • {activity['title']}</div>
                        <div class="muted">
                            Travel: {activity.get('travel_time_from_previous_minutes', 'N/A')} min &nbsp;&nbsp;•&nbsp;&nbsp;
                            {cost_label}: ₹ {activity['estimated_cost']}<br>
                            {activity['description']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if activity.get("buffer_note"):
                    st.caption(activity["buffer_note"])

            if day["route_legs"]:
                st.markdown("<div style='margin-top:0.8rem; color:inherit; font-weight:700;'>Route Details</div>", unsafe_allow_html=True)
                route_html = ""
                for leg in day["route_legs"]:
                    route_html += (
                        f"<span class='route-chip'>{leg['origin_name']} → {leg['destination_name']} • "
                        f"{leg['distance_km']} km • {leg['duration_minutes']} min</span>"
                    )
                st.markdown(route_html, unsafe_allow_html=True)

            for warning in day.get("warnings", []):
                st.warning(warning)

            st.markdown("</div>", unsafe_allow_html=True)

    json_bytes = response.text.encode("utf-8")
    ics_text = ""
    try:
        ics_response = httpx.post(f"{FASTAPI_URL}/export/ics", json=plan, timeout=30.0)
        if ics_response.status_code == 200:
            ics_text = ics_response.text
    except httpx.HTTPError:
        ics_text = ""

    download_col1, download_col2 = st.columns(2)
    with download_col1:
        st.download_button(
            "Download JSON",
            data=json_bytes,
            file_name="trip_plan.json",
            mime="application/json",
            use_container_width=True,
        )
    with download_col2:
        st.download_button(
            "Download ICS",
            data=ics_text.encode("utf-8"),
            file_name="trip_plan.ics",
            mime="text/calendar",
            use_container_width=True,
        )
else:
    st.markdown(
        """
        <div class="glass-card" style="margin-top:1rem;">
            <div class="section-title">Ready when you are</div>
            <div class="muted">
                Enter your destination, budget, travel preferences, and dates from the sidebar,
                then generate a premium itinerary with hotel suggestions, budget insights, budget chart,
                route details, and downloadable trip files.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
