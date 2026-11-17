#!/usr/bin/env python3
import os, json, math, itertools, random, statistics as st, sys
from pathlib import Path
import numpy as np
B = Path(os.environ.get("BENCH_DIR", "/tmp/indo-agent-bench"))
MODELS = [m for m in sys.argv[1:]] or [p.name for p in sorted((B / "raw").iterdir()) if p.name != "pilot"]
def load(m):
    return [json.loads(p.read_text()) for p in sorted((B / "raw" / m).glob("*.json")) if json.loads(p.read_text())["rep"] > 0]
def tot_in(r): u = r["usage"]; return sum((u.get(k) or 0) for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
def wilcoxon_exact(d):
    d = [x for x in d if abs(x) > 1e-12]; n = len(d)
    if n == 0: return 1.0
    ranks = st.mean  # average ranks for ties
    a = sorted(range(n), key=lambda i: abs(d[i])); r = [0.0] * n; i = 0
    while i < n:
        j = i
        while j + 1 < n and abs(abs(d[a[j + 1]]) - abs(d[a[i]])) < 1e-12: j += 1
        for k in range(i, j + 1): r[a[k]] = (i + j) / 2 + 1
        i = j + 1
    w = sum(r[i] for i in range(n) if d[i] > 0); mu = sum(r) / 2
    cnt = sum(1 for s in itertools.product([0, 1], repeat=n) if abs(sum(r[i] for i in range(n) if s[i]) - mu) >= abs(w - mu) - 1e-9)
    return cnt / 2 ** n
def sign_test(wins, losses):
    n = wins + losses
    if n == 0: return 1.0
    k = min(wins, losses); p = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * p)
def boot_ratio(rows, key, it=5000, seed=1):
    rng = random.Random(seed); tasks = sorted({r["task"] for r in rows}); out = []
    by = {(t, a): [r[key] for r in rows if r["task"] == t and r["arm"] == a] for t in tasks for a in "AB"}
    for _ in range(it):
        ts = [rng.choice(tasks) for _ in tasks]; la, lb = [], []
        for t in ts:
            la.append(st.mean(rng.choice(by[(t, "A")]) for _ in by[(t, "A")])); lb.append(st.mean(rng.choice(by[(t, "B")]) for _ in by[(t, "B")]))
        out.append(sum(lb) / sum(la))
    out.sort(); return out[int(0.025 * it)], out[int(0.975 * it)]
report = {}
SETS = []
for m in MODELS:
    allrows = load(m)
    for tier, pred in (("tier1", lambda r: r["task"].startswith("T")), ("tier2", lambda r: r["task"].startswith("H")), ("all", lambda r: True)):
        SETS.append((f"{m}|{tier}", [r for r in allrows if pred(r)]))
for m, rows in SETS:
    if not rows: continue
    for r in rows: r["tokens_in"] = tot_in(r); r["tokens_out"] = r["usage"]["output_tokens"] or 0; r["correct_i"] = int(bool(r["correct"]))
    tasks = sorted({r["task"] for r in rows}); per = []
    for t in tasks:
        e = {"task": t}
        for a in "AB":
            g = [r for r in rows if r["task"] == t and r["arm"] == a]
            e[a] = {"n": len(g), "correct": sum(r["correct_i"] for r in g), "partial_mean": round(st.mean(r["partial"] for r in g), 3),
                    "cost_mean": round(st.mean(r["cost_usd"] for r in g), 5), "tokens_in_mean": round(st.mean(r["tokens_in"] for r in g)),
                    "tokens_out_mean": round(st.mean(r["tokens_out"] for r in g)), "tool_calls_mean": round(st.mean(r["tool_calls"] for r in g), 2),
                    "turns_mean": round(st.mean(r["num_turns"] or 0 for r in g), 2), "wall_mean": round(st.mean(r["wall_s"] for r in g), 1),
                    "errors": sum(1 for r in g if r["subtype"] != "success"), "indo_used_runs": sum(1 for r in g if r["indo_calls"] > 0)}
        e["cost_ratio_B_over_A"] = round(e["B"]["cost_mean"] / e["A"]["cost_mean"], 3)
        per.append(e)
    def pooled(a, k): g = [r[k] for r in rows if r["arm"] == a]; return st.mean(g)
    acc_d = [p["B"]["correct"] - p["A"]["correct"] for p in per]
    pool = {"n_runs": {a: sum(1 for r in rows if r["arm"] == a) for a in "AB"},
            "correct": {a: sum(r["correct_i"] for r in rows if r["arm"] == a) for a in "AB"},
            "tasks_B_more_correct": sum(1 for d in acc_d if d > 0), "tasks_A_more_correct": sum(1 for d in acc_d if d < 0), "tasks_tied_correct": sum(1 for d in acc_d if d == 0),
            "sign_test_p_accuracy": round(sign_test(sum(1 for d in acc_d if d > 0), sum(1 for d in acc_d if d < 0)), 4)}
    for k in ("cost_usd", "tokens_in", "tokens_out", "tool_calls", "num_turns", "wall_s"):
        ma, mb = pooled("A", k), pooled("B", k)
        ta = {p["task"]: st.mean(r[k] or 0 for r in rows if r["task"] == p["task"] and r["arm"] == "A") for p in per}
        tb = {p["task"]: st.mean(r[k] or 0 for r in rows if r["task"] == p["task"] and r["arm"] == "B") for p in per}
        ld = [math.log(max(tb[t], 1e-9) / max(ta[t], 1e-9)) for t in ta]
        sd = st.stdev(ld) if len(ld) > 1 else float("nan")
        lo, hi = boot_ratio(rows, k)
        pool[k] = {"mean_A": round(ma, 5), "mean_B": round(mb, 5), "ratio_B_over_A": round(mb / ma, 3), "boot95_ratio": [round(lo, 3), round(hi, 3)],
                   "geo_mean_task_ratio": round(math.exp(st.mean(ld)), 3), "tasks_B_lower": sum(1 for x in ld if x < 0), "tasks_B_higher": sum(1 for x in ld if x > 0),
                   "wilcoxon_exact_p": round(wilcoxon_exact(ld), 4), "cohens_dz_log": round(st.mean(ld) / sd, 2) if sd and sd > 0 else None}
    adoption = sum(1 for r in rows if r["arm"] == "B" and r["indo_calls"] > 0)
    pool["indo_adoption_B_runs"] = f"{adoption}/{pool['n_runs']['B']}"
    pool["spend_usd"] = round(sum(r["cost_usd"] for r in rows), 4)
    failures = [{"id": r["id"], "subtype": r["subtype"], "detail": r["detail"]} for r in rows if not r["correct"]]
    report[m] = {"per_task": per, "pooled": pool, "incorrect_runs": failures}
json.dump(report, open(B / "summary.json", "w"), indent=1)
for m, R in report.items():
    print(f"\n=== {m} ===")
    print(f"{'task':12} {'A ok':>5} {'B ok':>5} {'A $':>8} {'B $':>8} {'B/A':>5} {'A tools':>7} {'B tools':>7} {'A s':>6} {'B s':>6} {'indo':>4}")
    for p in R["per_task"]:
        A, Bb = p["A"], p["B"]
        print(f"{p['task']:12} {A['correct']}/{A['n']:<3} {Bb['correct']}/{Bb['n']:<3} {A['cost_mean']:8.4f} {Bb['cost_mean']:8.4f} {p['cost_ratio_B_over_A']:5.2f} {A['tool_calls_mean']:7.2f} {Bb['tool_calls_mean']:7.2f} {A['wall_mean']:6.1f} {Bb['wall_mean']:6.1f} {Bb['indo_used_runs']:>4}")
    print(json.dumps(R["pooled"], indent=1))
    for f in R["incorrect_runs"]: print("WRONG", f["id"], f["subtype"], json.dumps(f["detail"])[:300])
