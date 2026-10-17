from datetime import date

from common import activity_label, load_activities, make_activity, save_activities, type_name


def test_make_activity_keeps_only_published_fields():
    activity = make_activity("garmin-1", date(2026, 10, 16), "running", 2950.4, 8214.9)
    assert activity == {
        "id": "garmin-1",
        "date": "2026-10-16",
        "type": "running",
        "duration_s": 2950,
        "distance_km": 8.21,
    }


def test_make_activity_drops_gps_noise_distance():
    assert make_activity("garmin-1", date(2026, 1, 1), "strength_training", 1800, 42)["distance_km"] is None
    assert make_activity("garmin-1", date(2026, 1, 1), "yoga", 1800, None)["distance_km"] is None


def test_save_writes_one_sorted_activity_per_line(tmp_path):
    path = tmp_path / "activities.json"
    later = make_activity("garmin-10", date(2026, 10, 16), "running", 60, 1000)
    earlier = make_activity("garmin-9", date(2026, 10, 16), "yoga", 60, None)
    oldest = make_activity("strava-5", date(2026, 10, 1), "walking", 60, 1000)
    save_activities([later, earlier, oldest], path)

    lines = path.read_text().splitlines()
    assert lines[0] == "[" and lines[-1] == "]"
    assert len(lines) == 5
    assert load_activities(path) == [oldest, earlier, later]


def test_save_empty(tmp_path):
    path = tmp_path / "activities.json"
    save_activities([], path)
    assert path.read_text() == "[]\n"
    assert load_activities(tmp_path / "missing.json") == []


def test_labels():
    run = make_activity("garmin-1", date(2026, 1, 1), "running", 2950, 8214)
    strength = make_activity("garmin-2", date(2026, 1, 1), "strength_training", 45 * 60, None)
    long_ride = make_activity("garmin-3", date(2026, 1, 1), "cycling", 4 * 3600 + 5 * 60, 142_400)
    assert activity_label(run) == "Run · 8.2 km"
    assert activity_label(strength) == "Strength · 45 min"
    assert activity_label(long_ride) == "Ride · 142 km"
    assert activity_label({**strength, "duration_s": 80 * 60}) == "Strength · 1h 20m"


def test_type_name_fallback():
    assert type_name("lap_swimming") == "Pool swim"
    assert type_name("inline_skating") == "Inline skating"
    assert type_name("some_new_sport_ws") == "Some new sport"
