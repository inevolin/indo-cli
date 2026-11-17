import os, json, glob, subprocess
from pathlib import Path
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt, numpy as np
B = Path(os.environ.get("BENCH_DIR", "/tmp/indo-agent-bench")); S = json.load(open(B / "summary.json"))
from tasks import TASKS, prompt
runs = [json.load(open(f)) for f in sorted(glob.glob(str(B / "raw/claude-*/*.json")))]
runs = [r for r in runs if r["rep"] > 0]
L = json.load(open(B / "ledger.json"))
meta = {"date_utc": "2026-11-17", "claude_code_version": subprocess.run([os.environ.get("CLAUDE_BIN", "claude"), "--version"], capture_output=True, text=True).stdout.strip(),
  "models": ["claude-sonnet-5-5", "claude-haiku-5-5"], "indo_commit": (B / "indo_commit.txt").read_text().strip(), "indo_version": "1.2.0",
  "prices_usd_per_mtok": {"claude-sonnet-5-5": {"input": 2, "cache_write_5m": 2.5, "cache_read": 0.10, "output": 10},
                           "claude-haiku-5-5": {"input": 0.10, "cache_write_5m": 0.125, "cache_read": 0.01, "output": 0.50},
                           "source": "https://platform.claude.com/docs/en/about-claude/pricing (fetched 2026-11-17)"},
  "arms": {"A": "plain bash; indo not on PATH; no extra prompt", "B": "indo on PATH + appended system note: one sentence + indo --help (585 tokens)"},
  "harness": "claude -p, stream-json, fresh CLAUDE_CONFIG_DIR per run, --setting-sources project, no MCP, WebFetch/WebSearch/Task/Agent disallowed, --dangerously-skip-permissions, max-turns 40, max-budget 0.40/run; workspace reset from template.tgz before every run; 3 slots in parallel; randomized order",
  "workspace": "20 shallow-cloned public repos (indo-cli bench/setup_workspace.sh) + local bare remotes; seeded: 5 behind, 2 ahead, 6 dirty, 1 feature branch, 4 failing test suites, 2 license files removed",
  "prompts": {t: prompt(t) for t in TASKS}, "total_spend_usd_incl_pilot_and_probe": L["spend_usd"]}
json.dump({"meta": meta, "ground_truth": json.load(open(B / "ground_truth.json"))["answers"], "summary": S, "runs": runs}, open(B / "results.json", "w"), indent=1)
fig, ax = plt.subplots(1, 3, figsize=(16, 5.5))
models = [("claude-sonnet-5-5", "Sonnet 5.5"), ("claude-haiku-5-5", "Haiku 5.5")]
x = np.arange(2); w = 0.35
for i, arm in enumerate("AB"):
    vals = [S[f"{m}|all"]["pooled"]["correct"][arm] / S[f"{m}|all"]["pooled"]["n_runs"][arm] * 100 for m, _ in models]
    b = ax[0].bar(x + (i - .5) * w, vals, w, label="plain bash" if arm == "A" else "with indo", color="#888" if arm == "A" else "#2b7bba")
    for xi, v, (m, _) in zip(x + (i - .5) * w, vals, models):
        p = S[f"{m}|all"]["pooled"]; ax[0].text(xi, v + 1, f"{p['correct'][arm]}/{p['n_runs'][arm]}", ha="center", fontsize=9)
ax[0].set_xticks(x, [n for _, n in models]); ax[0].set_ylim(0, 125); ax[0].set_ylabel("% runs fully correct"); ax[0].set_title("Correct answers (14 tasks x 3 runs)"); ax[0].legend(loc="upper center", ncol=2)
tasks = [p["task"] for p in S["claude-sonnet-5-5|all"]["per_task"]]; y = np.arange(len(tasks))
for j, (key, title, axi) in enumerate([("cost_mean", "Cost per run, with indo / plain bash", ax[1]), ("wall_mean", "Wall time per run, with indo / plain bash", ax[2])]):
    for i, (m, n) in enumerate(models):
        pt = {p["task"]: p for p in S[f"{m}|all"]["per_task"]}
        r = [pt[t]["B"][key] / pt[t]["A"][key] for t in tasks]
        axi.barh(y + (i - .5) * w, r, w, label=n, color=["#2b7bba", "#e08a2b"][i])
    axi.axvline(1, color="k", lw=1); axi.set_yticks(y, tasks, fontsize=8); axi.invert_yaxis(); axi.set_title(title); axi.set_xlabel("ratio (below 1 = indo better)"); axi.legend(fontsize=8)
fig.suptitle("Does indo help a coding agent (Claude Code) on multi-repo tasks? 168 runs, 20 repos", fontsize=12)
fig.tight_layout(); fig.savefig(B / "chart.png", dpi=130); print("ok", len(runs))
