#!/usr/bin/env python3
"""Generate light/dark contribution heatmap SVGs from the GitHub GraphQL API.

Run by .github/workflows/heatmap.yml daily. Needs GITHUB_TOKEN in the env.
"""
import json
import os
import urllib.request

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

# Steel-blue ramp to match the profile header gradient.
THEMES = {
    "light": {"text": "#57606a", "cells": ["#ebedf0", "#c7e7f1", "#8fd3e6", "#45a5c9", "#2c5364"]},
    "dark": {"text": "#8b949e", "cells": ["#1c2128", "#0b3a47", "#12606f", "#1f93a8", "#3ed3ec"]},
}

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DAY_LABELS = {1: "Mon", 3: "Wed", 5: "Fri"}

CELL = 11
GAP = 3
STEP = CELL + GAP
LEFT = 34
TOP = 22


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


def render(calendar, theme):
    weeks = calendar["weeks"]
    width = LEFT + len(weeks) * STEP + 2
    height = TOP + 7 * STEP + 16
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        f'<style>text{{font:10px -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;'
        f'fill:{theme["text"]}}}</style>',
    ]

    prev_month = None
    for wi, week in enumerate(weeks):
        month = int(week["contributionDays"][0]["date"][5:7])
        if month != prev_month:
            # Skip a label crammed into the very first column edge.
            if prev_month is not None or wi == 0:
                parts.append(f'<text x="{LEFT + wi * STEP}" y="12">{MONTHS[month - 1]}</text>')
            prev_month = month

    for weekday, label in DAY_LABELS.items():
        parts.append(f'<text x="0" y="{TOP + weekday * STEP + CELL - 2}">{label}</text>')

    for wi, week in enumerate(weeks):
        for day in week["contributionDays"]:
            color = theme["cells"][LEVEL_INDEX[day["contributionLevel"]]]
            parts.append(
                f'<rect x="{LEFT + wi * STEP}" y="{TOP + day["weekday"] * STEP}" '
                f'width="{CELL}" height="{CELL}" rx="2" fill="{color}">'
                f'<title>{day["date"]}: {day["contributionCount"]}</title></rect>'
            )

    total = calendar["totalContributions"]
    parts.append(
        f'<text x="{width - 2}" y="{height - 4}" text-anchor="end">'
        f"{total} contributions in the last year</text>"
    )
    parts.append("</svg>")
    return "".join(parts)


def main():
    calendar = fetch_calendar()
    for name, theme in THEMES.items():
        path = f"heatmap-{name}.svg"
        with open(path, "w") as f:
            f.write(render(calendar, theme))
        print(f"wrote {path} ({calendar['totalContributions']} contributions)")


if __name__ == "__main__":
    main()
