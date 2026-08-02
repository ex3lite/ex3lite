#!/usr/bin/env python3
"""Generate the profile's stat SVGs (heatmap, stats card, top languages) in
light/dark themes from the GitHub GraphQL API.

Self-hosted replacement for ghchart / github-readme-stats, whose public
instances regularly 503. Run by .github/workflows/heatmap.yml daily.
Needs GITHUB_TOKEN in the env.
"""
import json
import os
import urllib.request

USER = "ex3lite"

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel weekday } }
      }
    }
    pullRequests { totalCount }
    issues { totalCount }
    repositoriesContributedTo(contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]) {
      totalCount
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
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
    "light": {
        "text": "#57606a",
        "title": "#24292f",
        "accent": "#2c5364",
        "bar_bg": "#ebedf0",
        "cells": ["#ebedf0", "#c7e7f1", "#8fd3e6", "#45a5c9", "#2c5364"],
    },
    "dark": {
        "text": "#8b949e",
        "title": "#e6edf3",
        "accent": "#3ed3ec",
        "bar_bg": "#21262d",
        "cells": ["#1c2128", "#0b3a47", "#12606f", "#1f93a8", "#3ed3ec"],
    },
}

FONT = 'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif"'
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DAY_LABELS = {1: "Mon", 3: "Wed", 5: "Fri"}

CELL = 11
GAP = 3
STEP = CELL + GAP
LEFT = 34
TOP = 22


def fetch_user():
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
    return data["data"]["user"]


def render_heatmap(calendar, theme):
    weeks = calendar["weeks"]
    width = LEFT + len(weeks) * STEP + 2
    height = TOP + 7 * STEP + 16
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        f'<g {FONT} font-size="10" fill="{theme["text"]}">',
    ]

    prev_month = None
    for wi, week in enumerate(weeks):
        month = int(week["contributionDays"][0]["date"][5:7])
        if month != prev_month:
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
    parts.append("</g></svg>")
    return "".join(parts)


def render_stats_card(rows, theme):
    width, pad = 375, 22
    height = 60 + len(rows) * 27
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        f'<g {FONT}>',
        f'<text x="{pad}" y="34" font-size="15" font-weight="600" '
        f'fill="{theme["title"]}">GitHub Stats</text>',
    ]
    for i, (label, value) in enumerate(rows):
        y = 66 + i * 27
        parts.append(
            f'<text x="{pad}" y="{y}" font-size="13" fill="{theme["text"]}">{label}</text>'
        )
        parts.append(
            f'<text x="{width - pad}" y="{y}" font-size="13" font-weight="600" '
            f'text-anchor="end" fill="{theme["accent"]}">{value:,}</text>'
        )
    parts.append("</g></svg>")
    return "".join(parts)


def render_langs_card(langs, theme):
    width, pad = 375, 22
    bar_y, bar_h = 52, 10
    bar_w = width - 2 * pad
    legend_y = 84
    rows = (len(langs) + 1) // 2
    height = legend_y + rows * 25
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        f'<defs><clipPath id="bar"><rect x="{pad}" y="{bar_y}" width="{bar_w}" '
        f'height="{bar_h}" rx="5"/></clipPath></defs>',
        f'<g {FONT}>',
        f'<text x="{pad}" y="34" font-size="15" font-weight="600" '
        f'fill="{theme["title"]}">Top Languages</text>',
        f'<rect x="{pad}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="5" '
        f'fill="{theme["bar_bg"]}"/>',
    ]
    x = float(pad)
    for name, pct, color in langs:
        w = bar_w * pct / 100
        parts.append(
            f'<rect x="{x:.1f}" y="{bar_y}" width="{w:.1f}" height="{bar_h}" '
            f'fill="{color}" clip-path="url(#bar)"/>'
        )
        x += w
    for i, (name, pct, color) in enumerate(langs):
        cx = pad + (i % 2) * (bar_w // 2)
        cy = legend_y + (i // 2) * 25
        parts.append(f'<circle cx="{cx + 5}" cy="{cy - 4}" r="5" fill="{color}"/>')
        parts.append(
            f'<text x="{cx + 16}" y="{cy}" font-size="12" fill="{theme["text"]}">'
            f'{name} <tspan font-weight="600" fill="{theme["title"]}">{pct:.1f}%</tspan></text>'
        )
    parts.append("</g></svg>")
    return "".join(parts)


def main():
    user = fetch_user()
    coll = user["contributionsCollection"]
    calendar = coll["contributionCalendar"]

    stars = sum(r["stargazerCount"] for r in user["repositories"]["nodes"])
    commits_year = coll["totalCommitContributions"] + coll["restrictedContributionsCount"]
    rows = [
        ("Contributions (last year)", calendar["totalContributions"]),
        ("Commits (last year)", commits_year),
        ("Pull requests", user["pullRequests"]["totalCount"]),
        ("Issues", user["issues"]["totalCount"]),
        ("Stars earned", stars),
        ("Contributed to", user["repositoriesContributedTo"]["totalCount"]),
    ]

    sizes, colors = {}, {}
    for repo in user["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            sizes[name] = sizes.get(name, 0) + edge["size"]
            colors[name] = edge["node"]["color"] or "#8b949e"
    total_size = sum(sizes.values()) or 1
    langs = [
        (name, 100 * size / total_size, colors[name])
        for name, size in sorted(sizes.items(), key=lambda kv: -kv[1])[:6]
    ]

    for theme_name, theme in THEMES.items():
        outputs = {
            f"heatmap-{theme_name}.svg": render_heatmap(calendar, theme),
            f"stats-{theme_name}.svg": render_stats_card(rows, theme),
            f"langs-{theme_name}.svg": render_langs_card(langs, theme),
        }
        for path, svg in outputs.items():
            with open(path, "w") as f:
                f.write(svg)
            print(f"wrote {path}")


if __name__ == "__main__":
    main()
