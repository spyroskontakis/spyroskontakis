from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass
from html import escape
from math import hypot
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
PORTRAIT_SOURCE = ASSETS / "portrait_ascii.txt"

CARD_WIDTH = 1500
CARD_HEIGHT = 700
DIVIDER_X = 640
TEXT_X = 682

FONT_STACK = (
    'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, '
    '"Liberation Mono", monospace'
)
PORTRAIT_FONT_SIZE = 10
BODY_FONT_SIZE = 16.5
HEADING_FONT_SIZE = 17.5
BODY_LINE_HEIGHT = 1.64

PORTRAIT_DENSITY_RAMP = "@%#*+=-:. "
DARK_PORTRAIT_PALETTE = (
    "#484f58",
    "#6e7681",
    "#8c959f",
    "#a6b0bb",
    "#c1c9d2",
    "#d8dee4",
)
DARK_PORTRAIT_GAMMA = 0.71
DARK_PORTRAIT_BRIGHTNESS = 1.22
DARK_PORTRAIT_BACKGROUND_OPACITY = 0.54
DARK_PORTRAIT_SUBJECT_OPACITY_FLOOR = 0.88
DARK_PORTRAIT_FEATURE_OPACITY = 0.99
DARK_PORTRAIT_FEATURE_MIDTONE_LIFT = 0.16
DARK_PORTRAIT_FEATURE_CONTRAST = 0.24
DARK_PORTRAIT_HAIR_DARK_OPACITY_CAP = 0.68
DARK_BACKGROUND_UNIFORMITY_THRESHOLD = 0.80
DARK_BACKGROUND_WINDOW_RADIUS = 2
DARK_NOISE_SUPPORT_THRESHOLD = 5
DARK_SUBJECT_REGION = (165, 82, 125, 105)
DARK_HAIR_REGION = (128, 28, 78, 31)
DARK_FEATURE_REGIONS = (
    (153, 64, 52, 12),  # eyebrow and eye band
    (193, 83, 30, 23),  # nose bridge and nostrils
    (190, 101, 38, 11),  # lips and mouth
    (155, 119, 70, 27),  # beard boundary and jaw
    (80, 92, 28, 25),  # ear
)


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
    portrait_background_opacity: float = 1.0
    portrait_subject_opacity_floor: float = 1.0
    portrait_feature_opacity: float = 1.0
    portrait_feature_midtone_lift: float = 0.0
    portrait_feature_contrast: float = 0.0
    portrait_noise_reduction: bool = False
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
        portrait_background_opacity=DARK_PORTRAIT_BACKGROUND_OPACITY,
        portrait_subject_opacity_floor=DARK_PORTRAIT_SUBJECT_OPACITY_FLOOR,
        portrait_feature_opacity=DARK_PORTRAIT_FEATURE_OPACITY,
        portrait_feature_midtone_lift=DARK_PORTRAIT_FEATURE_MIDTONE_LIFT,
        portrait_feature_contrast=DARK_PORTRAIT_FEATURE_CONTRAST,
        portrait_noise_reduction=True,
        background_uniformity_threshold=DARK_BACKGROUND_UNIFORMITY_THRESHOLD,
    ),
)


PANEL_LINES = (
    ("prompt", 78, "$ whoami", ""),
    ("entry", 120, "role", "Software Engineer"),
    ("entry", 148, "interests", "Machine Learning, Data Analysis,"),
    ("continuation", 175, "", "Software Technology, Operating Systems, Security"),
    ("section", 228, "technical", ""),
    ("entry", 270, "code", "Python, SQL, C, C++, Java"),
    ("entry", 297, "tools", "Pandas, Jupyter, Anaconda, NetworkX"),
    ("academic", 350, "academic", ""),
    ("entry", 392, "degree", "Computer Science Engineering & Informatics"),
    ("entry", 419, "university", "University of Ioannina"),
    ("entry", 446, "thesis", "Hallucination Detection in Large Language Models"),
    ("entry", 473, "benchmarks", "SHROOM, SemEval"),
    ("section", 526, "languages", ""),
    ("entry", 568, "spoken", "Greek (Native), English (B2), French (A2)"),
    ("section", 621, "web", ""),
    ("entry", 663, "portfolio", "spyroskontakis.github.io"),
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


def region_distance(x: int, y: int, region: tuple[int, int, int, int]) -> float:
    center_x, center_y, radius_x, radius_y = region
    return hypot((x - center_x) / radius_x, (y - center_y) / radius_y)


def feature_weight(x: int, y: int) -> float:
    return max(
        (max(0.0, 1.0 - region_distance(x, y, region)) for region in DARK_FEATURE_REGIONS),
        default=0.0,
    )


def subject_opacity(x: int, y: int, feature: float, theme: Theme) -> float:
    subject_distance = region_distance(x, y, DARK_SUBJECT_REGION)
    if subject_distance <= 1.0:
        center_weight = 1.0 - subject_distance
        opacity = theme.portrait_subject_opacity_floor + 0.06 * center_weight
    else:
        opacity = theme.portrait_background_opacity
    if feature > 0:
        feature_opacity = theme.portrait_subject_opacity_floor + (
            theme.portrait_feature_opacity - theme.portrait_subject_opacity_floor
        ) * (0.55 + 0.45 * feature)
        opacity = max(opacity, feature_opacity)
    return min(theme.portrait_feature_opacity, opacity)


def interpolate_palette(palette: tuple[str, ...], tone: float) -> str:
    position = max(0.0, min(1.0, tone)) * (len(palette) - 1)
    lower = int(position)
    upper = min(lower + 1, len(palette) - 1)
    fraction = position - lower
    low_rgb = tuple(int(palette[lower][index : index + 2], 16) for index in (1, 3, 5))
    high_rgb = tuple(int(palette[upper][index : index + 2], 16) for index in (1, 3, 5))
    mixed = tuple(round(low + (high - low) * fraction) for low, high in zip(low_rgb, high_rgb))
    return "#" + "".join(f"{channel:02x}" for channel in mixed)


def local_dark_support(rows: list[str], x: int, y: int) -> int:
    height = len(rows)
    width = len(rows[0])
    return sum(
        rows[ny][nx] in "@%#*"
        for ny in range(max(0, y - 1), min(height, y + 2))
        for nx in range(max(0, x - 1), min(width, x + 2))
        if (nx, ny) != (x, y)
    )


def suppress_dark_noise(rows: list[str], x: int, y: int, source_tone: float) -> bool:
    if source_tone > 0.375 or feature_weight(x, y) > 0:
        return False
    support = local_dark_support(rows, x, y)
    outside_subject = region_distance(x, y, DARK_SUBJECT_REGION) > 1.0
    in_hair = region_distance(x, y, DARK_HAIR_REGION) <= 1.0
    if outside_subject:
        return support < DARK_NOISE_SUPPORT_THRESHOLD
    if in_hair and source_tone <= 0.25:
        return support < DARK_NOISE_SUPPORT_THRESHOLD + 2
    return False


def dark_tone_runs(
    rows: list[str],
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
        if theme.portrait_noise_reduction and suppress_dark_noise(rows, x, y, source_tone):
            styles.append("fill:transparent")
            continue
        corrected = min(
            1.0,
            (source_tone**theme.portrait_gamma) * theme.portrait_brightness,
        )
        feature = feature_weight(x, y)
        midtone_kernel = 4.0 * corrected * (1.0 - corrected)
        corrected += feature * theme.portrait_feature_midtone_lift * midtone_kernel
        corrected = 0.5 + (corrected - 0.5) * (
            1.0 + feature * theme.portrait_feature_contrast
        )
        corrected = max(0.0, min(1.0, corrected))
        color = interpolate_palette(theme.portrait_palette, corrected)
        opacity = subject_opacity(x, y, feature, theme)
        if (
            region_distance(x, y, DARK_HAIR_REGION) <= 1.0
            and source_tone <= 0.25
            and feature == 0
        ):
            opacity = min(opacity, DARK_PORTRAIT_HAIR_DARK_OPACITY_CAP)
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
            dark_tone_runs(rows, row, index, theme, background)
            if theme.portrait_palette
            else escape(row)
        )
        rendered_rows.append(f'      <tspan x="0" y="{y:.1f}">{content}</tspan>')
    return "\n".join(rendered_rows)


def panel_markup() -> str:
    lines: list[str] = []
    for kind, y, label, value in PANEL_LINES:
        if kind == "prompt":
            lines.append(f'      <text class="heading prompt" x="0" y="{y}">{label}</text>')
        elif kind in {"section", "academic"}:
            class_name = "heading section" if kind == "section" else "heading academic"
            lines.append(
                f'      <text class="{class_name}" x="0" y="{y}">&gt; {label}</text>'
            )
        elif kind == "continuation":
            lines.append(f'      <text class="value" x="148" y="{y}">{escape(value)}</text>')
        else:
            lines.extend(
                (
                    f'      <text class="label" x="0" y="{y}">{label}</text>',
                    f'      <text class="punctuation" x="120" y="{y}">:</text>',
                    f'      <text class="value" x="148" y="{y}">{escape(value)}</text>',
                )
            )
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
    .label, .punctuation {{ fill: {theme.secondary_text}; }}
    .value {{ fill: {theme.main_text}; }}
  </style>
{portrait_filter_definition}  <rect width="{CARD_WIDTH}" height="{CARD_HEIGHT}" rx="18" fill="{theme.background}"/>
  <rect x="14" y="14" width="1472" height="672" rx="14" fill="{theme.surface}"/>
  <rect x="1" y="1" width="1498" height="698" rx="17" fill="none" stroke="{theme.border}" stroke-width="2"/>
  <line x1="{DIVIDER_X}" y1="36" x2="{DIVIDER_X}" y2="664" stroke="{theme.border}" stroke-width="2"/>
  <g aria-label="ASCII portrait"{portrait_filter_attribute} transform="translate(34 28) scale(0.315 0.525)">
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
