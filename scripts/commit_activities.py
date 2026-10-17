"""One backdated commit per activity, so the contribution graph mirrors training.

Activity commits are authored as you (only commits from an email linked to
your account count on the graph). Card refreshes are authored by the Actions
bot, so the nightly re-render doesn't paint a square every day.
"""

from __future__ import annotations

import os
import subprocess
from datetime import date, datetime, time
from pathlib import Path

from common import CARDS_DIR, DATA_FILE, REPO_ROOT, TZ, activity_label, save_activities, sort_key

AUTHOR = ("Eike Christian Karbe", "38853513+ekarbe@users.noreply.github.com")
BOT = ("github-actions[bot]", "41898282+github-actions[bot]@users.noreply.github.com")


def commit_date(day: date) -> str:
    """Noon in Berlin keeps the commit on the activity's day and hides the start time."""
    return datetime.combine(day, time(12), TZ).isoformat()


def git(
    repo: Path, *args: str, identity: tuple[str, str] = BOT, when: str | None = None
) -> subprocess.CompletedProcess:
    name, email = identity
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": name,
        "GIT_AUTHOR_EMAIL": email,
        "GIT_COMMITTER_NAME": name,
        "GIT_COMMITTER_EMAIL": email,
    }
    if when:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = when
    return subprocess.run(["git", *args], cwd=repo, env=env, check=True)


def commit_activities(
    new: list[dict],
    activities: list[dict],
    repo: Path = REPO_ROOT,
    data_file: Path = DATA_FILE,
) -> list[dict]:
    """Add each new activity to the data file in its own commit, oldest first."""
    for activity in sorted(new, key=sort_key):
        activities = [*activities, activity]
        save_activities(activities, data_file)
        git(repo, "add", str(data_file))
        git(
            repo,
            "commit", "--quiet", "--message", activity_label(activity),
            identity=AUTHOR,
            when=commit_date(date.fromisoformat(activity["date"])),
        )
        print(f"Committed {activity['date']} {activity_label(activity)}")
    return activities


def commit_cards(repo: Path = REPO_ROOT, cards_dir: Path = CARDS_DIR) -> bool:
    git(repo, "add", str(cards_dir))
    unchanged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=repo).returncode == 0
    if unchanged:
        return False
    git(repo, "commit", "--quiet", "--message", "Update activity cards")
    return True
