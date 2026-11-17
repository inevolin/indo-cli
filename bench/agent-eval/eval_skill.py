#!/usr/bin/env python3
"""Usage: eval_skill.py MODEL TAG[:ARM] ...   e.g. claude-sonnet-5-5 devA:A dev_v1:C"""
import os, json, glob, sys, statistics as st
from tasks import PARALLEL_TASKS
B = os.environ.get("BENCH_DIR", "/tmp/indo-agent-bench"); m = sys.argv[1]
def load(spec):
    tag, _, arm = spec.partition(":")
    path = f"{B}/raw/{m}/{tag}/*.json" if tag != "-" else f"{B}/raw/{m}/*.json"
    return [r for r in (json.load(open(f)) for f in glob.glob(path)) if r["rep"] > 0 and (not arm or r["arm"] == arm)]
sets = {s: load(s) for s in sys.argv[2:]}
tasks = sorted({r["task"] for rs in sets.values() for r in rs})
print(f"{'task':16}" + "".join(f"{s:>34}" for s in sets))
agg = {s: {"ok": 0, "n": 0, "cost": [], "wall_par": [], "indo": 0, "par": 0, "skill": 0} for s in sets}
for t in tasks:
    row = f"{t:16}"
    for s, rs in sets.items():
        g = [r for r in rs if r["task"] == t]
        if not g: row += f"{'-':>34}"; continue
        a = agg[s]; a["n"] += len(g); a["ok"] += sum(r["correct"] for r in g); a["cost"] += [r["cost_usd"] for r in g]
        if t in PARALLEL_TASKS: a["wall_par"] += [r["wall_s"] for r in g]
        a["indo"] += sum(r["indo_calls"] > 0 for r in g); a["par"] += sum(r.get("indo_parallel_calls", 0) > 0 for r in g); a["skill"] += sum(bool(r.get("skill_invoked")) for r in g)
        row += f"  {sum(r['correct'] for r in g)}/{len(g)} {st.mean(r['wall_s'] for r in g):5.1f}s ${st.mean(r['cost_usd'] for r in g):.4f} i{sum(r['indo_calls']>0 for r in g)}p{sum(r.get('indo_parallel_calls',0)>0 for r in g)}s{sum(bool(r.get('skill_invoked')) for r in g)}"
    print(row)
for s, a in agg.items():
    if a["n"]: print(f"{s:14} correct {a['ok']}/{a['n']}  mean cost {st.mean(a['cost']):.4f}  mean wall on parallel tasks {st.mean(a['wall_par']) if a['wall_par'] else float('nan'):.1f}s  indo-runs {a['indo']} -P-runs {a['par']} skill-loaded {a['skill']}")
