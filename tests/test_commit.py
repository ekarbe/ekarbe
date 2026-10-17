import subprocess
from datetime import date

import pytest

from commit_activities import AUTHOR, BOT, commit_activities, commit_cards
from common import load_activities, make_activity


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "--quiet", "--initial-branch=main")
    git(tmp_path, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "--quiet", "--allow-empty", "-m", "init")
    return tmp_path


def test_one_backdated_commit_per_activity(repo):
    data_file = repo / "data" / "activities.json"
    winter_run = make_activity("garmin-2", date(2026, 1, 15), "running", 2950, 8214)
    summer_yoga = make_activity("garmin-1", date(2026, 7, 3), "yoga", 3600, None)

    activities = commit_activities([summer_yoga, winter_run], [], repo, data_file)

    log = git(repo, "log", "--format=%an|%ae|%aI|%cI|%s", "-2").splitlines()
    assert log == [
        f"{AUTHOR[0]}|{AUTHOR[1]}|2026-07-03T12:00:00+02:00|2026-07-03T12:00:00+02:00|Yoga · 1h",
        f"{AUTHOR[0]}|{AUTHOR[1]}|2026-01-15T12:00:00+01:00|2026-01-15T12:00:00+01:00|Run · 8.2 km",
    ]
    assert load_activities(data_file) == activities == [winter_run, summer_yoga]
    # Each commit adds exactly one line to the data file.
    assert git(repo, "show", "--format=", "--numstat", "HEAD").split()[:2] == ["2", "1"]


def test_cards_commit_only_when_changed(repo):
    cards = repo / "cards"
    cards.mkdir()
    (cards / "stats-light.svg").write_text("<svg/>")

    assert commit_cards(repo, cards) is True
    assert git(repo, "log", "--format=%ae|%s", "-1").strip() == f"{BOT[1]}|Update activity cards"
    assert commit_cards(repo, cards) is False
