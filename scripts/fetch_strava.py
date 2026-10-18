"""Fetch activities from the Strava API, the fallback when Garmin login breaks.

Needs STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET and STRAVA_REFRESH_TOKEN (see
strava_auth.py). Activities that Garmin uploaded to Strava keep their Garmin
ID, so switching sources never creates duplicates.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import date, datetime, time, timedelta

import requests

from common import STRAVA_TYPES, TZ, make_activity, today

TOKEN_URL = "https://www.strava.com/oauth/token"
ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"
PAGE_SIZE = 200
TIMEOUT_S = 30

# Garmin sets external_id to e.g. "garmin_ping_17234567890" on upload.
GARMIN_EXTERNAL_ID = re.compile(r"^garmin_(?:ping|push)_(\d+)")


def configured() -> bool:
    return all(
        os.environ.get(name)
        for name in ("STRAVA_CLIENT_ID", "STRAVA_CLIENT_SECRET", "STRAVA_REFRESH_TOKEN")
    )


def type_key(raw: dict) -> str:
    sport = raw.get("sport_type") or raw.get("type") or "Workout"
    if raw.get("trainer") and sport == "Ride":
        return "indoor_cycling"
    if raw.get("trainer") and sport == "Run":
        return "treadmill_running"
    if sport in STRAVA_TYPES:
        return STRAVA_TYPES[sport]
    return re.sub(r"(?<!^)(?=[A-Z])", "_", sport).lower()


def normalize(raw: dict) -> dict:
    match = GARMIN_EXTERNAL_ID.match(raw.get("external_id") or "")
    activity_id = f"garmin-{match.group(1)}" if match else f"strava-{raw['id']}"
    return make_activity(
        activity_id,
        date.fromisoformat(raw["start_date_local"][:10]),
        type_key(raw),
        raw.get("moving_time") or raw.get("elapsed_time"),
        raw.get("distance"),
    )


def access_token(refresh_tokens: list[str]) -> tuple[str, str]:
    """Trade the first working refresh token for an access token.

    Strava may rotate the refresh token on any exchange, so the caller has to
    keep the one returned here for the next run.
    """
    if not refresh_tokens:
        raise RuntimeError("STRAVA_REFRESH_TOKEN is not set")
    for refresh_token in refresh_tokens:
        response = requests.post(
            TOKEN_URL,
            data={
                "client_id": os.environ["STRAVA_CLIENT_ID"],
                "client_secret": os.environ["STRAVA_CLIENT_SECRET"],
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            timeout=TIMEOUT_S,
        )
        if response.ok:
            body = response.json()
            return body["access_token"], body["refresh_token"]
    response.raise_for_status()


def fetch(since: date | None, cached_token: str | None = None) -> tuple[list[dict], str]:
    """Return activities from `since` on (everything if None) and the refresh token to keep."""
    # The cached token is the newest; the secret still works if the cache was lost
    # before Strava rotated it, or after you replaced the secret.
    candidates = [t for t in (cached_token, os.environ.get("STRAVA_REFRESH_TOKEN")) if t]
    access, refresh_token = access_token(list(dict.fromkeys(candidates)))
    params = {"per_page": PAGE_SIZE}
    if since is not None:
        params["after"] = int(datetime.combine(since, time(), TZ).timestamp())
    raws: list[dict] = []
    page = 1
    while True:
        response = requests.get(
            ACTIVITIES_URL,
            headers={"Authorization": f"Bearer {access}"},
            params={**params, "page": page},
            timeout=TIMEOUT_S,
        )
        response.raise_for_status()
        if not (batch := response.json()):
            break
        raws.extend(batch)
        page += 1
    return [normalize(raw) for raw in raws], refresh_token


if __name__ == "__main__":
    # Local check: python scripts/fetch_strava.py [YYYY-MM-DD]
    since = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else today() - timedelta(days=7)
    activities, _ = fetch(since)
    print(json.dumps(activities, indent=2))
