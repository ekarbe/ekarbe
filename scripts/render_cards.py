"""Render the profile cards as SVG, each in a light and a dark variant.

    python scripts/render_cards.py [--today YYYY-MM-DD] [--data FILE] [--out DIR]
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

from common import (
    CARDS_DIR,
    DATA_FILE,
    activity_label,
    format_duration,
    format_km,
    load_activities,
    sort_key,
    today,
)

FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"

# GitHub's own colors, so the cards sit naturally on the profile page.
THEMES = {
    "light": {
        "bg": "#ffffff",
        "border": "#d1d9e0",
        "text": "#1f2328",
        "muted": "#59636e",
        "outline": "#1f2328",
        "levels": ("#eff2f5", "#aceebb", "#4ac26b", "#2da44e", "#116329"),
    },
    "dark": {
        "bg": "#0d1117",
        "border": "#3d444d",
        "text": "#f0f6fc",
        "muted": "#9198a1",
        "outline": "#ffffff",
        "levels": ("#151b23", "#033a16", "#196c2e", "#2ea043", "#56d364"),
    },
}

# Heatmap shades by minutes that day: under 30, under 60, under 90, 90 and up.
LEVEL_MINUTES = (30, 60, 90)
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()

PAD = 16
CELL = 11
STEP = CELL + 3
WEEKS = 53
# The stats and recent cards sit side by side, so they share a size.
SMALL_W, SMALL_H = 400, 210
RECENT_COUNT = 5


def svg(width: int, height: int, theme: str, title: str, body: list[str]) -> str:
    colors = THEMES[theme]
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-label={quoteattr(title)}>',
            f"<title>{escape(title)}</title>",
            "<style>",
            f"text {{ font-family: {FONT}; font-size: 12px; fill: {colors['text']}; }}",
            f".muted {{ fill: {colors['muted']}; }}",
            ".title { font-size: 14px; font-weight: 600; }",
            ".value { font-size: 13px; font-weight: 600; }",
            ".small { font-size: 10px; }",
            "</style>",
            f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="6" '
            f'fill="{colors["bg"]}" stroke="{colors["border"]}"/>',
            *body,
            "</svg>",
            "",
        ]
    )


def text(x: float, y: float, content: str, cls: str = "", anchor: str = "start") -> str:
    attrs = f' class="{cls}"' if cls else ""
    if anchor != "start":
        attrs += f' text-anchor="{anchor}"'
    return f'<text x="{x}" y="{y}"{attrs}>{escape(content)}</text>'


def plural(count: int, word: str, words: str | None = None) -> str:
    return f"{count:,} {word if count == 1 else words or word + 's'}"


def day_of(activity: dict) -> date:
    return date.fromisoformat(activity["date"])


def monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


def level(minutes: float | None) -> int:
    if minutes is None:
        return 0
    return 1 + sum(minutes >= threshold for threshold in LEVEL_MINUTES)


def heatmap(activities: list[dict], today: date, theme: str) -> str:
    colors = THEMES[theme]
    start = monday(today) - timedelta(weeks=WEEKS - 1)
    minutes: dict[date, float] = defaultdict(float)
    for activity in activities:
        minutes[day_of(activity)] += activity["duration_s"] / 60
    in_window = [a for a in activities if start <= day_of(a) <= today]

    left, top = PAD + 28, 64
    width = left + WEEKS * STEP - 3 + PAD
    height = top + 7 * STEP - 3 + 36
    total_s = sum(a["duration_s"] for a in in_window)
    summary = f"{format_duration(total_s)} · {plural(len(in_window), 'activity', 'activities')}"
    body = [
        text(PAD, 30, "Training in the last year", "title"),
        text(width - PAD, 30, summary, "muted", "end"),
    ]

    labels = []
    for col in range(WEEKS):
        week = start + timedelta(weeks=col)
        if col == 0 or week.month != (week - timedelta(weeks=1)).month:
            labels.append((col, MONTHS[week.month - 1]))
    if len(labels) > 1 and labels[1][0] < 3:
        labels.pop(0)  # no room for a partial first month
    body += [text(left + col * STEP, top - 8, name, "small muted") for col, name in labels]
    weekdays = ((0, "Mon"), (2, "Wed"), (4, "Fri"))
    body += [text(PAD, top + row * STEP + CELL - 2, name, "small muted") for row, name in weekdays]

    for col in range(WEEKS):
        for row in range(7):
            day = start + timedelta(weeks=col, days=row)
            if day > today:
                break
            fill = colors["levels"][level(minutes.get(day))]
            body.append(
                f'<rect x="{left + col * STEP}" y="{top + row * STEP}" width="{CELL}" height="{CELL}" '
                f'rx="2" fill="{fill}" stroke="{colors["outline"]}" stroke-opacity="0.06"/>'
            )

    legend_y = top + 7 * STEP - 3 + 22
    first_x = width - PAD - 30 - (5 * STEP - 3)
    body.append(text(left, legend_y, "Shade shows minutes of activity per day", "small muted"))
    body.append(text(first_x - 5, legend_y, "Less", "small muted", "end"))
    body += [
        f'<rect x="{first_x + i * STEP}" y="{legend_y - CELL + 2}" width="{CELL}" height="{CELL}" '
        f'rx="2" fill="{fill}" stroke="{colors["outline"]}" stroke-opacity="0.06"/>'
        for i, fill in enumerate(colors["levels"])
    ]
    body.append(text(width - PAD, legend_y, "More", "small muted", "end"))
    return svg(width, height, theme, "Training heatmap for the last 12 months", body)


def streaks(days: set[date], today: date) -> tuple[int, int]:
    """Current and longest run of consecutive days with at least one activity."""
    longest = run = 0
    previous = None
    for day in sorted(days):
        run = run + 1 if previous == day - timedelta(days=1) else 1
        longest = max(longest, run)
        previous = day
    # The nightly sync runs before most of today's training, so a streak
    # through yesterday still counts as current.
    current = 0
    day = today if today in days else today - timedelta(days=1)
    while day in days:
        current += 1
        day -= timedelta(days=1)
    return current, longest


def total_distance(activities: list[dict]) -> str:
    km = sum(a["distance_km"] or 0 for a in activities)
    return format_km(km) if km else "0 km"


def stats(activities: list[dict], today: date, theme: str) -> str:
    periods = (
        ("This week", monday(today)),
        ("This month", today.replace(day=1)),
        ("This year", today.replace(month=1, day=1)),
    )
    columns = [[a for a in activities if start <= day_of(a) <= today] for _, start in periods]
    rows = (
        ("Activities", lambda sel: f"{len(sel):,}"),
        ("Distance", total_distance),
        ("Time", lambda sel: format_duration(sum(a["duration_s"] for a in sel))),
    )
    right_edges = (220, 302, SMALL_W - PAD)

    body = [text(PAD, 30, "Training totals", "title")]
    body += [text(x, 60, label, "muted", "end") for x, (label, _) in zip(right_edges, periods)]
    for i, (label, value) in enumerate(rows):
        y = 88 + i * 26
        body.append(text(PAD, y, label, "muted"))
        body += [text(x, y, value(sel), "value", "end") for x, sel in zip(right_edges, columns)]

    current, longest = streaks({day_of(a) for a in activities}, today)
    border = THEMES[theme]["border"]
    body.append(f'<line x1="{PAD}" y1="158" x2="{SMALL_W - PAD}" y2="158" stroke="{border}"/>')
    for x, label, days in ((PAD, "Current streak", current), (SMALL_W / 2 + 8, "Longest streak", longest)):
        body.append(
            f'<text x="{x}" y="186"><tspan class="muted">{label}</tspan>'
            f'<tspan class="value" dx="8">{plural(days, "day")}</tspan></text>'
        )
    return svg(SMALL_W, SMALL_H, theme, "Training totals for this week, month and year, and streaks", body)


def weeks_ago(day: date, today: date) -> str:
    weeks = (monday(today) - monday(day)).days // 7
    if weeks <= 0:
        return "this week"
    if weeks == 1:
        return "last week"
    if weeks < 9:
        return f"{weeks} weeks ago"
    months = (today.year - day.year) * 12 + today.month - day.month
    if months < 12:
        return f"{months} months ago"
    return f"{plural(months // 12, 'year')} ago"


def recent(activities: list[dict], today: date, theme: str) -> str:
    dot = THEMES[theme]["levels"][3]
    body = [text(PAD, 30, "Recent activities", "title")]
    latest = sorted(activities, key=sort_key, reverse=True)[:RECENT_COUNT]
    if not latest:
        body.append(text(PAD, 62, "No activities yet", "muted"))
    for i, activity in enumerate(latest):
        y = 62 + i * 30
        body.append(f'<circle cx="{PAD + 5}" cy="{y - 4}" r="4" fill="{dot}"/>')
        body.append(text(PAD + 18, y, activity_label(activity)))
        body.append(text(SMALL_W - PAD, y, weeks_ago(day_of(activity), today), "muted", "end"))
    return svg(SMALL_W, SMALL_H, theme, "My five most recent activities", body)


def render_all(activities: list[dict], today: date, out_dir: Path = CARDS_DIR) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for theme in THEMES:
        for name, render in (("heatmap", heatmap), ("stats", stats), ("recent", recent)):
            (out_dir / f"{name}-{theme}.svg").write_text(render(activities, today, theme))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--today", type=date.fromisoformat, default=today())
    parser.add_argument("--data", type=Path, default=DATA_FILE)
    parser.add_argument("--out", type=Path, default=CARDS_DIR)
    args = parser.parse_args()
    render_all(load_activities(args.data), args.today, args.out)
