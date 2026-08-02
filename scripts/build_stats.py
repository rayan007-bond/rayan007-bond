#!/usr/bin/env python3
"""Generate assets/stats.svg from live GitHub data, styled to match the profile."""

import json
import os
import urllib.request
from datetime import datetime, timezone
from xml.sax.saxutils import escape

LOGIN = os.environ.get("GH_LOGIN", "rayan007-bond")
TOKEN = os.environ["GH_TOKEN"]
OUT = "assets/stats.svg"

BG, PANEL, RULE = "#0B1519", "#13242A", "#24404A"
SAND, MINT, INK, MUTED = "#E9B872", "#7FD1C1", "#E6EEF0", "#7E9AA3"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
SERIF = "Georgia, 'Times New Roman', serif"

# palette ramp for language segments, sand -> mint
RAMP = ["#E9B872", "#D9B489", "#B9BC9C", "#98C4AE", "#7FD1C1", "#4E8F86"]

QUERY = """
query($login:String!){
  user(login:$login){
    followers{ totalCount }
    contributionsCollection{ contributionCalendar{ totalContributions } }
    repositories(first:100, ownerAffiliations:OWNER, isFork:false, privacy:PUBLIC){
      totalCount
      nodes{
        stargazerCount
        languages(first:10, orderBy:{field:SIZE, direction:DESC}){
          edges{ size node{ name } }
        }
      }
    }
  }
}
"""


def fetch():
    body = json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": LOGIN,
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload:
        raise SystemExit(f"GitHub API error: {payload['errors']}")
    return payload["data"]["user"]


def summarise(user):
    repos = user["repositories"]["nodes"]
    stars = sum(r["stargazerCount"] for r in repos)

    sizes = {}
    for repo in repos:
        for edge in repo["languages"]["edges"]:
            sizes[edge["node"]["name"]] = sizes.get(edge["node"]["name"], 0) + edge["size"]

    ranked = sorted(sizes.items(), key=lambda kv: kv[1], reverse=True)[:6]
    total = sum(v for _, v in ranked) or 1
    langs = [(name, size / total * 100) for name, size in ranked]

    return {
        "repos": user["repositories"]["totalCount"],
        "stars": stars,
        "contributions": user["contributionsCollection"]["contributionCalendar"]["totalContributions"],
        "followers": user["followers"]["totalCount"],
        "langs": langs,
    }


def metric(x, value, label, delay):
    return f"""
  <g opacity="0">
    <animate attributeName="opacity" from="0" to="1" dur="0.6s" begin="{delay}s" fill="freeze"/>
    <text x="{x}" y="112" font-family="{SERIF}" font-size="46" fill="{INK}">{value}</text>
    <text x="{x}" y="136" font-family="{MONO}" font-size="10" letter-spacing="2.6" fill="{MUTED}">{label}</text>
  </g>"""


def render(d):
    stamp = datetime.now(timezone.utc).strftime("%d %b %Y")

    metrics = "".join([
        metric(60, d["repos"], "PUBLIC REPOS", 0.2),
        metric(340, d["stars"], "STARS EARNED", 0.35),
        metric(620, d["contributions"], "CONTRIBUTIONS / YR", 0.5),
        metric(960, d["followers"], "FOLLOWERS", 0.65),
    ])

    bar, legend, x, lx = [], [], 60.0, 60.0
    width = 1080.0
    for i, (name, pct) in enumerate(d["langs"]):
        seg = width * pct / 100
        colour = RAMP[i % len(RAMP)]
        bar.append(
            f'<rect x="{x:.1f}" y="186" width="0" height="10" rx="2" fill="{colour}">'
            f'<animate attributeName="width" from="0" to="{seg:.1f}" dur="1.1s" '
            f'begin="{0.8 + i * 0.12:.2f}s" fill="freeze"/></rect>'
        )
        legend.append(
            f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" dur="0.5s" '
            f'begin="{1.2 + i * 0.1:.2f}s" fill="freeze"/>'
            f'<circle cx="{lx:.0f}" cy="228" r="4" fill="{colour}"/>'
            f'<text x="{lx + 14:.0f}" y="232" font-family="{MONO}" font-size="11.5" '
            f'fill="{MUTED}">{escape(name)} {pct:.0f}%</text></g>'
        )
        x += seg
        lx += 40 + len(name) * 7.5

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 260" width="1200" height="260" role="img" aria-label="GitHub statistics for {escape(LOGIN)}">
  <defs><clipPath id="p"><rect width="1200" height="260" rx="12" ry="12"/></clipPath></defs>
  <g clip-path="url(#p)">
    <rect width="1200" height="260" fill="{BG}"/>
    <rect width="1200" height="52" fill="{PANEL}"/>
    <line x1="0" y1="52" x2="1200" y2="52" stroke="{RULE}" stroke-width="1"/>
    <circle cx="34" cy="26" r="4" fill="{MINT}">
      <animate attributeName="opacity" values="0.3;1;0.3" dur="2.5s" repeatCount="indefinite"/>
    </circle>
    <text x="52" y="31" font-family="{MONO}" font-size="12" letter-spacing="2.6" fill="{SAND}">LIVE SIGNAL</text>
    <text x="1140" y="31" text-anchor="end" font-family="{MONO}" font-size="11" fill="{MUTED}">synced {stamp}</text>
{metrics}
    <text x="60" y="172" font-family="{MONO}" font-size="10" letter-spacing="2.6" fill="{SAND}">LANGUAGE DISTRIBUTION</text>
    <rect x="60" y="186" width="1080" height="10" rx="2" fill="{RULE}" fill-opacity="0.5"/>
    {''.join(bar)}
    {''.join(legend)}
  </g>
</svg>
"""


if __name__ == "__main__":
    data = summarise(fetch())
    os.makedirs("assets", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(render(data))
    print(f"wrote {OUT}: {data['repos']} repos, {data['stars']} stars, "
          f"{data['contributions']} contributions, {len(data['langs'])} languages")
