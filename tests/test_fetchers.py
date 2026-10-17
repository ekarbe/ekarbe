from datetime import date

import fetch_garmin
import fetch_strava
import pytest

GARMIN_RUN = {
    "activityId": 17234567890,
    "activityName": "Berlin - Morning Run",
    "startTimeLocal": "2026-10-16 07:12:34",
    "startTimeGMT": "2026-10-16 05:12:34",
    "activityType": {"typeId": 1, "typeKey": "running", "parentTypeId": 17},
    "distance": 8214.9,
    "duration": 3010.2,
    "movingDuration": 2950.0,
    "averageHR": 151.0,
    "startLatitude": 52.52,
    "startLongitude": 13.40,
    "locationName": "Berlin",
    "deviceId": 3442975663,
}

GARMIN_STRENGTH = {
    "activityId": 17234567999,
    "activityName": "Strength",
    "startTimeLocal": "2026-10-15 18:00:00",
    "activityType": {"typeKey": "strength_training"},
    "distance": 0.0,
    "duration": 2700.0,
    "movingDuration": 540.0,
}


def test_garmin_normalize_keeps_only_published_fields():
    assert fetch_garmin.normalize(GARMIN_RUN) == {
        "id": "garmin-17234567890",
        "date": "2026-10-16",
        "type": "running",
        "duration_s": 2950,
        "distance_km": 8.21,
    }


def test_garmin_uses_total_time_without_distance():
    activity = fetch_garmin.normalize(GARMIN_STRENGTH)
    assert activity["duration_s"] == 2700
    assert activity["distance_km"] is None


STRAVA_RUN = {
    "id": 9988776655,
    "name": "Morning Run",
    "external_id": "garmin_ping_17234567890",
    "sport_type": "Run",
    "start_date": "2026-10-16T05:12:34Z",
    "start_date_local": "2026-10-16T07:12:34Z",
    "distance": 8214.9,
    "moving_time": 2950,
    "elapsed_time": 3010,
    "start_latlng": [52.52, 13.40],
    "map": {"summary_polyline": "abc"},
    "trainer": False,
}


def test_strava_maps_garmin_uploads_to_garmin_ids():
    # Same activity from either source gives the same record, so no duplicates.
    assert fetch_strava.normalize(STRAVA_RUN) == fetch_garmin.normalize(GARMIN_RUN)


def test_strava_types():
    assert fetch_strava.normalize({**STRAVA_RUN, "external_id": None})["id"] == "strava-9988776655"
    assert fetch_strava.type_key({"sport_type": "Ride", "trainer": True}) == "indoor_cycling"
    assert fetch_strava.type_key({"sport_type": "WeightTraining"}) == "strength_training"
    assert fetch_strava.type_key({"sport_type": "InlineSkate"}) == "inline_skate"


class FakeResponse:
    def __init__(self, status, body):
        self.status_code = status
        self.ok = status < 400
        self._body = body

    def json(self):
        return self._body

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError(f"HTTP {self.status_code}")


@pytest.fixture
def strava_env(monkeypatch):
    monkeypatch.setenv("STRAVA_CLIENT_ID", "1")
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "secret")
    monkeypatch.setenv("STRAVA_REFRESH_TOKEN", "from-secret")


def test_strava_fetch_pages_and_rotates_token(monkeypatch, strava_env):
    tried = []

    def post(url, data, timeout):
        tried.append(data["refresh_token"])
        if data["refresh_token"] == "stale-cached":
            return FakeResponse(400, {"message": "Bad Request"})
        return FakeResponse(200, {"access_token": "access", "refresh_token": "rotated"})

    pages = {1: [STRAVA_RUN], 2: [{**STRAVA_RUN, "id": 1, "external_id": None}], 3: []}

    def get(url, headers, params, timeout):
        assert headers["Authorization"] == "Bearer access"
        assert params["after"] > 0
        return FakeResponse(200, pages[params["page"]])

    monkeypatch.setattr(fetch_strava.requests, "post", post)
    monkeypatch.setattr(fetch_strava.requests, "get", get)

    activities, token = fetch_strava.fetch(date(2026, 10, 1), "stale-cached")
    assert tried == ["stale-cached", "from-secret"]
    assert token == "rotated"
    assert [a["id"] for a in activities] == ["garmin-17234567890", "strava-1"]
