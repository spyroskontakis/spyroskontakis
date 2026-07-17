from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
PORTRAIT_SOURCE = ASSETS / "portrait_ascii.txt"

CARD_WIDTH = 1500
CARD_HEIGHT = 740
CARD_PADDING = 34
INNER_MARGIN = 14

PORTRAIT_FONT_SIZE = 10
PORTRAIT_SCALE_X = 0.315
PORTRAIT_SCALE_Y = 0.525
PORTRAIT_CHAR_ADVANCE = PORTRAIT_FONT_SIZE * 0.6
PORTRAIT_VISIBLE_COLUMNS = 274
PORTRAIT_WIDTH = round(
    PORTRAIT_VISIBLE_COLUMNS * PORTRAIT_CHAR_ADVANCE * PORTRAIT_SCALE_X
)
PORTRAIT_HEIGHT = round((8 + 161 * 7.5) * PORTRAIT_SCALE_Y)
PORTRAIT_X = CARD_PADDING
PORTRAIT_Y = round((CARD_HEIGHT - PORTRAIT_HEIGHT) / 2)
CONTENT_GAP = 36
TEXT_X = PORTRAIT_X + PORTRAIT_WIDTH + CONTENT_GAP

FONT_STACK = (
    'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, '
    '"Liberation Mono", monospace'
)
LABEL_FONT_SIZE = 20.5
BODY_FONT_SIZE = 22
HEADING_FONT_SIZE = 23.5
BODY_LINE_HEIGHT = 1.545
LABEL_SEPARATOR_X = 142
VALUE_X = 170
PANEL_TOP = 60

PORTRAIT_DENSITY_RAMP = "@%#*+=-:. "
DARK_PORTRAIT_PALETTE = (
    "#59636e",
    "#6e7883",
    "#87919c",
    "#a0aab4",
    "#b6bec7",
    "#c7ced6",
)
DARK_PORTRAIT_GAMMA = 0.70
DARK_PORTRAIT_BRIGHTNESS = 1.30
DARK_PORTRAIT_MIN_OPACITY = 0.86
DARK_PORTRAIT_MAX_OPACITY = 0.99
DARK_BACKGROUND_UNIFORMITY_THRESHOLD = 0.80
DARK_BACKGROUND_WINDOW_RADIUS = 2


@dataclass(frozen=True)
class Theme:
    name: str
    background: str
    surface: str
    border: str
    main_text: str
    secondary_text: str
    blue: str
    green: str
    orange: str
    portrait_ink: str
    portrait_palette: tuple[str, ...] | None = None
    portrait_gamma: float = 1.0
    portrait_brightness: float = 1.0
    portrait_min_opacity: float = 1.0
    portrait_max_opacity: float = 1.0
    background_uniformity_threshold: float = 1.0


THEMES = (
    Theme(
        name="light",
        background="#ffffff",
        surface="#ffffff",
        border="#d0d7de",
        main_text="#1f2328",
        secondary_text="#57606a",
        blue="#0969da",
        green="#1a7f37",
        orange="#9a6700",
        portrait_ink="#1f2937",
    ),
    Theme(
        name="dark",
        background="#0d1117",
        surface="#161b22",
        border="#30363d",
        main_text="#f0f6fc",
        secondary_text="#8b949e",
        blue="#58a6ff",
        green="#3fb950",
        orange="#d29922",
        portrait_ink="#8b949e",
        portrait_palette=DARK_PORTRAIT_PALETTE,
        portrait_gamma=DARK_PORTRAIT_GAMMA,
        portrait_brightness=DARK_PORTRAIT_BRIGHTNESS,
        portrait_min_opacity=DARK_PORTRAIT_MIN_OPACITY,
        portrait_max_opacity=DARK_PORTRAIT_MAX_OPACITY,
        background_uniformity_threshold=DARK_BACKGROUND_UNIFORMITY_THRESHOLD,
    ),
)


PANEL_ITEMS = (
    ("prompt", "$ whoami", "", 46),
    ("entry", "role", "Software Engineer", 34),
    ("entry", "interests", "Machine Learning, Data Analysis,", 34),
    ("continuation", "", "Software Technology, Operating Systems, Security", 52),
    ("section", "technical", "", 46),
    ("entry", "code", "Python, SQL, C, C++, Java", 34),
    ("entry", "tools", "Pandas, Jupyter, Anaconda, NetworkX", 52),
    ("academic", "academic", "", 46),
    ("entry", "degree", "Computer Science Engineering & Informatics", 34),
    ("entry", "university", "University of Ioannina", 34),
    ("entry", "thesis", "Hallucination Detection in Large Language Models", 34),
    ("entry", "benchmarks", "SHROOM, SemEval", 52),
    ("section", "languages", "", 46),
    ("entry", "spoken", "Greek (Native), English (B2), French (A2)", 52),
    ("section", "web", "", 46),
    ("entry", "portfolio", "spyroskontakis.github.io", 0),
)


def load_portrait() -> list[str]:
    text = PORTRAIT_SOURCE.read_text(encoding="utf-8")
    rows = text.splitlines()
    if len(rows) != 162 or any(len(row) != 300 for row in rows):
        raise ValueError("portrait_ascii.txt must remain a 162 × 300 character grid")
    return rows


def background_mask(rows: list[str], threshold: float) -> set[tuple[int, int]]:
    height = len(rows)
    width = len(rows[0])
    radius = DARK_BACKGROUND_WINDOW_RADIUS
    candidates: set[tuple[int, int]] = set()

    for y, row in enumerate(rows):
        for x, character in enumerate(row):
            if character != "@":
                continue
            x0, x1 = max(0, x - radius), min(width, x + radius + 1)
            y0, y1 = max(0, y - radius), min(height, y + radius + 1)
            area = (x1 - x0) * (y1 - y0)
            dense = sum(rows[ny][nx] == "@" for ny in range(y0, y1) for nx in range(x0, x1))
            if dense / area >= threshold:
                candidates.add((x, y))

    queue = deque(
        cell
        for cell in candidates
        if cell[0] in {0, width - 1} or cell[1] in {0, height - 1}
    )
    background = set(queue)
    while queue:
        x, y = queue.popleft()
        for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if neighbor in candidates and neighbor not in background:
                background.add(neighbor)
                queue.append(neighbor)
    return background


def interpolate_palette(palette: tuple[str, ...], tone: float) -> str:
    position = max(0.0, min(1.0, tone)) * (len(palette) - 1)
    lower = int(position)
    upper = min(lower + 1, len(palette) - 1)
    fraction = position - lower
    low_rgb = tuple(int(palette[lower][index : index + 2], 16) for index in (1, 3, 5))
    high_rgb = tuple(int(palette[upper][index : index + 2], 16) for index in (1, 3, 5))
    mixed = tuple(round(low + (high - low) * fraction) for low, high in zip(low_rgb, high_rgb))
    return "#" + "".join(f"{channel:02x}" for channel in mixed)


def dark_tone_runs(
    row: str,
    y: int,
    theme: Theme,
    background: set[tuple[int, int]],
) -> str:
    assert theme.portrait_palette is not None
    styles: list[str] = []
    visible_ramp = PORTRAIT_DENSITY_RAMP[:-1]
    for x, character in enumerate(row):
        if character == " " or (x, y) in background:
            styles.append("fill:transparent")
            continue
        source_tone = visible_ramp.index(character) / (len(visible_ramp) - 1)
        corrected = min(
            1.0,
            (source_tone**theme.portrait_gamma) * theme.portrait_brightness,
        )
        color = interpolate_palette(theme.portrait_palette, corrected)
        opacity = theme.portrait_min_opacity + (
            theme.portrait_max_opacity - theme.portrait_min_opacity
        ) * corrected
        styles.append(f"fill:{color};fill-opacity:{opacity:.2f}")

    runs: list[str] = []
    start = 0
    current = styles[0]
    for index, style in enumerate(styles[1:], start=1):
        if style != current:
            runs.append(
                f'<tspan style="{current}">{escape(row[start:index])}</tspan>'
            )
            start = index
            current = style
    runs.append(f'<tspan style="{current}">{escape(row[start:])}</tspan>')
    return "".join(runs)


def portrait_markup(rows: list[str], theme: Theme) -> str:
    rendered_rows = []
    background = (
        background_mask(rows, theme.background_uniformity_threshold)
        if theme.portrait_palette
        else set()
    )
    for index, row in enumerate(rows):
        y = 8 + index * 7.5
        content = (
            dark_tone_runs(row, index, theme, background)
            if theme.portrait_palette
            else escape(row)
        )
        rendered_rows.append(f'      <tspan x="0" y="{y:.1f}">{content}</tspan>')
    return "\n".join(rendered_rows)


def panel_markup() -> str:
    lines: list[str] = []
    y = PANEL_TOP
    for kind, label, value, advance in PANEL_ITEMS:
        if kind == "prompt":
            lines.append(f'      <text class="heading prompt" x="0" y="{y}">{label}</text>')
        elif kind in {"section", "academic"}:
            class_name = "heading section" if kind == "section" else "heading academic"
            lines.append(
                f'      <text class="{class_name}" x="0" y="{y}">&gt; {label}</text>'
            )
        elif kind == "continuation":
            lines.append(f'      <text class="value" x="{VALUE_X}" y="{y}">{escape(value)}</text>')
        else:
            lines.extend(
                (
                    f'      <text class="label" x="0" y="{y}">{label}</text>',
                    f'      <text class="punctuation" x="{LABEL_SEPARATOR_X}" y="{y}">:</text>',
                    f'      <text class="value" x="{VALUE_X}" y="{y}">{escape(value)}</text>',
                )
            )
        y += advance
    return "\n".join(lines)


def render_svg(rows: list[str], theme: Theme) -> str:
    portrait_filter_definition = (
        '  <defs>\n'
        '    <filter id="portrait-monochrome" color-interpolation-filters="sRGB">\n'
        '      <feColorMatrix type="saturate" values="0"/>\n'
        '    </filter>\n'
        '  </defs>\n'
        if theme.portrait_palette
        else ""
    )
    portrait_filter_attribute = (
        ' filter="url(#portrait-monochrome)"' if theme.portrait_palette else ""
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_WIDTH}" height="{CARD_HEIGHT}" viewBox="0 0 {CARD_WIDTH} {CARD_HEIGHT}" role="img" aria-labelledby="title desc">
  <title id="title">Spyros Kontakis — terminal profile</title>
  <desc id="desc">ASCII portrait with a concise software engineering profile panel.</desc>
  <style>
    .portrait {{ font-family: {FONT_STACK}; font-size: {PORTRAIT_FONT_SIZE}px; fill: {theme.portrait_ink}; white-space: pre; }}
    .panel text {{ font-family: {FONT_STACK}; font-size: {BODY_FONT_SIZE}px; line-height: {BODY_LINE_HEIGHT}; }}
    .heading {{ font-size: {HEADING_FONT_SIZE}px; font-weight: 700; }}
    .prompt {{ fill: {theme.green}; }}
    .section {{ fill: {theme.blue}; }}
    .academic {{ fill: {theme.orange}; }}
    .label, .punctuation {{ fill: {theme.secondary_text}; font-size: {LABEL_FONT_SIZE}px; }}
    .value {{ fill: {theme.main_text}; font-weight: 600; }}
  </style>
{portrait_filter_definition}  <rect width="{CARD_WIDTH}" height="{CARD_HEIGHT}" rx="18" fill="{theme.background}"/>
  <rect x="{INNER_MARGIN}" y="{INNER_MARGIN}" width="{CARD_WIDTH - 2 * INNER_MARGIN}" height="{CARD_HEIGHT - 2 * INNER_MARGIN}" rx="14" fill="{theme.surface}"/>
  <rect x="1" y="1" width="{CARD_WIDTH - 2}" height="{CARD_HEIGHT - 2}" rx="17" fill="none" stroke="{theme.border}" stroke-width="2"/>
  <g aria-label="ASCII portrait"{portrait_filter_attribute} transform="translate({PORTRAIT_X} {PORTRAIT_Y}) scale({PORTRAIT_SCALE_X} {PORTRAIT_SCALE_Y})">
    <text class="portrait" xml:space="preserve">
{portrait_markup(rows, theme)}
    </text>
  </g>
  <g class="panel" transform="translate({TEXT_X} 0)">
{panel_markup()}
  </g>
</svg>
'''


def render_all(check: bool = False) -> None:
    rows = load_portrait()
    stale: list[Path] = []
    for theme in THEMES:
        output = ASSETS / f"profile-{theme.name}.svg"
        rendered = render_svg(rows, theme)
        if check:
            if not output.exists() or output.read_text(encoding="utf-8") != rendered:
                stale.append(output)
        else:
            output.write_text(rendered, encoding="utf-8", newline="\n")
    if stale:
        names = ", ".join(path.name for path in stale)
        raise SystemExit(f"Generated profile assets are stale: {names}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Render the theme-aware profile SVG assets.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when committed SVG assets differ from generated output",
    )
    args = parser.parse_args()
    render_all(check=args.check)


if __name__ == "__main__":
    main()
