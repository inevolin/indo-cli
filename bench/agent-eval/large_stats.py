import json, glob, math, random, statistics as st, sys
from tasks import PARALLEL_TASKS
tag = sys.argv[1] if len(sys.argv) > 1 else "large"
rows = [json.load(open(f)) for f in glob.glob(f"raw/claude-sonnet-5-5/{tag}/*.json")]
by = {(r["task"], r["rep"], r["arm"]): r for r in rows}
pairs = [(by[(t, k, "A")], by[(t, k, "C")]) for (t, k, a) in by if a == "A" and (t, k, "C") in by]
tasks = sorted({r["task"] for r in rows})
def gm(x): return math.exp(st.mean(math.log(v) for v in x))
def boot(ps, key, it=10000, seed=5):
    rng = random.Random(seed); out = []
    for _ in range(it):
        s = [rng.choice(ps) for _ in ps]; out.append(gm([c[key] / a[key] for a, c in s]))
    out.sort(); return [round(out[int(.025 * it)], 3), round(out[int(.975 * it)], 3)]
res = {"per_task": {}, "pooled": {}}
print(f"{'task':16} {'A ok':>5} {'C ok':>5} {'A s':>7} {'C s':>7} {'speedup':>8} {'A USD':>7} {'C USD':>7} indo -P")
for t in tasks:
    ps = [p for p in pairs if p[0]["task"] == t]
    A = [a for a, c in ps]; C = [c for a, c in ps]
    d = {"n_pairs": len(ps), "A_correct": sum(r["correct"] for r in A), "C_correct": sum(r["correct"] for r in C),
         "A_wall": round(st.mean(r["wall_s"] for r in A), 1), "C_wall": round(st.mean(r["wall_s"] for r in C), 1),
         "A_cost": round(st.mean(r["cost_usd"] for r in A), 4), "C_cost": round(st.mean(r["cost_usd"] for r in C), 4),
         "C_indo_runs": sum(r["indo_calls"] > 0 for r in C), "C_parallel_runs": sum(r["indo_parallel_calls"] > 0 for r in C),
         "A_parallel_any": sum(any(k in c for c in r["bash_cmds"] for k in ("xargs -P", "parallel", " & ", "&\n", "wait")) for r in A)}
    d["speedup"] = round(d["A_wall"] / d["C_wall"], 2); res["per_task"][t] = d
    print(f"{t:16} {d['A_correct']}/{d['n_pairs']:<3} {d['C_correct']}/{d['n_pairs']:<3} {d['A_wall']:7.1f} {d['C_wall']:7.1f} {d['speedup']:7.2f}x {d['A_cost']:7.4f} {d['C_cost']:7.4f} {d['C_indo_runs']}/{d['n_pairs']} {d['C_parallel_runs']}/{d['n_pairs']}")
for label, sel in (("parallel_tasks", lambda t: t in PARALLEL_TASKS), ("all_tasks", lambda t: True)):
    ps = [p for p in pairs if sel(p[0]["task"])]
    wr = gm([c["wall_s"] / a["wall_s"] for a, c in ps]); cr = gm([c["cost_usd"] / a["cost_usd"] for a, c in ps])
    res["pooled"][label] = {"pairs": len(ps), "A_correct": sum(a["correct"] for a, c in ps), "C_correct": sum(c["correct"] for a, c in ps),
        "A_wall_mean": round(st.mean(a["wall_s"] for a, c in ps), 1), "C_wall_mean": round(st.mean(c["wall_s"] for a, c in ps), 1),
        "wall_ratio_geomean": round(wr, 3), "wall_ratio_boot95": boot(ps, "wall_s"), "speedup_geomean": round(1 / wr, 2),
        "pairs_C_faster": sum(c["wall_s"] < a["wall_s"] for a, c in ps),
        "cost_ratio_geomean": round(cr, 3), "cost_ratio_boot95": boot(ps, "cost_usd"),
        "A_cost_total": round(sum(a["cost_usd"] for a, c in ps), 4), "C_cost_total": round(sum(c["cost_usd"] for a, c in ps), 4),
        "C_indo_runs": sum(c["indo_calls"] > 0 for a, c in ps), "C_parallel_runs": sum(c["indo_parallel_calls"] > 0 for a, c in ps)}
    print(label, json.dumps(res["pooled"][label]))
json.dump(res, open(f"{tag}_stats.json", "w"), indent=1)
