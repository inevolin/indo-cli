#!/usr/bin/env python3
"""Render the README charts from the agent-eval results.

Reads:
  bench/agent-eval/results/runs.csv
  bench/agent-eval/results/large-sensitivity.json
  bench/agent-eval/results/large-stats.json
  bench/agent-eval/results/summary.json

Writes light and dark SVGs to .github/assets/readme/.
Run from anywhere:

  python3 bench/agent-eval/render_readme_charts.py

Numbers on the charts are medians of the 3 paired runs (arm A vs arm C)
for Claude Code with Sonnet 5.5 on the 54-repo workspace. Pooled intervals
come from large-sensitivity.json, which drops the one plain-bash run that
stalled for 355 s. The script checks those files against runs.csv and exits
if they disagree.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "bench" / "agent-eval" / "results"
OUT = ROOT / ".github" / "assets" / "readme"

SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"

# Published narrative order. Speedup falls down the list.
TASKS = [
    ("L1_tests", "All tests"),
    ("L7_fail_behind", "Failing and behind"),
    ("L4_pytests", "Python tests"),
    ("L2_jstests", "JavaScript tests"),
    ("L3_gotests", "Go tests"),
    ("L5_behind", "git fetch"),
    ("L6_pull_test", "Pull 6, then test"),
    ("L8_dirty", "git status"),
]
SLOW = {"L1_tests", "L2_jstests", "L3_gotests", "L4_pytests", "L6_pull_test", "L7_fail_behind"}

THEMES = {
    "light": {
        "bg": "#ffffff",
        "border": "#d0d7de",
        "ink": "#1f2328",
        "muted": "#656d76",
        "faint": "#8c959f",
        "track": "#eef1f4",
        "plain": "#8b949e",
        "plain_block": "#4d5966",
        "plain_edge": "#6e7781",
        "indo": "#1a7f37",
        "indo_soft": "#2da44e",
        "amber": "#9a6700",
        "amber_bar": "#bf8700",
        "slate": "#6e7781",
        "card": "#f6f8fa",
        "card_border": "#d0d7de",
        "line": "#afb8c1",
        "tick": "#ffffff",
        "banner": "#f6f8fa",
        "lane_gap": "#ffffff",
    },
    "dark": {
        "bg": "#0d1117",
        "border": "#30363d",
        "ink": "#e6edf3",
        "muted": "#8b949e",
        "faint": "#6e7681",
        "track": "#21262d",
        "plain": "#6e7681",
        "plain_block": "#6e7681",
        "plain_edge": "#8b949e",
        "indo": "#3fb950",
        "indo_soft": "#56d364",
        "amber": "#d29922",
        "amber_bar": "#e3b341",
        "slate": "#8b949e",
        "card": "#161b22",
        "card_border": "#30363d",
        "line": "#484f58",
        "tick": "#0d1117",
        "banner": "#161b22",
        "lane_gap": "#0d1117",
    },
}


def r1(x: float) -> float:
    """Half-up round to 1 decimal. Avoids banker's rounding."""
    return math.floor(x * 10 + 0.5) / 10


def r2(x: float) -> float:
    return math.floor(x * 100 + 0.5) / 100


def fmt1(x: float) -> str:
    return f"{r1(x):.1f}"


def fmt2(x: float) -> str:
    return f"{r2(x):.2f}"


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def load() -> dict:
    rows = list(csv.DictReader(open(RES / "runs.csv", newline="")))
    if len(rows) != 402:
        sys.exit(f"expected 402 graded runs in runs.csv, found {len(rows)}")

    plain = [r for r in rows if r["arm"] == "A"]
    if len(plain) != 172:
        sys.exit(f"expected 172 plain bash runs, found {len(plain)}")

    large = [
        r
        for r in rows
        if r["model"] == "claude-sonnet-5-5" and r["round_tag"] == "large"
    ]
    if len(large) != 48:
        sys.exit(f"expected 48 large sonnet runs, found {len(large)}")

    by = defaultdict(lambda: {"A": [], "C": []})
    for r in large:
        by[r["task"]][r["arm"]].append(r)

    import statistics as st

    tasks = {}
    correct_a = correct_c = 0
    costs = []
    outlier = None
    for key, _label in TASKS:
        arms = by[key]
        if len(arms["A"]) != 3 or len(arms["C"]) != 3:
            sys.exit(f"{key}: expected 3 runs per arm, got {len(arms['A'])}/{len(arms['C'])}")
        aw = [float(r["wall_s"]) for r in arms["A"]]
        cw = [float(r["wall_s"]) for r in arms["C"]]
        ac = [float(r["cost_usd"]) for r in arms["A"]]
        cc = [float(r["cost_usd"]) for r in arms["C"]]
        costs.extend(ac)
        costs.extend(cc)
        ca = sum(r["correct"] == "True" for r in arms["A"])
        cc_ok = sum(r["correct"] == "True" for r in arms["C"])
        correct_a += ca
        correct_c += cc_ok
        for wall, rep in zip(aw, [r["rep"] for r in arms["A"]]):
            if wall > 100:
                if outlier is not None:
                    sys.exit("more than one stalled plain-bash run")
                outlier = {"task": key, "rep": rep, "wall_s": wall}
        tasks[key] = {
            "a_walls": aw,
            "c_walls": cw,
            "med_a": st.median(aw),
            "med_c": st.median(cw),
            "correct_a": ca,
            "correct_c": cc_ok,
        }
        tasks[key]["speedup"] = tasks[key]["med_a"] / tasks[key]["med_c"]

    if correct_a != 24 or correct_c != 24:
        sys.exit(f"expected 24/24 correct, got {correct_a}/{correct_c}")
    if outlier is None or outlier["task"] != "L3_gotests":
        sys.exit(f"expected the stalled run on L3_gotests, got {outlier}")

    sens = json.loads((RES / "large-sensitivity.json").read_text())
    for key, _label in TASKS:
        published = sens["median"][key]
        got = tasks[key]
        for name, a, b in (
            ("A", got["med_a"], published["A"]),
            ("C", got["med_c"], published["C"]),
        ):
            if abs(a - b) > 0.05:
                sys.exit(f"{key} median {name} {a} disagrees with large-sensitivity {b}")

    slow = sens["parallel_excl_outlier"]
    all_tasks = sens["all_excl_outlier"]
    if slow["pairs"] != 17 or all_tasks["pairs"] != 23:
        sys.exit("sensitivity pair counts are not 17 slow / 23 all")
    if abs(slow["speedup"] - 1.82) > 0.001:
        sys.exit(f"slow speedup {slow['speedup']} is not 1.82")
    if abs(all_tasks["cost_ratio"] - 1.018) > 0.001:
        sys.exit(f"cost ratio {all_tasks['cost_ratio']} is not 1.018")

    # Point estimates recomputed from runs.csv, outlier pair removed.
    # Pair by rep. CSV order is not the pair order.
    by_rep = defaultdict(dict)
    for r in large:
        by_rep[(r["task"], r["rep"])][r["arm"]] = r
    slow_ratios = []
    cost_ratios = []
    for (task, _rep), arms in by_rep.items():
        if float(arms["A"]["wall_s"]) > 100:
            continue
        ratio = float(arms["C"]["wall_s"]) / float(arms["A"]["wall_s"])
        cr = float(arms["C"]["cost_usd"]) / float(arms["A"]["cost_usd"])
        cost_ratios.append(cr)
        if task in SLOW:
            slow_ratios.append(ratio)

    def geomean(xs: list[float]) -> float:
        return math.exp(sum(math.log(v) for v in xs) / len(xs))

    if len(slow_ratios) != 17 or len(cost_ratios) != 23:
        sys.exit("recomputed pair counts do not match the sensitivity file")
    if abs((1 / geomean(slow_ratios)) - slow["speedup"]) > 0.02:
        sys.exit("recomputed slow speedup disagrees with large-sensitivity.json")
    if abs(geomean(cost_ratios) - all_tasks["cost_ratio"]) > 0.005:
        sys.exit("recomputed cost ratio disagrees with large-sensitivity.json")

    stats = json.loads((RES / "large-stats.json").read_text())
    parallel_plain = 0
    parallel_tasks = []
    for key, block in stats["per_task"].items():
        n = block["A_parallel_any"]
        parallel_plain += n
        if n:
            parallel_tasks.append(key)
    if parallel_plain != 2 or parallel_tasks != ["L5_behind"]:
        sys.exit(f"expected 2 plain parallel runs, both on L5_behind, got {parallel_plain} {parallel_tasks}")
    with_outlier = stats["pooled"]["parallel_tasks"]["speedup_geomean"]
    if abs(with_outlier - 2.25) > 0.001:
        sys.exit(f"speedup with the stalled run is {with_outlier}, expected 2.25")

    summary = json.loads((RES / "summary.json").read_text())
    note = summary["agents"]["claude_code_sonnet_5_5"]["workspace_20_repos"]["plain_bash_ran_in_parallel"]
    if note != "0/148 runs":
        sys.exit(f"summary.json 20-repo parallel note changed: {note}")

    wall_lo, wall_hi = slow["ci"]
    cost_lo, cost_hi = all_tasks["cost_ci"]
    mean_cost = sum(costs) / len(costs)

    return {
        "tasks": tasks,
        "outlier_s": outlier["wall_s"],
        "slow_speedup": slow["speedup"],
        "slow_ci": (1 / wall_hi, 1 / wall_lo),
        "cost_ratio": all_tasks["cost_ratio"],
        "cost_ci": (cost_lo, cost_hi),
        "mean_cost": mean_cost,
        "plain_runs": 172,
        "plain_parallel": 2,
        "with_outlier_speedup": with_outlier,
        "correct": (24, 24),
    }


def svg_open(w: int, h: int, title: str, desc: str, theme: dict) -> str:
    c = theme
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title desc">
  <title id="title">{esc(title)}</title>
  <desc id="desc">{esc(desc)}</desc>
  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="14" fill="{c["bg"]}" stroke="{c["border"]}"/>
'''


def svg_close() -> str:
    return "</svg>\n"


def text(x, y, s, *, fill, size, weight="400", anchor="start", family=None, spacing=None) -> str:
    extra = ""
    if spacing is not None:
        extra += f' letter-spacing="{spacing}"'
    fam = family or SANS
    return (
        f'  <text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-family="{fam}" '
        f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}"{extra}>{esc(s)}</text>\n'
    )


def rect(x, y, w, h, *, fill, rx=0, stroke=None, sw=0) -> str:
    stroke_attr = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    return (
        f'  <rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" '
        f'fill="{fill}"{stroke_attr}/>\n'
    )


def line(x1, y1, x2, y2, *, stroke, sw=1, dash=None) -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'  <line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{stroke}" stroke-width="{sw}"{dash_attr}/>\n'
    )


def hero(theme: dict, data: dict) -> str:
    c = theme
    t = data["tasks"]["L1_tests"]
    med_a, med_c = t["med_a"], t["med_c"]
    speed = fmt1(t["speedup"])
    W, H = 960, 488
    title = f"Full test run: plain bash {fmt1(med_a)} seconds, indo {fmt1(med_c)} seconds, {speed}x"
    desc = (
        f"Claude Code with Sonnet 5.5 on 54 repos. Median of 3 runs. "
        f"Plain bash {fmt1(med_a)}s, indo plus the Agent Skill {fmt1(med_c)}s ({speed}x). "
        f"Both setups 24 of 24 correct. Cost {fmt2(data['cost_ratio'])}x "
        f"(95% CI {fmt2(data['cost_ci'][0])}x to {fmt2(data['cost_ci'][1])}x), "
        f"about {fmt2(data['mean_cost'])} USD per run."
    )
    parts = [svg_open(W, H, title, desc, c)]
    parts.append(
        f"  <!-- exact median ratio {t['speedup']:.4f}; walls A {t['a_walls']} C {t['c_walls']} -->\n"
    )

    parts.append(text(40, 48, "Full test run", fill=c["ink"], size=28, weight="650"))
    parts.append(
        text(
            40,
            74,
            "Claude Code, Sonnet 5.5, 54 real repos. Median of 3 paired runs.",
            fill=c["muted"],
            size=15,
        )
    )

    track_x, track_w = 196, 520
    scale_s = 60
    px = track_w / scale_s
    bar_h = 40
    lanes = [
        ("plain bash", med_a, t["a_walls"], c["plain"], c["ink"]),
        ("indo + skill", med_c, t["c_walls"], c["indo"], c["indo"]),
    ]
    first_y = 108
    gap = 28
    for i, (label, med, _walls, color, label_color) in enumerate(lanes):
        y = first_y + i * (bar_h + gap)
        parts.append(text(40, y + 26, label, fill=label_color, size=16, weight="600"))
        parts.append(rect(track_x, y, track_w, bar_h, fill=c["track"], rx=8))
        bw = med * px
        parts.append(rect(track_x, y, bw, bar_h, fill=color, rx=8))
        parts.append(
            text(track_x + bw + 12, y + 26, f"{fmt1(med)}s", fill=c["ink"], size=18, weight="650")
        )

    # Big ratio, aligned to the right edge, vertically centered on the indo lane.
    indo_y = first_y + (bar_h + gap)
    parts.append(text(920, indo_y + 22, f"{speed}x", fill=c["indo"], size=36, weight="650", anchor="end"))
    parts.append(text(920, indo_y + 44, "faster", fill=c["indo"], size=14, weight="600", anchor="end"))

    axis_y = indo_y + bar_h + 22
    parts.append(line(track_x, axis_y, track_x + track_w, axis_y, stroke=c["line"], sw=1))
    for sec in (0, 15, 30, 45, 60):
        x = track_x + sec * px
        parts.append(line(x, axis_y, x, axis_y + 6, stroke=c["line"], sw=1))
        label = f"{sec}s" if sec else "0"
        anchor = "start" if sec == 0 else "end" if sec == 60 else "middle"
        parts.append(text(x, axis_y + 22, label, fill=c["faint"], size=12, anchor=anchor))

    # Stat row.
    card_y = axis_y + 44
    card_h = 86
    card_w = 276
    cards = [
        (f"{speed}x", "faster", c["indo"]),
        ("24/24", "same answers", c["ink"]),
        (f"{fmt2(data['cost_ratio'])}x", "same cost", c["ink"]),
    ]
    for i, (num, label, color) in enumerate(cards):
        x = 40 + i * (card_w + 16)
        parts.append(rect(x, card_y, card_w, card_h, fill=c["card"], rx=10, stroke=c["card_border"], sw=1))
        parts.append(text(x + card_w / 2, card_y + 40, num, fill=color, size=30, weight="650", anchor="middle"))
        parts.append(text(x + card_w / 2, card_y + 66, label, fill=c["muted"], size=15, anchor="middle"))

    cap_y = card_y + card_h + 28
    plain_runs = ", ".join(f"{fmt1(v)}s" for v in sorted(t["a_walls"]))
    indo_runs = ", ".join(f"{fmt1(v)}s" for v in sorted(t["c_walls"]))
    parts.append(
        text(
            40,
            cap_y,
            f"Cost {fmt2(data['cost_ratio'])}x "
            f"(95% CI {fmt2(data['cost_ci'][0])}x to {fmt2(data['cost_ci'][1])}x), "
            f"about {fmt2(data['mean_cost'])} USD per run.",
            fill=c["muted"],
            size=13,
        )
    )
    parts.append(
        text(
            40,
            cap_y + 20,
            f"The 3 plain runs: {plain_runs}. The 3 indo runs: {indo_runs}.",
            fill=c["muted"],
            size=13,
        )
    )
    parts.append(svg_close())
    return "".join(parts)


def bar_color(speed: float, c: dict) -> str:
    if speed < 0.95:
        return c["amber_bar"]
    if speed < 1.15:
        return c["slate"]
    return c["indo"]


def label_color(speed: float, c: dict) -> str:
    if speed < 0.95:
        return c["amber"]
    if speed < 1.15:
        return c["muted"]
    return c["indo"]


def tasks_chart(theme: dict, data: dict) -> str:
    c = theme
    W, H = 960, 612
    bits = []
    for key, label in TASKS:
        t = data["tasks"][key]
        bits.append(
            f"{label} {fmt1(t['speedup'])}x ({fmt1(t['med_a'])}s plain, {fmt1(t['med_c'])}s indo)"
        )
    title = "Speedup by task"
    desc = (
        "Median speedup, plain bash over indo, 3 runs each. "
        + "; ".join(bits)
        + f". Six slow tasks pooled: {fmt1(data['slow_speedup'])}x "
        f"(95% CI {fmt1(data['slow_ci'][0])}x to {fmt1(data['slow_ci'][1])}x). "
        f"One plain Go run of {data['outlier_s']:.0f}s is excluded from that pool."
    )
    parts = [svg_open(W, H, title, desc, c)]
    parts.append(text(40, 48, "Speedup by task", fill=c["ink"], size=28, weight="650"))
    parts.append(
        text(
            40,
            74,
            "1x is no change. Bars that pass the line are faster. Median of 3 runs.",
            fill=c["muted"],
            size=15,
        )
    )

    label_x = 212
    bar_x = 228
    px = 108  # pixels per 1x, so 3.3x is about 356px and 4x would be 432
    row_h = 52
    row0 = 108
    plot_bottom = row0 + row_h * len(TASKS) - 10

    # 2x and 3x sit behind the bars. 1x is drawn after them so it stays visible.
    for mult, name in ((2, "2x"), (3, "3x")):
        x = bar_x + mult * px
        parts.append(line(x, row0 - 6, x, plot_bottom, stroke=c["track"], sw=1, dash="3 4"))
        parts.append(text(x, row0 - 16, name, fill=c["faint"], size=12, anchor="middle"))

    for i, (key, label) in enumerate(TASKS):
        t = data["tasks"][key]
        speed = t["speedup"]
        y = row0 + i * row_h
        cy = y + 16
        shown = label + (" *" if key == "L3_gotests" else "")
        parts.append(text(label_x, cy + 5, shown, fill=c["ink"], size=16, anchor="end"))
        bw = max(speed * px, 2)
        parts.append(rect(bar_x, cy - 7, bw, 14, fill=bar_color(speed, c), rx=4))
        speed_s = f"{fmt1(speed)}x"
        times = f"{fmt1(t['med_a'])}s  to  {fmt1(t['med_c'])}s"
        parts.append(text(700, cy + 5, speed_s, fill=label_color(speed, c), size=16, weight="650"))
        parts.append(text(762, cy + 5, times, fill=c["muted"], size=15, family=MONO))

    one_x = bar_x + px
    parts.append(line(one_x, row0 - 6, one_x, plot_bottom, stroke=c["line"], sw=1.5))
    parts.append(text(one_x, row0 - 16, "1x", fill=c["ink"], size=13, weight="650", anchor="middle"))

    foot = plot_bottom + 36
    parts.append(
        text(
            40,
            foot,
            f"6 slow tasks together: {fmt1(data['slow_speedup'])}x "
            f"(95% CI {fmt1(data['slow_ci'][0])}x to {fmt1(data['slow_ci'][1])}x). "
            f"git status got slower. Fetch, and a pull of 6 repos, barely moved.",
            fill=c["muted"],
            size=13,
        )
    )
    parts.append(
        text(
            40,
            foot + 22,
            f"* Go median is {fmt1(data['tasks']['L3_gotests']['med_a'])}s. "
            f"One plain bash run took {data['outlier_s']:.0f}s and is left out of the 1.8x pool. "
            f"With it, that pool is {data['with_outlier_speedup']:.2f}x.",
            fill=c["muted"],
            size=13,
        )
    )
    parts.append(svg_close())
    return "".join(parts)


def serial(theme: dict, data: dict) -> str:
    c = theme
    t = data["tasks"]["L1_tests"]
    W, H = 960, 560
    title = "Serial loop versus indo in parallel"
    desc = (
        "Schematic of 8 equal repos. Plain bash runs them one after another. "
        f"indo -P 8 runs them at once. In {data['plain_runs']} plain bash runs the agent "
        f"did this in parallel {data['plain_parallel']} times, both git fetch, never tests. "
        f"Real suites are uneven, so the measured all-tests speedup is {fmt1(t['speedup'])}x, not 8x."
    )
    parts = [svg_open(W, H, title, desc, c)]
    parts.append(text(40, 48, "One loop, or all at once", fill=c["ink"], size=28, weight="650"))
    parts.append(
        text(
            40,
            74,
            f"Schematic of 8 equal repos. Real suites are uneven, so all tests were {fmt1(t['speedup'])}x, not 8x.",
            fill=c["muted"],
            size=15,
        )
    )

    n = 8
    left = 40
    right = 920
    gap = 8
    block_w = (right - left - (n - 1) * gap) / n

    parts.append(text(40, 118, "Plain bash", fill=c["ink"], size=16, weight="600"))
    parts.append(
        text(
            148,
            118,
            'for d in */; do (cd "$d" && ./ci.sh); done',
            fill=c["muted"],
            size=14,
            family=MONO,
        )
    )

    by = 132
    bh = 44
    for i in range(n):
        x = left + i * (block_w + gap)
        parts.append(rect(x, by, block_w, bh, fill=c["plain_block"], rx=7))
        parts.append(
            text(x + block_w / 2, by + 28, str(i + 1), fill="#ffffff", size=16, weight="650", anchor="middle")
        )

    parts.append(text(40, 214, "indo -P 8", fill=c["indo"], size=16, weight="600"))
    parts.append(
        text(
            156,
            214,
            "indo -f -P 8 */ ./ci.sh",
            fill=c["muted"],
            size=14,
            family=MONO,
        )
    )

    lanes_y = 232
    lane_h = 18
    lane_gap = 4
    stack_h = n * lane_h + (n - 1) * lane_gap
    # Faint track shows the time the serial loop is still busy.
    parts.append(rect(left, lanes_y, right - left, stack_h, fill=c["track"], rx=8))
    for i in range(n):
        y = lanes_y + i * (lane_h + lane_gap)
        parts.append(rect(left, y, block_w, lane_h, fill=c["indo"], rx=4))
    # "done" just to the right of the stack, centered on it.
    note_x = left + block_w + 16
    note_y = lanes_y + stack_h / 2
    parts.append(text(note_x, note_y - 2, "finished", fill=c["indo"], size=16, weight="650"))
    parts.append(
        text(
            note_x,
            note_y + 20,
            "the serial loop is still on repo 2",
            fill=c["muted"],
            size=14,
        )
    )

    banner_y = lanes_y + stack_h + 28
    banner_h = 78
    parts.append(rect(40, banner_y, 880, banner_h, fill=c["banner"], rx=10, stroke=c["card_border"], sw=1))
    parts.append(
        text(64, banner_y + 48, f"{data['plain_parallel']} of {data['plain_runs']}", fill=c["indo"], size=28, weight="650")
    )
    parts.append(
        text(
            250,
            banner_y + 34,
            "plain bash runs started the next folder before the previous one finished.",
            fill=c["ink"],
            size=15,
        )
    )
    parts.append(
        text(
            250,
            banner_y + 58,
            "Both times it was git fetch. It never ran tests in parallel.",
            fill=c["ink"],
            size=15,
        )
    )
    parts.append(svg_close())
    return "".join(parts)


def write(name: str, body: str) -> None:
    path = OUT / name
    path.write_text(body)
    # Well-formed and carries the headline figures.
    if "<svg" not in body or "</svg>" not in body:
        sys.exit(f"{name} is not an svg")
    if "53.0s" not in body and name.startswith("hero"):
        sys.exit(f"{name} missing 53.0s")


def main() -> None:
    data = load()
    OUT.mkdir(parents=True, exist_ok=True)
    t = data["tasks"]["L1_tests"]
    charts = {
        "hero": hero,
        "tasks": tasks_chart,
        "serial": serial,
    }
    for theme_name, theme in THEMES.items():
        for stem, fn in charts.items():
            write(f"{stem}-{theme_name}.svg", fn(theme, data))

    print("wrote", OUT)
    print(f"full test  {fmt1(t['med_a'])}s -> {fmt1(t['med_c'])}s  {fmt1(t['speedup'])}x")
    print(f"correct    {data['correct'][0]}/{data['correct'][1]}")
    print(
        f"cost       {fmt2(data['cost_ratio'])}x  "
        f"CI {fmt2(data['cost_ci'][0])}x to {fmt2(data['cost_ci'][1])}x  "
        f"mean {data['mean_cost']:.4f} USD"
    )
    print(
        f"slow       {fmt1(data['slow_speedup'])}x  "
        f"CI {fmt1(data['slow_ci'][0])}x to {fmt1(data['slow_ci'][1])}x  "
        f"outlier {data['outlier_s']:.0f}s"
    )
    for key, label in TASKS:
        task = data["tasks"][key]
        print(
            f"  {label:22} {fmt1(task['med_a'])}s -> {fmt1(task['med_c'])}s   "
            f"{fmt1(task['speedup'])}x   exact {task['speedup']:.3f}"
        )
    print(f"parallel   {data['plain_parallel']} of {data['plain_runs']} plain bash runs")


if __name__ == "__main__":
    main()
