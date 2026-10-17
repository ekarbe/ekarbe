from datetime import date, timedelta
from xml.dom import minidom

from common import make_activity
from render_cards import heatmap, level, recent, render_all, stats, streaks, weeks_ago

TODAY = date(2026, 10, 17)  # a Saturday


def run(day, km=10.0, minutes=50, n=0):
    return make_activity(f"garmin-{day.toordinal()}{n}", day, "running", minutes * 60, km * 1000)


def test_level_thresholds():
    assert [level(m) for m in (None, 0, 29, 30, 59, 60, 89, 90, 240)] == [0, 1, 1, 2, 2, 3, 3, 4, 4]


def test_streaks():
    days = {TODAY - timedelta(days=d) for d in (1, 2, 3, 10, 11, 12, 13, 14)}
    # Today isn't synced yet, so the streak through yesterday is current.
    assert streaks(days, TODAY) == (3, 5)
    assert streaks(days | {TODAY}, TODAY) == (4, 5)
    assert streaks(days - {TODAY - timedelta(days=1)}, TODAY) == (0, 5)
    assert streaks(set(), TODAY) == (0, 0)


def test_weeks_ago():
    assert weeks_ago(date(2026, 10, 12), TODAY) == "this week"  # Monday
    assert weeks_ago(date(2026, 10, 11), TODAY) == "last week"  # Sunday before
    assert weeks_ago(date(2026, 9, 28), TODAY) == "2 weeks ago"
    assert weeks_ago(date(2026, 6, 1), TODAY) == "4 months ago"
    assert weeks_ago(date(2025, 9, 1), TODAY) == "1 year ago"
    assert weeks_ago(date(2023, 1, 1), TODAY) == "3 years ago"


def test_stats_totals():
    activities = [
        run(date(2026, 10, 13), km=8.2, minutes=40),  # this week
        run(date(2026, 10, 2), km=10.0, minutes=50),  # this month
        run(date(2026, 3, 1), km=100.0, minutes=600),  # this year
        run(date(2025, 12, 31), km=5.0, minutes=30),  # last year
    ]
    svg = stats(activities, TODAY, "light")
    assert ">8.2 km<" in svg and ">18.2 km<" in svg and ">118 km<" in svg
    assert ">40 min<" in svg and ">1h 30m<" in svg and ">11h 30m<" in svg


def test_recent_shows_newest_five():
    activities = [run(TODAY - timedelta(days=d)) for d in range(0, 16, 2)]
    svg = recent(activities, TODAY, "dark")
    assert svg.count("Run · 10.0 km") == 5
    assert svg.count(">this week<") == 3 and svg.count(">last week<") == 2


def test_heatmap_draws_a_year_up_to_today():
    svg = heatmap([run(TODAY), run(TODAY, minutes=60, n=1)], TODAY, "light")
    cells = svg.count('width="11" height="11"') - 5  # minus the legend
    assert cells == 52 * 7 + TODAY.weekday() + 1
    assert "1h 50m · 2 activities" in svg


def test_render_all_writes_valid_svgs(tmp_path):
    render_all([run(TODAY - timedelta(days=3))], TODAY, tmp_path)
    files = sorted(p.name for p in tmp_path.iterdir())
    assert files == [f"{card}-{theme}.svg" for card in ("heatmap", "recent", "stats") for theme in ("dark", "light")]
    for path in tmp_path.iterdir():
        minidom.parse(str(path))


def test_render_empty(tmp_path):
    render_all([], TODAY, tmp_path)
    assert "No activities yet" in (tmp_path / "recent-light.svg").read_text()
