#!/usr/bin/env python3
"""Generate light/dark contribution heatmap SVGs from the GitHub GraphQL API.

Run by .github/workflows/graphics.yml daily. Needs GITHUB_TOKEN in the env.
"""
import json
import os
import urllib.request

from theme import THEMES, group, rect, svg_open, text

USER = "ex3lite"

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel weekday } }
      }
    }
  }
}
"""

LEVEL_INDEX = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DAY_LABELS = {1: "Mon", 3: "Wed", 5: "Fri"}

W, H = 900, 232
CELL, STEP = 11, 14
LEFT, TOP = 62, 78


def fetch_calendar():
    token = os.environ["GITHUB_TOKEN"]
    body = json.dumps({"query": QUERY, "variables": {"login": USER}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        data = json.load(resp)
    if data.get("errors"):
        raise SystemExit(f"GraphQL errors: {data['errors']}")
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def render(calendar, key):
    c = THEMES[key]
    weeks = calendar["weeks"]
    total = calendar["totalContributions"]
    parts = [
        svg_open(W, H, "contribution heatmap"),
        rect(0.5, 0.5, W - 1, H - 1, rx=14, fill=c["panel"], stroke=c["line"]),
        text(24, 34, "$ gh contributions --last-year", size=12.5, fill=c["green"]),
        text(W - 24, 34, f"{group(total)} contributions", size=12, fill=c["fg"], anchor="end"),
        rect(1, 50, W - 2, 1, fill=c["line"]),
    ]

    prev_month = None
    for wi, week in enumerate(weeks):
        month = int(week["contributionDays"][0]["date"][5:7])
        if month != prev_month:
            # Skip a label crammed into the very first column edge.
            if prev_month is not None or wi == 0:
                parts.append(text(LEFT + wi * STEP, 68, MONTHS[month - 1], size=10, fill=c["dim"]))
            prev_month = month

    for weekday, label in DAY_LABELS.items():
        parts.append(text(24, TOP + weekday * STEP + 9, label, size=10, fill=c["dim"]))

    for wi, week in enumerate(weeks):
        for day in week["contributionDays"]:
            fill = c["cells"][LEVEL_INDEX[day["contributionLevel"]]]
            parts.append(
                f'<rect x="{LEFT + wi * STEP}" y="{TOP + day["weekday"] * STEP}" '
                f'width="{CELL}" height="{CELL}" rx="2" fill="{fill}">'
                f'<title>{day["date"]}: {day["contributionCount"]}</title></rect>'
            )

    # Lay the legend out from the right edge so the run of cells never collides
    # with the right-anchored "more" label.
    lx = W - 24 - 24 - 10 - (5 * 15 - 4)
    parts.append(text(lx - 10, 206, "less", size=10, fill=c["dim"], anchor="end"))
    for i in range(5):
        parts.append(rect(lx + i * 15, 196, CELL, CELL, rx=2, fill=c["cells"][i]))
    parts.append(text(W - 24, 206, "more", size=10, fill=c["dim"], anchor="end"))

    parts.append("</svg>")
    return "".join(parts)


def main():
    calendar = fetch_calendar()
    for key in THEMES:
        path = f"assets/heatmap-{key}.svg"
        with open(path, "w") as f:
            f.write(render(calendar, key))
        print(f"wrote {path} ({calendar['totalContributions']} contributions)")


if __name__ == "__main__":
    main()
