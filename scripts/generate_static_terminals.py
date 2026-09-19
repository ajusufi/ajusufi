#!/usr/bin/env python3
"""Generate the static terminal-style SVG cards used by the profile README."""

from __future__ import annotations

import html
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ICON_URL = "https://cdn.jsdelivr.net/npm/simple-icons@v16/icons/{slug}.svg"

BG = "#0b0b0b"
TOPBAR = "#151515"
PINK = "#ff69b4"
TEXT = "#f2f2f2"
SECONDARY = "#a6a6a6"
MUTED = "#666666"
DIVIDER = "#303030"


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def terminal_start(height: int, title: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{height}" viewBox="0 0 1200 {height}" role="img">',
        f'  <title>{esc(title)}</title>',
        f'  <rect width="1200" height="{height}" fill="{BG}"/>',
        f'  <rect width="1200" height="78" fill="{TOPBAR}"/>',
        f'  <line x1="0" y1="78" x2="1200" y2="78" stroke="{DIVIDER}" stroke-width="2"/>',
        f'  <g fill="none" stroke="#b8b8b8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">',
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
        f'  <text x="600" y="47" text-anchor="middle" fill="#d0d0d0" font-size="22" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">{esc(title)}</text>',
    ]


def prompt(command: str, y: int = 130) -> list[str]:
    return [
        '  <g font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="24">',
        f'    <text x="30" y="{y}" fill="{PINK}" font-weight="600">alt@github</text>',
        f'    <text x="179" y="{y}" fill="#8c8c8c">:</text>',
        f'    <text x="193" y="{y}" fill="#c8c8c8">~</text>',
        f'    <text x="210" y="{y}" fill="#8c8c8c">$</text>',
        f'    <text x="238" y="{y}" fill="{TEXT}">{esc(command)}</text>',
        '  </g>',
    ]


def terminal_end(height: int) -> list[str]:
    return [
        f'  <text x="1170" y="{height - 28}" text-anchor="end" fill="#555555" font-size="18" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">bash</text>',
        '</svg>',
    ]


def write_svg(name: str, lines: list[str]) -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / name).write_text("\n".join(lines) + "\n", encoding="utf-8")


def icon_paths(slug: str) -> list[str]:
    try:
        request = urllib.request.Request(
            ICON_URL.format(slug=slug), headers={"User-Agent": "ajusufi-profile-generator"}
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            root = ET.fromstring(response.read())
    except (urllib.error.HTTPError, urllib.error.URLError, ET.ParseError, TimeoutError):
        return []

    paths: list[str] = []
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1] == "path" and node.attrib.get("d"):
            paths.append(node.attrib["d"])
    return paths


def initials(label: str) -> str:
    words = label.replace("+", " plus ").replace("-", " ").split()
    if len(words) > 1:
        return "".join(word[0] for word in words[:2]).upper()
    return label[:2].upper()


def icon_item(center_x: int, y: int, label: str, slug: str) -> list[str]:
    paths = icon_paths(slug)
    result: list[str] = []
    if paths:
        result.append(
            f'  <g transform="translate({center_x - 21} {y}) scale(1.75)" fill="#d0d0d0">'
        )
        result.extend(f'    <path d="{esc(path)}"/>' for path in paths)
        result.append('  </g>')
    else:
        result.extend(
            [
                f'  <rect x="{center_x - 21}" y="{y}" width="42" height="42" fill="none" stroke="#555555" stroke-width="2"/>',
                f'  <text x="{center_x}" y="{y + 28}" text-anchor="middle" fill="#d0d0d0" font-size="17" font-weight="700" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">{esc(initials(label))}</text>',
            ]
        )
    result.append(
        f'  <text x="{center_x}" y="{y + 67}" text-anchor="middle" fill="{SECONDARY}" font-size="16" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">{esc(label)}</text>'
    )
    return result


def icon_row(category: str, y: int, items: list[tuple[str, str]]) -> list[str]:
    result = [
        f'  <text x="30" y="{y + 30}" fill="{MUTED}" font-size="18" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">{esc(category)}/</text>'
    ]
    start_x = 220
    step = 160
    for index, (label, slug) in enumerate(items):
        result.extend(icon_item(start_x + index * step, y, label, slug))
    return result


def generate_about() -> None:
    height = 340
    lines = terminal_start(height, "alt@github: ~/about")
    lines += prompt("cat ~/about.txt")
    lines += [
        f'  <text x="30" y="190" fill="{TEXT}" font-size="23" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">Artificial Intelligence BSc student at JKU Linz.</text>',
        f'  <text x="30" y="232" fill="{SECONDARY}" font-size="21" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">Turning coursework into code, experiments, and public progress.</text>',
        f'  <text x="30" y="274" fill="{SECONDARY}" font-size="21" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">Current focus: machine learning, robotics, and embedded systems.</text>',
    ]
    lines += terminal_end(height)
    write_svg("about.svg", lines)


def generate_deep_ml() -> None:
    height = 430
    lines = terminal_start(height, "alt@github: ~/deep-ml")
    lines += prompt("./deep-ml --status")
    fields = [
        ("project", "LeetCode-style machine-learning practice"),
        ("approach", "learn -> implement -> test -> document -> repeat"),
        ("status", "active"),
        ("repository", "github.com/ajusufi/deep-ml"),
    ]
    y = 190
    for key, value in fields:
        lines.append(
            f'  <text x="30" y="{y}" fill="{MUTED}" font-size="21" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">{esc(key):<12}</text>'
        )
        lines.append(
            f'  <text x="210" y="{y}" fill="{TEXT if key in {"project", "status"} else SECONDARY}" font-size="21" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">{esc(value)}</text>'
        )
        y += 48
    lines += terminal_end(height)
    write_svg("deep-ml-cover.svg", lines)


def generate_skills() -> None:
    height = 570
    lines = terminal_start(height, "alt@github: ~/skills")
    lines += prompt("ls --icons ~/skills")
    lines += icon_row(
        "languages",
        170,
        [("Python", "python"), ("TypeScript", "typescript"), ("C++", "cplusplus"), ("C", "c"), ("Prolog", "prolog")],
    )
    lines += icon_row(
        "web",
        300,
        [("Svelte", "svelte"), ("React", "react"), ("Tailwind CSS", "tailwindcss")],
    )
    lines += icon_row(
        "ml-data",
        430,
        [("NumPy", "numpy"), ("pandas", "pandas"), ("PyTorch", "pytorch"), ("scikit-learn", "scikitlearn"), ("Matplotlib", "matplotlib"), ("Seaborn", "seaborn")],
    )
    lines += terminal_end(height)
    write_svg("skills.svg", lines)


def generate_tools() -> None:
    height = 590
    lines = terminal_start(height, "alt@github: ~/tools")
    lines += prompt("ls --icons ~/tools")
    lines += icon_row(
        "robotics",
        170,
        [("ROS 2", "ros"), ("Foxglove", "foxglove"), ("RViz 2", "rviz"), ("Gazebo", "gazebo"), ("OpenCV", "opencv")],
    )
    lines += icon_row(
        "embedded",
        310,
        [("STM32", "stmicroelectronics"), ("Arduino", "arduino"), ("PlatformIO", "platformio")],
    )
    lines += icon_row(
        "dev-tools",
        450,
        [("Docker", "docker"), ("PostgreSQL", "postgresql"), ("Git", "git"), ("GitHub", "github"), ("Linux", "linux")],
    )
    lines += terminal_end(height)
    write_svg("tools.svg", lines)


def generate_academic() -> None:
    height = 330
    lines = terminal_start(height, "alt@github: ~/academic")
    lines += prompt("ls ~/academic")
    entries = [("completed/", 30), ("currently-learning/", 350), ("up-next/", 790)]
    for label, x in entries:
        lines.append(
            f'  <text x="{x}" y="205" fill="{TEXT}" font-size="23" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">{esc(label)}</text>'
        )
        lines.append(
            f'  <text x="{x}" y="244" fill="{MUTED}" font-size="17" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">drwxr-xr-x</text>'
        )
    lines += terminal_end(height)
    write_svg("academic.svg", lines)


def generate_hobbies() -> None:
    height = 280
    lines = terminal_start(height, "alt@github: ~/hobbies")
    lines += prompt("ls -1 ~/hobbies")
    for x, label in zip((30, 280, 530, 830), ("music/", "gaming/", "electronics/", "robotics/")):
        lines.append(
            f'  <text x="{x}" y="202" fill="{TEXT}" font-size="23" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">{label}</text>'
        )
    lines += terminal_end(height)
    write_svg("hobbies.svg", lines)


def main() -> int:
    generate_about()
    generate_deep_ml()
    generate_skills()
    generate_tools()
    generate_academic()
    generate_hobbies()
    return 0


if __name__ == "__main__":
    sys.exit(main())

