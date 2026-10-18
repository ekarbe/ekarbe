"""Nightly sync: fetch new activities, commit each one backdated, re-render the cards.

    python scripts/sync.py [--source auto|garmin|strava] [--dry-run]

An empty data file means first run, so the whole history is fetched. Pushing
is left to the workflow.
"""

from __future__ import annotations

import argparse
import os
from datetime import date, timedelta

import fetch_garmin
import fetch_strava
import tokens
from commit_activities import commit_activities, commit_cards
from common import activity_label, load_activities, sort_key, today
from render_cards import render_all

# Re-check this many days before the newest stored activity, for watches that
# sync to Garmin late. Already-stored IDs are skipped.
LOOKBACK_DAYS = 14


def warn(message: str) -> None:
    # Shows up as an annotation on the workflow run.
    print(f"::warning::{message}")


def fetch(source: str, since: date | None, cache: dict) -> list[dict]:
    """Fetch from Garmin, falling back to Strava in auto mode. Updates `cache`."""
    if source in ("auto", "garmin"):
        try:
            activities, cache["garmin"] = fetch_garmin.fetch(since, cache.get("garmin"))
            return activities
        except Exception as error:
            if source == "garmin" or not fetch_strava.configured():
                raise
            warn(f"Garmin failed, using Strava instead ({type(error).__name__}: {error})")
    activities, cache["strava"] = fetch_strava.fetch(since, cache.get("strava"))
    return activities


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", choices=["auto", "garmin", "strava"], default="auto")
    parser.add_argument("--dry-run", action="store_true", help="list new activities, change nothing")
    args = parser.parse_args(argv)

    activities = load_activities()
    known = {a["id"] for a in activities}
    since = None
    if activities:
        since = date.fromisoformat(max(a["date"] for a in activities)) - timedelta(days=LOOKBACK_DAYS)

    secret = os.environ.get("TOKEN_CACHE_KEY")
    if not secret:
        warn("TOKEN_CACHE_KEY is not set, so every run does a full login")
    cache = tokens.load(secret)
    try:
        fetched = fetch(args.source, since, cache)
    finally:
        tokens.save(cache, secret)

    new = list({a["id"]: a for a in fetched if a["id"] not in known}.values())
    print(f"Fetched {len(fetched)} activities, {len(new)} new" + (" (backfill)" if since is None else ""))
    if args.dry_run:
        for activity in sorted(new, key=sort_key):
            print(f"  {activity['date']}  {activity_label(activity)}")
        return

    activities = commit_activities(new, activities)
    render_all(activities, today())
    if commit_cards():
        print("Cards updated")


if __name__ == "__main__":
    main()
