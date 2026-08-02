#!/usr/bin/env python3
"""Generate the stats and top-languages cards from the GitHub GraphQL API.

Replaces github-readme-stats: no third-party service, no rate limit, no camo
cache surprises. Run by .github/workflows/graphics.yml. Needs GITHUB_TOKEN.
"""
import datetime as dt
import json
import os
import urllib.request

from theme import THEMES, cw, group, rect, svg_open, text

USER = "ex3lite"
W, H = 440, 240

QUERY = """
query($login: String!) {
  user(login: $login) {
    id
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      totalPullRequestContributions
      totalIssueContributions
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
      totalCount
      nodes { stargazerCount }
    }
  }
}
"""

# Org repos the affiliations listing may not surface; skipped silently when the
# token cannot see them (e.g. the nightly fine-grained PAT scoped to ex3lite).
EXTRA_REPOS = [
    ("Matrena-VPN", "backend_ai"),
    ("Matrena-VPN", "kakadu_cbackend"),
    ("Matrena-VPN", "cbackend"),
]

REPO_LANG_FRAGMENT = """
fragment RepoLang on Repository {
  nameWithOwner
  defaultBranchRef { target { ... on Commit { history(author: $author, since: $since) { totalCount } } } }
  languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
    totalSize
    edges { size node { name } }
  }
}
"""

LANG_QUERY = (
    """
query($login: String!, $author: CommitAuthor!, $since: GitTimestamp!) {
  user(login: $login) {
    repositories(first: 100, affiliations: [OWNER, COLLABORATOR, ORGANIZATION_MEMBER],
                 isFork: false, orderBy: {field: PUSHED_AT, direction: DESC}) {
      nodes { ...RepoLang }
    }
  }
"""
    + "".join(
        f'  x{i}: repository(owner: "{owner}", name: "{name}") {{ ...RepoLang }}\n'
        for i, (owner, name) in enumerate(EXTRA_REPOS)
    )
    + "}\n"
    + REPO_LANG_FRAGMENT
)


def gql(query, variables, allow_partial=False):
    token = os.environ["GITHUB_TOKEN"]
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        data = json.load(resp)
    # allow_partial: NOT_FOUND on an EXTRA_REPOS alias just means this token
    # cannot see that repo — usable data still comes back for the rest.
    if data.get("errors") and not (allow_partial and data.get("data")):
        raise SystemExit(f"GraphQL errors: {data['errors']}")
    return data["data"]


def fetch():
    return gql(QUERY, {"login": USER})["user"]


def authored_language_weights(user_id):
    """Languages weighted by MY authored commits per repository (last year).

    GraphQL hides the per-repo breakdown of private contributions behind
    restrictedContributionsCount for every token kind, so we walk default-branch
    history with an author filter instead: every repo the token can see, plus
    the EXTRA_REPOS org list. Weight = my commits x language share of the repo.
    """
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=365)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    data = gql(
        LANG_QUERY,
        {"login": USER, "author": {"id": user_id}, "since": since},
        allow_partial=True,
    )
    nodes = list(data["user"]["repositories"]["nodes"])
    nodes += [data.get(f"x{i}") for i in range(len(EXTRA_REPOS))]
    sizes, seen = {}, set()
    for node in nodes:
        if not node or node["nameWithOwner"] in seen or not node["defaultBranchRef"]:
            continue
        seen.add(node["nameWithOwner"])
        commits = node["defaultBranchRef"]["target"]["history"]["totalCount"]
        if not commits:
            continue
        langs = node["languages"]
        total = langs["totalSize"] or 1
        for edge in langs["edges"]:
            name = edge["node"]["name"]
            sizes[name] = sizes.get(name, 0) + edge["size"] / total * commits
    return sizes


def collect(user):
    cc = user["contributionsCollection"]
    repos = user["repositories"]
    stars = sum(n["stargazerCount"] for n in repos["nodes"])
    sizes = authored_language_weights(user["id"])
    year = dt.date.today().year
    rows = [
        (f"commits ({year})", cc["totalCommitContributions"] + cc["restrictedContributionsCount"]),
        ("pull requests", cc["totalPullRequestContributions"]),
        ("issues closed", cc["totalIssueContributions"]),
        ("repositories", repos["totalCount"]),
        ("stars earned", stars),
    ]
    total = sum(sizes.values()) or 1
    ranked = sorted(sizes.items(), key=lambda kv: -kv[1])[:4]
    langs = [(name.lower(), 100.0 * size / total) for name, size in ranked]
    rest = 100.0 - sum(p for _, p in langs)
    if rest > 0.05:
        langs.append(("other", rest))
    return rows, langs


def render_stats(rows, key):
    c = THEMES[key]
    parts = [
        svg_open(W, H, "github stats"),
        rect(0.5, 0.5, W - 1, H - 1, rx=11, fill=c["panel"], stroke=c["line"]),
        text(20, 32, f"$ gh stats --user {USER}", size=12, fill=c["green"]),
        rect(1, 48, W - 2, 1, fill=c["line"]),
    ]
    y = 76
    for label, value in rows:
        val = group(value)
        kx = 24 + round(len(label) * cw(12.5)) + 10
        vx = W - 24 - round(len(val) * cw(13)) - 10
        parts += [
            text(24, y, label, size=12.5, fill=c["dim"]),
            rect(kx, y - 4, max(8, vx - kx), 1, fill=c["line"]),
            text(W - 24, y, val, size=13, fill=c["fg"], anchor="end", weight=700),
        ]
        y += 26
    parts += [
        rect(24, 200, W - 48, 1, fill=c["line"]),
        text(24, 222, "private activity included", size=10.5, fill=c["dim"]),
        text(W - 24, 222, dt.date.today().isoformat(), size=10.5, fill=c["dim"], anchor="end"),
        "</svg>",
    ]
    return "".join(parts)


def render_langs(langs, key):
    c = THEMES[key]
    # No "line" here: it is the panel border colour and would vanish on the panel.
    ramp = [c["green"], c["amber"], c["cells"][3], c["muted"], c["dim"]]
    parts = [
        svg_open(W, H, "top languages"),
        rect(0.5, 0.5, W - 1, H - 1, rx=11, fill=c["panel"], stroke=c["line"]),
        text(20, 32, "$ gh langs --authored --last-year", size=12, fill=c["green"]),
        rect(1, 48, W - 2, 1, fill=c["line"]),
    ]
    x = 24.0
    for i, (_, pct) in enumerate(langs):
        w = (W - 48) * pct / 100
        parts.append(rect(round(x, 2), 64, round(max(2, w - 2), 2), 10, rx=2, fill=ramp[i % 5]))
        x += w
    y = 110
    for i, (name, pct) in enumerate(langs):
        parts += [
            rect(24, y - 9, 10, 10, rx=2, fill=ramp[i % 5]),
            text(42, y, name, size=12.5, fill=c["dim"]),
            text(W - 24, y, f"{pct:.1f} %", size=12.5, fill=c["fg"], anchor="end"),
        ]
        y += 24
    parts.append("</svg>")
    return "".join(parts)


def main():
    rows, langs = collect(fetch())
    for key in THEMES:
        for path, svg in (
            (f"assets/stats-{key}.svg", render_stats(rows, key)),
            (f"assets/langs-{key}.svg", render_langs(langs, key)),
        ):
            with open(path, "w") as f:
                f.write(svg)
            print(f"wrote {path}")


if __name__ == "__main__":
    main()
