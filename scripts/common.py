"""Shared pieces: the activity record, the public data file, display helpers."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = REPO_ROOT / "data" / "activities.json"
CARDS_DIR = REPO_ROOT / "cards"
TZ = ZoneInfo("Europe/Berlin")

# Shorter distances are GPS noise on indoor activities, not real distance.
MIN_DISTANCE_M = 100

# Garmin type keys (also the canonical keys for Strava activities).
# Anything missing falls back to the key with underscores as spaces.
TYPE_NAMES = {
    "running": "Run",
    "street_running": "Run",
    "treadmill_running": "Treadmill run",
    "trail_running": "Trail run",
    "track_running": "Track run",
    "indoor_running": "Indoor run",
    "virtual_run": "Virtual run",
    "ultra_run": "Ultra run",
    "cycling": "Ride",
    "road_biking": "Road ride",
    "gravel_cycling": "Gravel ride",
    "mountain_biking": "MTB ride",
    "indoor_cycling": "Indoor ride",
    "virtual_ride": "Virtual ride",
    "e_bike_fitness": "E-bike ride",
    "e_bike_mountain": "E-MTB ride",
    "cyclocross": "Cyclocross",
    "swimming": "Swim",
    "lap_swimming": "Pool swim",
    "open_water_swimming": "Open water swim",
    "walking": "Walk",
    "casual_walking": "Walk",
    "speed_walking": "Speed walk",
    "hiking": "Hike",
    "mountaineering": "Mountaineering",
    "strength_training": "Strength",
    "yoga": "Yoga",
    "pilates": "Pilates",
    "hiit": "HIIT",
    "indoor_cardio": "Cardio",
    "fitness_equipment": "Workout",
    "elliptical": "Elliptical",
    "stair_climbing": "Stair climb",
    "floor_climbing": "Floor climb",
    "rowing": "Row",
    "indoor_rowing": "Indoor row",
    "kayaking": "Kayak",
    "stand_up_paddleboarding": "SUP",
    "resort_skiing": "Ski",
    "resort_snowboarding": "Snowboard",
    "resort_skiing_snowboarding_ws": "Ski",
    "backcountry_skiing": "Backcountry ski",
    "cross_country_skiing_ws": "XC ski",
    "skate_skiing_ws": "Skate ski",
    "snowshoeing": "Snowshoe",
    "indoor_climbing": "Climbing",
    "rock_climbing": "Climbing",
    "bouldering": "Bouldering",
    "multi_sport": "Multisport",
    "breathwork": "Breathwork",
    "meditation": "Meditation",
    "other": "Activity",
}

# Strava sport_type to Garmin type key.
STRAVA_TYPES = {
    "Run": "running",
    "TrailRun": "trail_running",
    "VirtualRun": "virtual_run",
    "Ride": "cycling",
    "GravelRide": "gravel_cycling",
    "MountainBikeRide": "mountain_biking",
    "VirtualRide": "virtual_ride",
    "EBikeRide": "e_bike_fitness",
    "EMountainBikeRide": "e_bike_mountain",
    "Swim": "swimming",
    "Walk": "walking",
    "Hike": "hiking",
    "WeightTraining": "strength_training",
    "Yoga": "yoga",
    "Pilates": "pilates",
    "HighIntensityIntervalTraining": "hiit",
    "Crossfit": "hiit",
    "Workout": "indoor_cardio",
    "Elliptical": "elliptical",
    "StairStepper": "stair_climbing",
    "Rowing": "rowing",
    "VirtualRow": "indoor_rowing",
    "Kayaking": "kayaking",
    "StandUpPaddling": "stand_up_paddleboarding",
    "AlpineSki": "resort_skiing",
    "Snowboard": "resort_snowboarding",
    "BackcountrySki": "backcountry_skiing",
    "NordicSki": "cross_country_skiing_ws",
    "Snowshoe": "snowshoeing",
    "RockClimbing": "rock_climbing",
}


def today() -> date:
    return datetime.now(TZ).date()


def make_activity(
    activity_id: str,
    day: date,
    type_key: str,
    duration_s: float | None,
    distance_m: float | None,
) -> dict:
    """Build a record holding only the fields that may be published."""
    distance_km = None
    if distance_m and distance_m >= MIN_DISTANCE_M:
        distance_km = round(distance_m / 1000, 2)
    return {
        "id": activity_id,
        "date": day.isoformat(),
        "type": type_key,
        "duration_s": round(duration_s or 0),
        "distance_km": distance_km,
    }


def sort_key(activity: dict) -> tuple:
    source, _, number = activity["id"].partition("-")
    return activity["date"], source, int(number)


def load_activities(path: Path = DATA_FILE) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text())


def save_activities(activities: list[dict], path: Path = DATA_FILE) -> None:
    """Write one activity per line, so each commit's diff is a single line."""
    lines = [json.dumps(a, ensure_ascii=False) for a in sorted(activities, key=sort_key)]
    body = ",\n".join(f"  {line}" for line in lines)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"[\n{body}\n]\n" if lines else "[]\n")


def type_name(type_key: str) -> str:
    if type_key in TYPE_NAMES:
        return TYPE_NAMES[type_key]
    name = type_key.removesuffix("_ws").replace("_", " ").strip()
    return name.capitalize() or "Activity"


def format_km(km: float) -> str:
    return f"{km:.1f} km" if km < 100 else f"{km:,.0f} km"


def format_duration(seconds: float) -> str:
    minutes = round(seconds / 60)
    if minutes < 60:
        return f"{minutes} min"
    hours, minutes = divmod(minutes, 60)
    if hours >= 100 or minutes == 0:
        return f"{hours:,}h"
    return f"{hours}h {minutes}m"


def activity_label(activity: dict) -> str:
    """'Run · 8.2 km', or 'Strength · 45 min' when there is no distance."""
    amount = (
        format_km(activity["distance_km"])
        if activity["distance_km"] is not None
        else format_duration(activity["duration_s"])
    )
    return f"{type_name(activity['type'])} · {amount}"
