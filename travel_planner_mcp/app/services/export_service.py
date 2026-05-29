from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from app.models.schemas import TripPlanResponse


def plan_to_json(plan: TripPlanResponse) -> str:
    return plan.model_dump_json(indent=2)


def plan_to_ics(plan: TripPlanResponse) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//TravelPlannerMCP//EN",
        "CALSCALE:GREGORIAN",
    ]
    now_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    hotel_name = plan.hotel.name if plan.hotel else "No hotel selected"
    hotel_price = plan.hotel.nightly_price if plan.hotel and plan.hotel.nightly_price is not None else "Not available"
    transport = plan.transport.mode if plan.transport else "Not estimated"

    for daily_plan in plan.daily_plans:
        if daily_plan.date:
            start = datetime.combine(daily_plan.date, datetime.min.time()) + timedelta(hours=9)
            end = start + timedelta(hours=10)
            dtstart = start.strftime("%Y%m%dT%H%M%S")
            dtend = end.strftime("%Y%m%dT%H%M%S")
        else:
            dtstart = "20260101T090000"
            dtend = "20260101T190000"

        attraction_names = ", ".join(
            activity.place_name or activity.title for activity in daily_plan.activities if activity.place_name or activity.title
        )
        total_travel = round(sum(leg.duration_minutes for leg in daily_plan.route_legs), 1)
        description = (
            f"Hotel: {hotel_name}\\n"
            f"Hotel nightly price: {hotel_price}\\n"
            f"Transport mode: {transport}\\n"
            f"Attractions: {attraction_names}\\n"
            f"Estimated travel time: {total_travel} minutes\\n"
            f"Daily estimated cost: {daily_plan.estimated_cost}"
        )
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:travel-planner-day-{daily_plan.day_number}@local",
                f"DTSTAMP:{now_stamp}",
                f"DTSTART:{dtstart}",
                f"DTEND:{dtend}",
                f"SUMMARY:Day {daily_plan.day_number} - {daily_plan.theme}",
                f"DESCRIPTION:{description}",
                "END:VEVENT",
            ]
        )

    lines.append("END:VCALENDAR")
    return "\n".join(lines)
