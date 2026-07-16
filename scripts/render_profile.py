#!/usr/bin/env python3
"""Render the final light/dark profile SVGs from modular source files.

Normal edits belong in profile.toml. The portrait and visual template remain
independent, so changing biography text does not require hand-editing either SVG.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError as exc:  # Python < 3.11
    raise SystemExit("Python 3.11 or newer is required.") from exc

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "profile.toml"
TEMPLATE_PATH = ROOT / "templates" / "profile.svg.tpl"
PORTRAIT_ASCII_PATH = ROOT / "assets" / "portrait_ascii.txt"
PORTRAIT_PATHS_PATH = ROOT / "assets" / "portrait_paths.svgfrag"
OUTPUTS = {
    "light": ROOT / "light_mode.svg",
    "dark": ROOT / "dark_mode.svg",
}

THEMES = {
    "light": {
        "BG": "#f6f8fa",
        "BORDER": "#d0d7de",
        "TEXT": "#24292f",
        "MUTED": "#8c959f",
        "KEY": "#9a4a00",
        "VALUE": "#0969da",
        "GREEN": "#1a7f37",
        "PORTRAIT": "#24292f",
        "LINE": "#57606a",
        "GLOW": "#afb8c1",
    },
    "dark": {
        "BG": "#0d1117",
        "BORDER": "#30363d",
        "TEXT": "#e6edf3",
        "MUTED": "#8b949e",
        "KEY": "#ffa657",
        "VALUE": "#79c0ff",
        "GREEN": "#56d364",
        "PORTRAIT": "#c9d1d9",
        "LINE": "#8b949e",
        "GLOW": "#30363d",
    },
}

API_ROOT = "https://api.github.com"
TIMEOUT_SECONDS = 20
KEY_WIDTH = 18
MAX_VALUE_LENGTH = 46


class RenderError(RuntimeError):
    """Raised for invalid configuration or rendering failures."""


def xml(value: object) -> str:
    """Escape user-controlled text for safe SVG/XML output."""
    return html.escape(str(value), quote=True)


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open("rb") as handle:
        config = tomllib.load(handle)

    required_tables = ("profile", "contact", "stats")
    for table in required_tables:
        if table not in config:
            raise RenderError(f"Missing [{table}] table in profile.toml.")

    if not config.get("sections"):
        raise RenderError("profile.toml must define at least one [[sections]] table.")

    return config


def validate_row(row: dict[str, Any], context: str) -> tuple[str, str]:
    key = str(row.get("key", "")).strip()
    value = str(row.get("value", "")).strip()
    if not key or not value:
        raise RenderError(f"{context} requires non-empty key and value fields.")
    if len(key) > KEY_WIDTH:
        raise RenderError(
            f"{context} key {key!r} is too long; maximum is {KEY_WIDTH} characters."
        )
    if len(value) > MAX_VALUE_LENGTH:
        raise RenderError(
            f"{context} value {value!r} is too long; maximum is "
            f"{MAX_VALUE_LENGTH} characters to preserve the fixed layout."
        )
    return key, value


def row_markup(y: int, key: str, value: str, value_class: str = "value") -> str:
    dots = " " + "." * max(2, KEY_WIDTH - len(key)) + " "
    return (
        f'    <tspan x="420" y="{y}" class="key">{xml(key)}</tspan>'
        f'<tspan class="muted">{xml(dots)}</tspan>'
        f'<tspan class="{value_class}">{xml(value)}</tspan>'
    )


def section_heading(y: int, title: str) -> str:
    suffix = "-" * max(3, 56 - len(title))
    return f'    <tspan x="420" y="{y}">- {xml(title)} {suffix}</tspan>'


def fetch_json(path: str, token: str) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "spyroskontakis-profile-renderer",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(API_ROOT + path, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RenderError(
            f"GitHub API returned HTTP {exc.code} for {path}: {body[:300]}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RenderError(f"Could not reach GitHub API for {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RenderError(f"GitHub returned invalid JSON for {path}.") from exc


def fetch_stats(username: str) -> dict[str, int]:
    token = os.getenv("GITHUB_TOKEN", "").strip()
    user = fetch_json(f"/users/{username}", token)
    if not isinstance(user, dict):
        raise RenderError("GitHub user response was not an object.")

    repos: list[dict[str, Any]] = []
    page = 1
    while True:
        batch = fetch_json(
            f"/users/{username}/repos?type=owner&sort=full_name"
            f"&direction=asc&per_page=100&page={page}",
            token,
        )
        if not isinstance(batch, list):
            raise RenderError("GitHub repository response was not a list.")
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    return {
        "repos": len(repos),
        "followers": int(user.get("followers", 0)),
        "stars": sum(int(repo.get("stargazers_count", 0)) for repo in repos),
    }


def portrait_tspans() -> str:
    lines = PORTRAIT_ASCII_PATH.read_text(encoding="utf-8").splitlines()
    start_y = 33.0
    line_height = 13.1
    return "\n".join(
        f'    <tspan x="22" y="{start_y + index * line_height:.1f}">'
        f"{xml(line)}</tspan>"
        for index, line in enumerate(lines)
    )


def build_right_text(config: dict[str, Any], stats: dict[str, int]) -> str:
    profile = config["profile"]
    contact = config["contact"]
    lines: list[str] = []

    shell = xml(profile["shell"])
    cwd = xml(profile["cwd"])
    lines.append(
        f'    <tspan x="420" y="31">{shell}</tspan>'
        f'<tspan class="muted">  {cwd}</tspan>'
    )

    y = 66
    for index, row in enumerate(profile.get("identity_rows", []), start=1):
        key, value = validate_row(row, f"identity_rows[{index}]")
        lines.append(row_markup(y, key, value))
        y += 24

    y += 15
    for section_index, section in enumerate(config["sections"], start=1):
        title = str(section.get("title", "")).strip()
        if not title:
            raise RenderError(f"sections[{section_index}] is missing a title.")

        lines.append(section_heading(y, title))
        y += 26

        rows = section.get("rows", [])
        if not rows:
            raise RenderError(f"Section {title!r} must contain at least one row.")

        for row_index, row in enumerate(rows, start=1):
            key, value = validate_row(
                row, f"section {title!r} row {row_index}"
            )
            lines.append(row_markup(y, key, value))
            y += 24

        y += 13

    lines.append(section_heading(y, "Contact & GitHub"))
    y += 26
    lines.append(row_markup(y, "Web", str(contact["website_label"])))
    y += 24
    lines.append(row_markup(y, "LinkedIn", str(contact["linkedin_label"])))
    y += 34

    stats_text = (
        f'    <tspan x="420" y="{y}" class="key">Public repos</tspan>'
        f'<tspan class="muted"> ..... </tspan>'
        f'<tspan id="stat_repos" class="green">{stats["repos"]}</tspan>'
        f'<tspan class="muted">   ·   </tspan>'
        f'<tspan class="key">Followers</tspan>'
        f'<tspan class="muted"> ... </tspan>'
        f'<tspan id="stat_followers" class="green">{stats["followers"]}</tspan>'
        f'<tspan class="muted">   ·   </tspan>'
        f'<tspan class="key">Stars</tspan>'
        f'<tspan class="muted"> ... </tspan>'
        f'<tspan id="stat_stars" class="green">{stats["stars"]}</tspan>'
    )
    lines.append(stats_text)
    y += 26

    if y > 540:
        raise RenderError(
            "Configured rows exceed the fixed 560px layout. "
            "Shorten the profile or remove a row."
        )

    lines.append(
        f'    <tspan x="420" y="{y}" class="muted">'
        f'{xml(profile["footer"])}</tspan>'
    )
    return "\n".join(lines)


def render_theme(
    theme_name: str,
    config: dict[str, Any],
    stats: dict[str, int],
) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    profile = config["profile"]

    replacements = {
        **THEMES[theme_name],
        "TITLE": xml(
            f'{profile["name"]} — terminal-style GitHub profile'
        ),
        "DESC": xml(
            f'ASCII portrait and professional profile information for '
            f'{profile["name"]}.'
        ),
        "PORTRAIT_TSPANS": portrait_tspans(),
        "PORTRAIT_PATHS": PORTRAIT_PATHS_PATH.read_text(encoding="utf-8").rstrip(),
        "RIGHT_TEXT": build_right_text(config, stats),
    }

    rendered = template
    for key, value in replacements.items():
        rendered = rendered.replace("{{" + key + "}}", str(value))

    unresolved = [token for token in rendered.split() if "{{" in token]
    if unresolved:
        raise RenderError(f"Unresolved template placeholders: {unresolved}")

    ET.fromstring(rendered)
    return rendered


def write_if_changed(path: Path, content: str) -> bool:
    previous = path.read_text(encoding="utf-8") if path.exists() else None
    if previous == content:
        return False

    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8", newline="\n")
    temporary.replace(path)
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fetch-stats",
        action="store_true",
        help="Fetch current public repository, follower and star counts.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if generated SVG files are not up to date.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config()
    stats = (
        fetch_stats(str(config["profile"]["username"]))
        if args.fetch_stats
        else {
            "repos": int(config["stats"]["repos"]),
            "followers": int(config["stats"]["followers"]),
            "stars": int(config["stats"]["stars"]),
        }
    )

    stale: list[str] = []
    changed: list[str] = []

    for theme_name, output_path in OUTPUTS.items():
        rendered = render_theme(theme_name, config, stats)
        current = (
            output_path.read_text(encoding="utf-8")
            if output_path.exists()
            else None
        )

        if args.check:
            if current != rendered:
                stale.append(output_path.name)
        elif write_if_changed(output_path, rendered):
            changed.append(output_path.name)

    if args.check and stale:
        print("Generated SVG files are stale: " + ", ".join(stale), file=sys.stderr)
        return 1

    print(
        f'Rendered profile for {config["profile"]["username"]}: '
        f'{stats["repos"]} public repos, {stats["followers"]} followers, '
        f'{stats["stars"]} stars.'
    )
    if not args.check:
        print("Updated: " + (", ".join(changed) if changed else "nothing"))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RenderError, OSError, KeyError, TypeError, ValueError, ET.ParseError) as exc:
        print(f"Profile render failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
