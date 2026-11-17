import json, glob, random, statistics as st, sys
from tasks import PARALLEL_TASKS
m = sys.argv[1]; arms = sys.argv[2] if len(sys.argv) > 2 else "ABC"
rows = [json.load(open(f)) for f in glob.glob(f"raw/{m}/{sys.argv[3] if len(sys.argv) > 3 else "heldout"}/*.json")]
tasks = ["O_jstests", "O_pytests", "H1_pull_test", "H3_ahead_behind", "T01_dirty", "N_toolz"]
def g(t, a): return [r for r in rows if r["task"] == t and r["arm"] == a]
out = {"model": m, "per_task": {}, "pooled": {}}
print(f"{'task':16}" + "".join(f"| {a}: ok  wall_s  cost_usd  indo -P skill " for a in arms))
for t in tasks:
    line = f"{t:16}"; out["per_task"][t] = {}
    for a in arms:
        x = g(t, a)
        d = {"n": len(x), "correct": sum(r["correct"] for r in x), "wall_mean": round(st.mean(r["wall_s"] for r in x), 1), "wall_sd": round(st.stdev(r["wall_s"] for r in x), 1),
             "cost_mean": round(st.mean(r["cost_usd"] for r in x), 5), "turns_mean": round(st.mean(r["num_turns"] for r in x), 2),
             "indo_runs": sum(r["indo_calls"] > 0 for r in x), "parallel_runs": sum(r["indo_parallel_calls"] > 0 for r in x), "skill_loaded": sum(bool(r["skill_invoked"]) for r in x)}
        out["per_task"][t][a] = d
        line += f"| {d['correct']}/{d['n']} {d['wall_mean']:6.1f} {d['cost_mean']:.4f} {d['indo_runs']} {d['parallel_runs']} {d['skill_loaded']} "
    print(line)
def boot(sel, a, b, key, it=10000):
    rng = random.Random(3); res = []
    ts = [t for t in tasks if sel(t)]
    for _ in range(it):
        sa = sb = 0
        for t in ts:
            xa = [r[key] for r in g(t, a)]; xb = [r[key] for r in g(t, b)]
            sa += st.mean(rng.choice(xa) for _ in xa); sb += st.mean(rng.choice(xb) for _ in xb)
        res.append(sb / sa)
    res.sort(); return [round(res[int(.025 * it)], 3), round(res[int(.975 * it)], 3)]
for label, sel in (("parallel_tasks", lambda t: t in PARALLEL_TASKS), ("all_tasks", lambda t: True), ("other_tasks", lambda t: t not in PARALLEL_TASKS)):
    P = {}
    for a in arms:
        x = [r for r in rows if r["arm"] == a and sel(r["task"])]
        P[a] = {"n": len(x), "correct": sum(r["correct"] for r in x), "wall_mean": round(st.mean(r["wall_s"] for r in x), 2), "cost_mean": round(st.mean(r["cost_usd"] for r in x), 5),
                "cost_total": round(sum(r["cost_usd"] for r in x), 4), "indo_runs": sum(r["indo_calls"] > 0 for r in x), "parallel_runs": sum(r["indo_parallel_calls"] > 0 for r in x),
                "skill_loaded": sum(bool(r["skill_invoked"]) for r in x)}
    for b in arms[1:]:
        P[f"{b}_vs_A"] = {"wall_ratio": round(P[b]["wall_mean"] / P["A"]["wall_mean"], 3), "wall_ratio_boot95": boot(sel, "A", b, "wall_s"),
                          "cost_ratio": round(P[b]["cost_mean"] / P["A"]["cost_mean"], 3), "cost_ratio_boot95": boot(sel, "A", b, "cost_usd")}
    if "B" in arms and "C" in arms:
        P["C_vs_B"] = {"wall_ratio": round(P["C"]["wall_mean"] / P["B"]["wall_mean"], 3), "cost_ratio": round(P["C"]["cost_mean"] / P["B"]["cost_mean"], 3), "cost_ratio_boot95": boot(sel, "B", "C", "cost_usd")}
    out["pooled"][label] = P; print(label, json.dumps(P))
json.dump(out, open(f"{sys.argv[3] if len(sys.argv) > 3 else "heldout"}_{m}.json", "w"), indent=1)
