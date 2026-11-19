#!/usr/bin/env python3
"""Render the README landing assets: wordmark, animated demo, badges.

Not benchmark data. The demo is a schematic of one command fanning out
across 8 repos, contrasted with a serial loop. Measured numbers stay in
the charts from bench/agent-eval/render_readme_charts.py.

  python3 bench/render_readme_landing.py

Writes light and dark SVGs to .github/assets/readme/.
Animation is SMIL. The attributes you see with animation disabled are the
end frame: the loop is still on its third repo, and indo has already
printed only the failures.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".github" / "assets" / "readme"

SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"

CYCLE = 8.0  # seconds

THEMES = {
    "light": {
        "ink": "#1f2328",
        "muted": "#656d76",
        "faint": "#8c959f",
        "green": "#1a7f37",
        "green_bar": "#1f883d",
        "green_soft": "#dafbe1",
        "red": "#cf222e",
        "bg": "#ffffff",
        "bar_bg": "#f6f8fa",
        "border": "#d0d7de",
        "track": "#eaeef2",
        "line": "#d8dee4",
        "highlight": "#eef7f1",
        "title_bg": "#f6f8fa",
        "pill": "#f6f8fa",
        "pill_border": "#d0d7de",
        "fail_bg": "#fff1f0",
    },
    "dark": {
        "ink": "#e6edf3",
        "muted": "#8b949e",
        "faint": "#6e7681",
        "green": "#3fb950",
        "green_bar": "#3fb950",
        "green_soft": "#12261e",
        "red": "#ff7b72",
        "bg": "#0d1117",
        "bar_bg": "#161b22",
        "border": "#30363d",
        "track": "#21262d",
        "line": "#30363d",
        "highlight": "#122117",
        "title_bg": "#161b22",
        "pill": "#161b22",
        "pill_border": "#30363d",
        "fail_bg": "#2d1214",
    },
}

# Same 8 folders on both sides. Two fail. Finish times are fractions of CYCLE.
REPOS = [
    ("api", 0.02, 0.15, False),
    ("web", 0.03, 0.19, False),
    ("worker", 0.04, 0.17, False),
    ("billing", 0.05, 0.23, False),
    ("checkout", 0.06, 0.28, True),
    ("mail", 0.07, 0.33, True),
    ("search", 0.04, 0.21, False),
    ("docs", 0.05, 0.18, False),
]
# Left-hand loop advances one repo per this fraction of the cycle.
# Indo's summary is on screen by ~0.46, while this loop is on repo 3.
STEP = 0.22


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, *, fill, size, weight="400", anchor="start", family=None, opacity=None, extra="") -> str:
    op = f' opacity="{opacity}"' if opacity is not None else ""
    fam = family or SANS
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-family="{fam}" '
        f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}"{op}{extra}>{esc(s)}</text>'
    )


def rect(x, y, w, h, *, fill, rx=0, opacity=None, extra="", children="") -> str:
    op = f' opacity="{opacity}"' if opacity is not None else ""
    attrs = (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" '
        f'fill="{fill}"{op}{extra}'
    )
    if children:
        return attrs + ">" + children + "</rect>"
    return attrs + "/>"


def anim_opacity(values: str, keys: str, calc: str = "linear") -> str:
    return (
        f'<animate attributeName="opacity" values="{values}" keyTimes="{keys}" '
        f'dur="{CYCLE}s" repeatCount="indefinite" calcMode="{calc}"/>'
    )


def wordmark(c: dict) -> str:
    # Left-aligned mark + word. Transparent outside the artwork so it sits
    # on the README background.
    w, h = 460, 108
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">',
        "<title>indo</title>",
        "<desc>indo wordmark. A stack of parallel bars beside the name.</desc>",
    ]
    # Icon: eight lanes, staggered, like jobs in flight.
    ix, iy, isz = 4, 22, 64
    parts.append(rect(ix, iy, isz, isz, fill=c["green_soft"], rx=14))
    # Vertical bars, bottom-aligned, so the mark reads as parallel work
    # rather than a menu of horizontal lines.
    heights = [0.38, 0.62, 0.48, 0.86, 0.55, 0.74, 0.42, 0.68]
    inner = 8
    gap = 1.5
    n = len(heights)
    bw = (isz - inner * 2 - gap * (n - 1)) / n
    floor = iy + isz - inner
    for i, frac in enumerate(heights):
        bh = (isz - inner * 2) * frac
        x = ix + inner + i * (bw + gap)
        parts.append(rect(x, floor - bh, bw, bh, fill=c["green"], rx=1.5))
    parts.append(text(ix + isz + 18, 76, "indo", fill=c["ink"], size=56, weight="650"))
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def badge(label: str, c: dict) -> str:
    try:
        from PIL import ImageFont

        font = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf", 13)
        tw = font.getlength(label)
    except Exception:
        tw = len(label) * 7.2
    w = int(tw + 36)
    h = 30
    return "\n".join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">',
        f"<title>{esc(label)}</title>",
        rect(0.5, 0.5, w - 1, h - 1, fill=c["pill"], rx=15, extra=f' stroke="{c["pill_border"]}" stroke-width="1"'),
        text(w / 2, 20, label, fill=c["ink"], size=13, weight="600", anchor="middle"),
        "</svg>",
    ]) + "\n"


def _keys(*stops: float) -> str:
    return ";".join(f"{s:.3f}" for s in stops)


def demo(c: dict) -> str:
    W, H = 960, 420
    row_h = 28
    row0 = 158
    bar_x = 612
    bar_w = 250
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img">',
        "<title>indo runs eight repos at once</title>",
        "<desc>A for loop tests one repo at a time. indo -f -P 8 runs npm test in eight repos at once, then prints only the two failures.</desc>",
        f"<!-- generated by bench/render_readme_landing.py; cycle {CYCLE}s -->",
        rect(0.5, 0.5, W - 1, H - 1, fill=c["bg"], rx=14, extra=f' stroke="{c["border"]}" stroke-width="1"'),
        rect(1, 1, W - 2, 40, fill=c["title_bg"], extra=f' clip-path="inset(0 0 0 0 round 13px 13px 0 0)"'),
    ]
    # Title-bar dots and caption.
    for i, color in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        cx = 22 + i * 16
        parts.append(f'<circle cx="{cx}" cy="20" r="5" fill="{color}"/>')
    parts.append(text(W / 2, 25, "~/repos", fill=c["muted"], size=13, weight="600", anchor="middle"))
    parts.append(f'<line x1="480" y1="40" x2="480" y2="{H - 1}" stroke="{c["line"]}" stroke-width="1"/>')

    # Column labels and the commands. These stay put for the whole loop.
    parts.append(text(28, 66, "plain bash", fill=c["muted"], size=13, weight="600"))
    parts.append(text(500, 66, "indo", fill=c["green"], size=13, weight="650"))
    parts.append(text(28, 94, "$", fill=c["green"], size=14, weight="650", family=MONO))
    parts.append(text(44, 94, "for d in */; do", fill=c["ink"], size=14, family=MONO))
    parts.append(text(44, 116, '(cd "$d" && npm test); done', fill=c["ink"], size=14, family=MONO))
    parts.append(text(500, 94, "$", fill=c["green"], size=14, weight="650", family=MONO))
    parts.append(text(516, 94, "indo -f -P 8 */ 'npm test'", fill=c["ink"], size=14, family=MONO))
    parts.append(text(28, 142, "one repo, then the next", fill=c["faint"], size=12))
    parts.append(text(500, 142, "eight at once, then only the failures", fill=c["faint"], size=12))

    # Moving highlight on the serial side. Base y is the third row (the still frame).
    hy = row0 + 2 * row_h + 2
    parts.append(
        rect(16, hy, 448, row_h - 4, fill=c["highlight"], rx=6, children=(
            "<animate attributeName=\"y\" calcMode=\"discrete\" "
            f'values="{";".join(str(int(row0 + i * row_h + 2)) for i in range(4))}" '
            f'keyTimes="{_keys(0, STEP, STEP * 2, STEP * 3)}" '
            f'dur="{CYCLE}s" repeatCount="indefinite"/>'
        ))
    )

    # Serial rows. First four change state. The rest stay waiting, which is the point.
    for i, (name, _s, _f, _fail) in enumerate(REPOS):
        y = row0 + i * row_h + 18
        parts.append(text(32, y, name, fill=c["ink"], size=14, family=MONO))
        if i >= 4:
            parts.append(text(448, y, "wait", fill=c["faint"], size=13, anchor="end", family=MONO))
            continue
        # wait / run / ok. Discrete so two labels never show at once.
        # Base matches the still frame: loop on the third repo.
        base_wait = 1 if i > 2 else 0
        base_run = 1 if i == 2 else 0
        base_ok = 1 if i < 2 else 0
        a = i * STEP
        b = (i + 1) * STEP
        if a <= 0:
            wait_v, wait_k = "0;0", "0;1"
            run_v, run_k = "1;0;0", _keys(0, b, 1)
        else:
            wait_v, wait_k = "1;0;0", _keys(0, a, 1)
            run_v, run_k = "0;1;0;0", _keys(0, a, b, 1)
        ok_v, ok_k = "0;1;1", _keys(0, b, 1)
        parts.append(
            f'<text x="448" y="{y:.1f}" fill="{c["faint"]}" font-family="{MONO}" font-size="13" text-anchor="end" opacity="{base_wait}">wait'
            f'{anim_opacity(wait_v, wait_k, "discrete")}</text>'
        )
        parts.append(
            f'<text x="448" y="{y:.1f}" fill="{c["green"]}" font-family="{MONO}" font-size="13" font-weight="650" text-anchor="end" opacity="{base_run}">run'
            f'{anim_opacity(run_v, run_k, "discrete")}</text>'
        )
        parts.append(
            f'<text x="448" y="{y:.1f}" fill="{c["muted"]}" font-family="{MONO}" font-size="13" text-anchor="end" opacity="{base_ok}">ok'
            f'{anim_opacity(ok_v, ok_k, "discrete")}</text>'
        )

    # Parallel progress. Hidden in the still frame. Fades out once the summary is up.
    parts.append(
        '<g opacity="0">'
        + anim_opacity("1;1;0;0;1", _keys(0, 0.34, 0.42, 0.94, 1))
    )
    for i, (name, start, finish, fail) in enumerate(REPOS):
        y = row0 + i * row_h
        baseline = y + 18
        parts.append(text(500, baseline, name, fill=c["ink"], size=14, family=MONO))
        parts.append(rect(bar_x, y + 8, bar_w, 10, fill=c["track"], rx=5))
        color = c["red"] if fail else c["green_bar"]
        # Grow, hold, snap back with the loop.
        width_anim = (
            "<animate attributeName=\"width\" "
            f'values="0;0;{bar_w:.0f};{bar_w:.0f};0;0" '
            f'keyTimes="{_keys(0, start, finish, 0.40, 0.42, 1)}" '
            f'dur="{CYCLE}s" repeatCount="indefinite"/>'
        )
        fill_anim = ""
        if fail:
            fill_anim = (
                "<animate attributeName=\"fill\" calcMode=\"discrete\" "
                f'values="{c["green_bar"]};{c["red"]};{c["red"]}" '
                f'keyTimes="{_keys(0, finish, 1)}" '
                f'dur="{CYCLE}s" repeatCount="indefinite"/>'
            )
        parts.append(
            rect(bar_x, y + 8, bar_w, 10, fill=color, rx=5, children=width_anim + fill_anim)
        )
        # The still frame hides this group, so the base width can be the full bar.
        # Width animate overrides it from 0 while SMIL runs. Fail color base is red,
        # and the fill animate starts green. Good.
    parts.append("</g>")

    # Fail-only summary. Centered in the right pane so it reads as the
    # command's output, not as another column of the repo list.
    # Visible in the still frame (animation disabled).
    # Counts come from REPOS: 8 folders, 2 failures, so 6 ok.
    failed = [name for name, _s, _f, fail in REPOS if fail]
    ok_n = len(REPOS) - len(failed)
    if len(failed) != 2:
        raise SystemExit(f"demo summary card is laid out for 2 failures, got {failed}")
    summary = f"{ok_n}/{len(REPOS)} ok, {len(failed)} failed: {' '.join(failed)}"
    pane_cx = 720
    sy = 250
    parts.append('<g opacity="1">' + anim_opacity("0;0;1;1;0", _keys(0, 0.40, 0.48, 0.92, 1)))
    parts.append(
        rect(532, sy - 28, 376, 108, fill=c["bar_bg"], rx=10, extra=f' stroke="{c["border"]}" stroke-width="1"')
    )
    for i, name in enumerate(failed):
        parts.append(text(pane_cx, sy + i * 28, f"FAIL {name}", fill=c["red"], size=15, weight="650", family=MONO, anchor="middle"))
    parts.append(text(pane_cx, sy + 58, summary, fill=c["ink"], size=14, family=MONO, anchor="middle"))
    parts.append("</g>")

    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    badges = [
        ("mit", "MIT"),
        ("deps", "Zero dependencies"),
        ("bash", "One Bash file"),
        ("agents", "Claude Code, Cursor, Codex"),
    ]
    for name, theme in THEMES.items():
        (OUT / f"wordmark-{name}.svg").write_text(wordmark(theme))
        (OUT / f"demo-{name}.svg").write_text(demo(theme))
        for stem, label in badges:
            (OUT / f"badge-{stem}-{name}.svg").write_text(badge(label, theme))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
