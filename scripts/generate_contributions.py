#!/usr/bin/env python3
"""Generate a terminal-style contribution calendar from GitHub data."""

from __future__ import annotations

import argparse
import calendar
import datetime as dt
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


GRAPHQL_URL = "https://api.github.com/graphql"
PUBLIC_URL = "https://github.com/users/{username}/contributions"

BG = "#0b0b0b"
TOPBAR = "#151515"
PINK = "#ff69b4"
TEXT = "#f2f2f2"
SECONDARY = "#a6a6a6"
MUTED = "#666666"
DIVIDER = "#303030"
LEVEL_COLORS = ["#202024", "#482137", "#8f315f", "#d94692", PINK]


@dataclass(frozen=True)
class Day:
    date: dt.date
    count: int
    level: int


def request_bytes(url: str, *, data: bytes | None = None, headers: dict[str, str] | None = None) -> bytes:
    request = urllib.request.Request(
        url,
        data=data,
        headers={"User-Agent": "ajusufi-profile-contributions", **(headers or {})},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def fetch_graphql(username: str, token: str) -> tuple[list[Day], int]:
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                contributionCount
                contributionLevel
                date
              }
            }
          }
        }
      }
    }
    """
    payload = json.dumps({"query": query, "variables": {"login": username}}).encode("utf-8")
    raw = request_bytes(
        GRAPHQL_URL,
        data=payload,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    response = json.loads(raw)
    if response.get("errors"):
        raise RuntimeError(response["errors"])
    calendar_data = response["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    level_map = {
        "NONE": 0,
        "FIRST_QUARTILE": 1,
        "SECOND_QUARTILE": 2,
        "THIRD_QUARTILE": 3,
        "FOURTH_QUARTILE": 4,
    }
    days = [
        Day(
            date=dt.date.fromisoformat(day["date"]),
            count=int(day["contributionCount"]),
            level=level_map[day["contributionLevel"]],
        )
        for week in calendar_data["weeks"]
        for day in week["contributionDays"]
    ]
    return days, int(calendar_data["totalContributions"])


def fetch_public(username: str) -> tuple[list[Day], int]:
    source = request_bytes(PUBLIC_URL.format(username=username)).decode("utf-8", errors="replace")
    cells = re.findall(
        r'<td[^>]*data-date="(?P<date>\d{4}-\d{2}-\d{2})"[^>]*id="(?P<id>[^"]+)"[^>]*data-level="(?P<level>[0-4])"[^>]*>',
        source,
    )
    tooltip_counts: dict[str, int] = {}
    for element_id, text in re.findall(r'<tool-tip[^>]*for="([^"]+)"[^>]*>(.*?)</tool-tip>', source, re.S):
        plain = re.sub(r"<[^>]+>", "", text).strip()
        match = re.match(r"(\d+) contributions? on ", plain)
        tooltip_counts[element_id] = int(match.group(1)) if match else 0

    unique: dict[dt.date, Day] = {}
    for date_text, element_id, level_text in cells:
        date = dt.date.fromisoformat(date_text)
        unique[date] = Day(date=date, count=tooltip_counts.get(element_id, 0), level=int(level_text))
    if not unique:
        raise RuntimeError("GitHub's public contribution calendar returned no day cells")
    days = sorted(unique.values(), key=lambda item: item.date)
    return days, sum(day.count for day in days)


def load_contributions(username: str) -> tuple[list[Day], int, str]:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if token:
        try:
            days, total = fetch_graphql(username, token)
            return days, total, "GitHub GraphQL API"
        except (urllib.error.URLError, RuntimeError, KeyError, TypeError, ValueError) as error:
            print(f"GraphQL fetch failed; using public calendar: {error}", file=sys.stderr)
    days, total = fetch_public(username)
    return days, total, "public GitHub calendar"


def topbar(title: str) -> list[str]:
    return [
        f'  <rect width="1200" height="410" fill="{BG}"/>',
        f'  <rect width="1200" height="78" fill="{TOPBAR}"/>',
        f'  <line x1="0" y1="78" x2="1200" y2="78" stroke="{DIVIDER}" stroke-width="2"/>',
        '  <g fill="none" stroke="#b8b8b8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">',
        '    <line x1="27" y1="40" x2="45" y2="40"/>',
        '    <line x1="36" y1="31" x2="36" y2="49"/>',
        '    <line x1="1044" y1="40" x2="1058" y2="40"/>',
        '    <rect x="1100" y="33" width="14" height="14"/>',
        '    <line x1="1158" y1="33" x2="1172" y2="47"/>',
        '    <line x1="1172" y1="33" x2="1158" y2="47"/>',
        '  </g>',
        '  <g fill="#b8b8b8">',
        '    <circle cx="960" cy="40" r="1.4"/>',
        '    <circle cx="968" cy="40" r="1.4"/>',
        '    <circle cx="976" cy="40" r="1.4"/>',
        '  </g>',
        '  <line x1="1010" y1="22" x2="1010" y2="56" stroke="#3b3b3b" stroke-width="2"/>',
        f'  <text x="600" y="47" text-anchor="middle" fill="#d0d0d0" font-size="22" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">{html.escape(title)}</text>',
    ]


def render_svg(username: str, days: list[Day], total: int, source: str) -> str:
    by_date = {day.date: day for day in days}
    first_date = min(by_date)
    last_date = max(by_date)
    start = first_date - dt.timedelta(days=(first_date.weekday() + 1) % 7)
    end = last_date + dt.timedelta(days=(6 - ((last_date.weekday() + 1) % 7)))
    week_count = ((end - start).days // 7) + 1

    grid_x = 72
    grid_y = 192
    cell = 14
    step = min(19, max(14, (1090 - grid_x) // max(week_count, 1)))

    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="410" viewBox="0 0 1200 410" role="img" aria-labelledby="title description">',
        f'  <title id="title">{total} GitHub contributions by {html.escape(username)} in the last year</title>',
        f'  <desc id="description">Terminal-style GitHub contribution calendar generated from {html.escape(source)}.</desc>',
    ]
    lines += topbar("alt@github: ~/activity")
    lines += [
        '  <g font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="24">',
        f'    <text x="30" y="130" fill="{PINK}" font-weight="600">alt@github</text>',
        '    <text x="179" y="130" fill="#8c8c8c">:</text>',
        '    <text x="193" y="130" fill="#c8c8c8">~</text>',
        '    <text x="210" y="130" fill="#8c8c8c">$</text>',
        f'    <text x="238" y="130" fill="{TEXT}">./contributions.sh --since 1y</text>',
        '  </g>',
    ]

    for weekday, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        y = grid_y + weekday * step + cell - 2
        lines.append(
            f'  <text x="30" y="{y}" fill="{MUTED}" font-size="13" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">{label}</text>'
        )

    seen_months: set[tuple[int, int]] = set()
    current = start
    for column in range(week_count):
        week_date = start + dt.timedelta(days=column * 7)
        month_key = (week_date.year, week_date.month)
        if month_key not in seen_months and (column == 0 or week_date.day <= 7):
            seen_months.add(month_key)
            lines.append(
                f'  <text x="{grid_x + column * step}" y="174" fill="{MUTED}" font-size="13" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">{calendar.month_abbr[week_date.month]}</text>'
            )
        for row in range(7):
            date = current + dt.timedelta(days=column * 7 + row)
            day = by_date.get(date)
            color = LEVEL_COLORS[day.level] if day else BG
            lines.append(
                f'  <rect x="{grid_x + column * step}" y="{grid_y + row * step}" width="{cell}" height="{cell}" rx="2" fill="{color}"/>'
            )

    total_label = (
        f"{total} public contributions in the last year"
        if source == "public GitHub calendar"
        else f"{total} contributions in the last year"
    )
    lines += [
        f'  <text x="30" y="365" fill="{SECONDARY}" font-size="18" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">{total_label}</text>',
        '  <text x="1170" y="382" text-anchor="end" fill="#555555" font-size="18" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">bash</text>',
        '</svg>',
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", default="ajusufi")
    parser.add_argument("--output", type=Path, default=Path("assets/contributions.svg"))
    args = parser.parse_args()

    days, total, source = load_contributions(args.username)
    output = args.output if args.output.is_absolute() else Path.cwd() / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_svg(args.username, days, total, source), encoding="utf-8")
    print(f"Wrote {output} from {source} ({total} contributions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
