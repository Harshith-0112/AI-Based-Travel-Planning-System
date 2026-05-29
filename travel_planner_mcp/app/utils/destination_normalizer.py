from __future__ import annotations

import re


DESTINATION_ALIASES = {
    "vizag": "visakhapatnam",
    "visag": "visakhapatnam",
    "banglore": "bangalore",
    "bengaluru": "bangalore",
    "mysuru": "mysore",
    "benaras": "varanasi",
    "banaras": "varanasi",
    "bombay": "mumbai",
    "calcutta": "kolkata",
    "madras": "chennai",
    "pondy": "pondicherry",
    "cochin": "kochi",
    "leh ladakh": "leh_ladakh",
    "leh-ladakh": "leh_ladakh",
    "andaman islands": "andaman",
    "benares": "varanasi",
}


def normalize_destination_name(destination: str) -> str:
    """Return the canonical destination name used by lookups and prompts."""
    cleaned = re.sub(r"\s+", " ", destination.strip().lower())
    return DESTINATION_ALIASES.get(cleaned, cleaned)


def display_destination_name(destination: str) -> str:
    return normalize_destination_name(destination).title()


def destination_slug(destination: str) -> str:
    normalized = normalize_destination_name(destination)
    slug = re.sub(r"[^a-z0-9]+", "_", normalized)
    return slug.strip("_") or "unknown_destination"
