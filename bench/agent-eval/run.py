#!/usr/bin/env python3
"""indo agent bench runner. The API key is read from file into the child env only; never printed or stored."""
import json, os, random, re, shutil, subprocess, sys, threading, time, uuid, queue
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from tasks import prompt, TASKS
B = Path(os.environ.get("BENCH_DIR", "/tmp/indo-agent-bench")); CLAUDE = os.environ.get("CLAUDE_BIN", "claude"); KEY = Path(os.environ["ANTHROPIC_KEY_FILE"])  # a file that holds your API key
CAP = float(os.environ.get("CAP_USD", "7.0")); PER_RUN_MAX = float(os.environ.get("PER_RUN_MAX", "0.40"))
MODEL = os.environ.get("MODEL", "claude-sonnet-5-5")
TAG = os.environ.get("RUN_TAG", ""); SKILL_FILE = os.environ.get("SKILL_FILE", "")
RAW = B / "raw" / MODEL / TAG if TAG else B / "raw" / MODEL; RAW.mkdir(parents=True, exist_ok=True)
LEDGER = Path(os.environ.get("LEDGER", str(B / "ledger.json")))
SOURCES = os.environ.get("SETTING_SOURCES", "project"); LOCK = threading.Lock()
GTALL = json.load(open(os.environ.get("GT_FILE", str(B / "ground_truth.json")))); GT = GTALL["answers"]
HELP = subprocess.run(["bash", str(B / "indo.sh"), "--help"], capture_output=True, text=True).stdout.strip()
NOTE_B = ("The `indo` command is installed on PATH. It runs one command in many folders. "
          "This is its --help output:\n\n" + HELP)
def now(): return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
def ledger():
    return json.load(open(LEDGER)) if LEDGER.exists() else {"spend_usd": 0.0, "runs": 0}
def log(m):
    with LOCK:
        with open(B / "runner.log", "a") as f: f.write(f"[{now()}] {m}\n")
def reset_slot(slot):
    S = B / "slots" / slot
    if S.exists(): shutil.rmtree(S)
    S.mkdir(parents=True)
    subprocess.run(["tar", "xzf", os.environ.get("TEMPLATE", str(B / "template.tgz")), "-C", str(S)], check=True)
    (S / "bin").mkdir(); shutil.copy2(B / "indo.sh", S / "bin" / "indo"); os.chmod(S / "bin" / "indo", 0o755)
    for r in (S / "repos").iterdir():
        subprocess.run(["git", "remote", "set-url", "origin", str(S / "remotes" / f"{r.name}.git")], cwd=r, check=True)
    return S
def parse_answer(text, task):
    lines = [l for l in (text or "").splitlines() if l.strip().upper().startswith("ANSWER:")]
    if not lines: return None
    body = lines[-1].split(":", 1)[1].strip().strip("`*").strip()
    if task in ("N_branch", "N_toolz"):
        return body.strip().strip("`.").strip()
    if task == "H3_ahead_behind":
        return {k.strip("`"): f"{a}/{b}" for k, a, b in re.findall(r"([\w.\-]+)\s*=\s*(\d+)\s*/\s*(\d+)", body)}
    if task == "T08_todo":
        return {k.strip().strip("`"): int(v) for k, v in re.findall(r"([\w.\-]+)\s*[=:]\s*(\d+)", body)}
    if body.lower().rstrip(".") == "none": return []
    return sorted({x.strip().strip("`*/").strip() for x in body.split(",") if x.strip()})
def g(S, r, c): return subprocess.run(c, cwd=S / "repos" / r, shell=True, capture_output=True, text=True).stdout.strip()
def grade(task, ans, S):
    gt = GT[task]
    if task in ("N_branch", "N_toolz"):
        ok = ans == gt; return ok, float(ok), {"expected": gt, "got": ans}
    if task == "H3_ahead_behind":
        ok = ans is not None and ans == gt
        return ok, sum(1 for k, v in gt.items() if ans and ans.get(k) == v) / len(gt), {"expected": gt, "got": ans}
    if task in ("H1_pull_test", "H4_commit_readme", "L6_pull_test"):
        exp = set(gt); got = set(ans or []); bad = []
        for r, h in GTALL["template_heads"].items():
            head = g(S, r, "git rev-parse HEAD")
            if task in ("H1_pull_test", "L6_pull_test"):
                want = GTALL["upstream_heads"][r] if r in GTALL["H1_behind"] else h
                if head != want: bad.append(f"{r}: HEAD not as expected")
            else:
                if r in exp:
                    if g(S, r, "git rev-parse HEAD^") != h: bad.append(f"{r}: not exactly one new commit")
                    elif g(S, r, "git log -1 --format=%s") != "docs: wip": bad.append(f"{r}: wrong message")
                    elif len(g(S, r, "git diff --name-only HEAD^ HEAD").splitlines()) != 1 or "readme" not in g(S, r, "git diff --name-only HEAD^ HEAD").lower(): bad.append(f"{r}: commit touches more than the README")
                    elif g(S, r, "git status --porcelain"): bad.append(f"{r}: still dirty")
                else:
                    if head != h: bad.append(f"{r}: HEAD changed")
                    elif g(S, r, "git status --porcelain") != GTALL["template_status"][r]: bad.append(f"{r}: status changed")
        ok = ans is not None and got == exp and not bad
        tp = len(got & exp); f1 = 2 * tp / (len(got) + len(exp)) if (got or exp) else 1.0
        return ok, f1, {"expected": sorted(exp), "got": ans, "state_problems": bad}
    if task == "T08_todo":
        ok = ans is not None and ans == gt
        corr = sum(1 for k, v in gt.items() if ans and ans.get(k) == v)
        fp = sum(1 for k, v in (ans or {}).items() if gt.get(k) != v and k not in gt)
        return ok, corr / len(gt), {"expected": gt, "got": ans}
    exp = set(gt); got = set(ans or [])
    if task == "T10_touch":
        created = sorted(p.parent.name for p in (S / "repos").glob("*/.bench-ok"))
        stray = sorted(str(p.relative_to(S / "repos")) for p in (S / "repos").rglob(".bench-ok") if p.parent.parent != S / "repos")
        ok = set(created) == exp and not stray and ans is not None and got == exp
        tp = len(set(created) & exp); f1 = 2 * tp / (len(created) + len(exp)) if (created or exp) else 1.0
        return ok, f1, {"expected": sorted(exp), "got": ans, "created": created, "stray": stray}
    ok = ans is not None and got == exp
    tp = len(got & exp); f1 = 2 * tp / (len(got) + len(exp)) if (got or exp) else 1.0
    return ok, f1, {"expected": sorted(exp), "got": ans}
def run_one(job, slot):
    task, arm, rep = job["task"], job["arm"], job["rep"]
    rid = f"{task}_{arm}_r{rep}"; cfgid = MODEL + "_" + TAG + "_" + rid
    S = reset_slot(slot)
    cfg = B / "cfg" / cfgid
    if cfg.exists(): shutil.rmtree(cfg)
    cfg.mkdir(parents=True)
    if arm == "C":
        (cfg / "skills" / "indo").mkdir(parents=True); shutil.copy2(SKILL_FILE, cfg / "skills" / "indo" / "SKILL.md")
    env = {k: v for k, v in os.environ.items() if not k.startswith(("ANTHROPIC", "CLAUDE"))}
    env["CLAUDE_CONFIG_DIR"] = str(cfg)
    env["ANTHROPIC_API_KEY"] = KEY.read_text().strip()
    base_path = "/usr/local/go/bin:/usr/local/bin:/usr/bin:/bin"
    env["PATH"] = (str(S / "bin") + ":" + base_path) if arm in ("B", "C") else base_path
    env["DISABLE_AUTOUPDATER"] = "1"; env["DISABLE_TELEMETRY"] = "1"
    argv = [CLAUDE, "-p", prompt(task), "--output-format", "stream-json", "--verbose", "--model", MODEL,
            "--max-turns", "40", "--max-budget-usd", str(PER_RUN_MAX), "--dangerously-skip-permissions",
            "--disallowedTools", "WebFetch", "WebSearch", "Task", "Agent",
            "--setting-sources", SOURCES, "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}']
    if arm == "B": argv += ["--append-system-prompt", NOTE_B]
    t0 = time.time(); start = now()
    try:
        p = subprocess.run(argv, cwd=S / "repos", env=env, capture_output=True, text=True, timeout=1200)
        out, err, rc = p.stdout, p.stderr, p.returncode
    except subprocess.TimeoutExpired as e:
        out, err, rc = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or ""), "TIMEOUT", -9
    del env
    wall = time.time() - t0
    (RAW / f"{rid}.jsonl").write_text(out); (RAW / f"{rid}.stderr").write_text(err[-5000:])
    res, tools, bash_cmds, skills_used = {}, [], [], []
    for line in out.splitlines():
        try: ev = json.loads(line)
        except Exception: continue
        if ev.get("type") == "result": res = ev
        if ev.get("type") == "assistant":
            for c in ev.get("message", {}).get("content", []):
                if c.get("type") == "tool_use":
                    tools.append(c.get("name"))
                    if c.get("name") == "Skill": skills_used.append(json.dumps(c.get("input")))
                    if c.get("name") == "Bash": bash_cmds.append(c.get("input", {}).get("command", ""))
    text = res.get("result", "")
    ans = parse_answer(text, task)
    ok, partial, detail = grade(task, ans, S)
    u = res.get("usage", {}) or {}
    cost = float(res.get("total_cost_usd") or 0.0)
    rec = {"id": rid, "task": task, "arm": arm, "rep": rep, "order": job["order"], "slot": slot, "model": MODEL,
           "start_utc": start, "wall_s": round(wall, 1), "rc": rc, "subtype": res.get("subtype"), "is_error": res.get("is_error"),
           "num_turns": res.get("num_turns"), "duration_ms": res.get("duration_ms"), "duration_api_ms": res.get("duration_api_ms"),
           "cost_usd": cost, "usage": {k: u.get(k) for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")},
           "model_usage": res.get("modelUsage"), "tool_calls": len(tools), "tools": tools, "bash_calls": len(bash_cmds),
           "indo_calls": sum(1 for c in bash_cmds if re.search(r"(^|[\s;&|(])indo\s", c)),
           "indo_parallel_calls": sum(1 for c in bash_cmds if re.search(r"(^|[\s;&|(])indo\s.*(-P\s*\d|--parallel)", c)),
           "skill_invoked": any(t == "Skill" for t in tools), "skill_calls": skills_used, "tag": TAG, "skill_file": SKILL_FILE if arm == "C" else None, "bash_cmds": bash_cmds,
           "correct": ok, "partial": round(partial, 3), "detail": detail, "final_text": text[-1500:]}
    (RAW / f"{rid}.json").write_text(json.dumps(rec, indent=1))
    with LOCK:
        L = ledger(); L["spend_usd"] = round(L["spend_usd"] + cost, 6); L["runs"] += 1; json.dump(L, open(LEDGER, "w"))
    log(f"DONE {rid} slot={slot} ok={ok} partial={partial:.2f} cost=${cost:.4f} tools={len(tools)} indo={rec['indo_calls']} wall={wall:.0f}s turns={res.get('num_turns')} sub={res.get('subtype')} total=${ledger()['spend_usd']:.4f}")
    shutil.rmtree(cfg, ignore_errors=True)
    return rec
def main():
    sched = json.load(open(sys.argv[1])); nslots = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    q = queue.Queue()
    for j in sched:
        if not (RAW / f"{j['task']}_{j['arm']}_r{j['rep']}.json").exists(): q.put(j)
    stop = threading.Event()
    def worker(slot):
        while not stop.is_set():
            try: j = q.get_nowait()
            except queue.Empty: return
            with LOCK:
                if ledger()["spend_usd"] + PER_RUN_MAX * nslots > CAP:
                    log(f"STOP cap guard before {j}"); stop.set(); return
            try: rec = run_one(j, slot)
            except Exception as e: log(f"ERROR {j} {e!r}"); continue
            if rec["cost_usd"] == 0 and rec["rc"] != 0:
                log(f"ZERO-COST failure {rec['id']} rc={rec['rc']} – stopping (billing?)"); 
                os.remove(RAW / f"{rec['id']}.json"); stop.set(); return
    ts = [threading.Thread(target=worker, args=(f"s{i}",)) for i in range(nslots)]
    [t.start() for t in ts]; [t.join() for t in ts]
    log("RUNNER EXIT")
if __name__ == "__main__": main()
