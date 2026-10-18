"""Fetch activities from Garmin Connect.

Garmin has no public API for individual users, so this uses the unofficial
garminconnect library and logs in with GARMIN_EMAIL / GARMIN_PASSWORD.
Only the fields built by common.make_activity leave this module.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, timedelta

from common import make_activity, today

PAGE_SIZE = 100


def normalize(raw: dict) -> dict:
    distance_m = raw.get("distance") or 0
    # Moving time for activities that cover distance; total time for the rest
    # (strength, yoga), where Garmin's moving time means little.
    duration_s = raw.get("duration") or 0
    if distance_m and raw.get("movingDuration"):
        duration_s = raw["movingDuration"]
    return make_activity(
        f"garmin-{raw['activityId']}",
        date.fromisoformat(raw["startTimeLocal"][:10]),
        raw["activityType"]["typeKey"],
        duration_s,
        distance_m,
    )


def login(token: str | None):
    from garminconnect import Garmin

    garmin = Garmin(os.environ["GARMIN_EMAIL"], os.environ["GARMIN_PASSWORD"])
    # The cached token is inline JSON; if it is missing or stale the library
    # does a full password login instead.
    garmin.login(token)
    return garmin


def fetch(since: date | None, token: str | None = None) -> tuple[list[dict], str]:
    """Return activities from `since` on (everything if None) and the fresh token."""
    garmin = login(token)
    if since is None:
        raws: list[dict] = []
        while page := garmin.get_activities(len(raws), PAGE_SIZE):
            raws.extend(page)
    else:
        # A day past today covers activities logged in a time zone ahead of Berlin.
        end = today() + timedelta(days=1)
        raws = garmin.get_activities_by_date(since.isoformat(), end.isoformat())
    return [normalize(raw) for raw in raws], garmin.client.dumps()


if __name__ == "__main__":
    # Local check: python scripts/fetch_garmin.py [YYYY-MM-DD]
    since = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else today() - timedelta(days=7)
    activities, _ = fetch(since)
    print(json.dumps(activities, indent=2))
