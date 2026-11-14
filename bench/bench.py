#!/usr/bin/env python3
"""Benchmark in-cli against default tools on a 20-repo workspace.

Every command runs through `bash -c` with no terminal, the way AI agents run
commands. Tokens are counted with tiktoken cl100k_base on stdout+stderr.
"""
import json, os, re, statistics, subprocess, sys, time
import tiktoken

WS = os.environ.get("BENCH_WS", "/workspace/bench/src")
BIN = os.environ.get("BENCH_BIN", "/workspace/bench/bin")
REFS = os.environ.get("BENCH_REFS", "/workspace/bench/refs.txt")
RUNS = int(os.environ.get("BENCH_RUNS", "3"))
ENC = tiktoken.get_encoding("cl100k_base")
tok = lambda s: len(ENC.encode(s, disallowed_special=()))

REPOS = sorted(d for d in os.listdir(WS) if os.path.isdir(os.path.join(WS, d)))
ENV = dict(os.environ, PATH=f"{BIN}:{os.path.expanduser('~/.local/bin')}:/usr/local/go/bin:/usr/local/bin:/usr/bin:/bin",
           HOME=os.environ.get("HOME", "/tmp"), GIT_PAGER="cat", PAGER="cat", TERM="dumb")
for k in ("NO_COLOR", "FORCE_COLOR", "PY_COLORS", "CLICOLOR_FORCE"):
    ENV.pop(k, None)

TRUTH = {
    "dirty": {"dotfiles", "idna", "more-itertools", "pretty-bytes", "semver", "slugify"},
    "behind": {"uuid", "six", "p-limit", "toolz", "gitignore"},
    "failing": {"errors", "slugify", "tldr-python-client", "toolz"},
    "old_ava": {"escape-string-regexp"},
    "off_main": {"go-humanize"},
}

names = "|".join(re.escape(r) for r in sorted(REPOS, key=len, reverse=True))
HEADER = [  # lines that start a new repo segment
    re.compile(rf"^(?:\x1b\[[0-9;]*m)*(?:== |in |\[|### |\./)?(?P<n>{names})/?(?:\]|:?$| \$)"),
    re.compile(rf"^(?:\x1b\[[0-9;]*m)*(?:FAIL|ok|✘)\s+(?P<n>{names})\b"),
]
PREFIX = re.compile(rf"^(?:\./|src/)?(?P<n>{names})(?:/|:|\t)")
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def segments(out):
    """Assign every output line to a repo, as a careful reader would."""
    seg, cur = {}, None
    for line in out.splitlines():
        hit = None
        for h in HEADER:
            m = h.match(line)
            if m:
                hit = m.group("n"); break
        if hit:
            cur = hit
            seg.setdefault(cur, []).append(line)
            continue
        m = PREFIX.match(line)
        if m:
            seg.setdefault(m.group("n"), []).append(line)
        elif cur:
            seg[cur].append(line)
    return seg


def flagged(out, pred):
    return {r for r, lines in segments(out).items() if pred("\n".join(lines))}

DIRTY = re.compile(r"^(?:.*?: |.*?\t|  )?(?:\s?M|\?\?|A |D |MM) \S|Changes not staged|Untracked files|modified:", re.M)
BEHIND = re.compile(r"behind")
FAILRE = re.compile(r"\bFAIL\b|\bERROR\b|✖|\d+ failed|exit [1-9]|not ok|Error:")
OLD_AVA = re.compile(r'"ava":\s*"\^?[0-5]\.')
OFF_MAIN = re.compile(r"feature/")

TODO_TRUTH = None


def check(task, out, rc):
    o = ANSI.sub("", out)
    if task == "T1":
        got = flagged(o, DIRTY.search); return got == TRUTH["dirty"], rc == 0, got
    if task == "T2":
        got = flagged(o, BEHIND.search); return got == TRUTH["behind"], rc == 0, got
    if task in ("T3", "T4"):
        got = flagged(o, FAILRE.search); return got == TRUTH["failing"], rc != 0, got
    if task == "T5":
        is_hit = lambda l: "TODO" in l and "grep -n" not in l and not l.startswith("$ ")
        lines = [l for l in o.splitlines() if is_hit(l)]
        got = {r for r, ls in segments(o).items() if any(is_hit(l) for l in ls)}
        ok = got == set(TODO_TRUTH) and len(lines) == sum(TODO_TRUTH.values())
        return ok, rc == 0, f"{len(lines)} TODO lines in {len(got)} repos"
    if task == "T6":
        got = flagged(o, OLD_AVA.search); return got == TRUTH["old_ava"], rc == 0, got
    if task == "T7":
        got = flagged(o, OFF_MAIN.search); return got == TRUTH["off_main"], rc == 0, got


def reset_fetch():
    for line in open(REFS):
        repo, ref, sha = line.split()
        if ref.endswith("/HEAD"):
            continue
        subprocess.run(["git", "-C", os.path.join(WS, repo), "update-ref", ref, sha], check=True)

GREP_AVA = r'''grep "\"ava\"" package.json'''
TASKS = [
 ("T1", "Which repos have uncommitted changes?", None, [
  ("old in-cli", "human", "in-old * git status"),
  ("new in-cli", "human", "indo * git status"),
  ("new in-cli", "agent", "indo -c * 'git status -s'"),
  ("naive loop", "default", 'for d in */; do echo "== $d"; (cd "$d" && git status); done'),
  ("expert loop", "default", 'rc=0; for d in */; do s=$(git -C "$d" status -s) || rc=1; [ -n "$s" ] && printf \'%s:\\n%s\\n\' "${d%/}" "$s"; done; exit $rc'),
  ("find -execdir (README)", "default", "find . -maxdepth 1 -type d -not -name '.' -execdir git status \\;"),
  ("xargs -P", "default", "ls -d */ | xargs -P 8 -I{} sh -c 'git -C {} status -s | sed \"s|^|{}: |\"'"),
  ("GNU parallel", "default", "parallel -k --tag 'git -C {} status -s' ::: */"),
 ]),
 ("T2", "Fetch every repo. Which are behind?", reset_fetch, [
  ("old in-cli", "human", "in-old * 'git fetch -q && git status -sb | head -1'"),
  ("new in-cli", "human", "indo * 'git fetch -q && git status -sb | head -1'"),
  ("new in-cli", "agent", "indo -c -P 8 * 'git fetch -q && git status -sb | head -1'"),
  ("naive loop", "default", 'for d in */; do echo "== $d"; (cd "$d" && git fetch && git status); done'),
  ("expert loop", "default", 'rc=0; for d in */; do git -C "$d" fetch -q || rc=1; echo "${d%/}: $(git -C "$d" status -sb | head -1)"; done; exit $rc'),
  ("xargs -P", "default", "ls -d */ | xargs -P 8 -I{} sh -c 'git -C {} fetch -q && echo \"{}: $(git -C {} status -sb | head -1)\"'"),
  ("GNU parallel", "default", "parallel -j8 -k --tag 'git -C {} fetch -q && git -C {} status -sb | head -1' ::: */"),
 ]),
 ("T3", "Run tests everywhere. Which failed?", None, [
  ("old in-cli", "human", "in-old * ./ci.sh"),
  ("new in-cli", "human", "indo * ./ci.sh"),
  ("new in-cli", "agent", "indo -f * ./ci.sh"),
  ("naive loop", "default", 'for d in */; do echo "== $d"; (cd "$d" && ./ci.sh); done'),
  ("expert loop", "default", 'f=0; for d in */; do o=$(cd "$d" && ./ci.sh 2>&1) || { f=1; echo "FAIL ${d%/}"; echo "$o" | tail -n 10; }; done; exit $f'),
  ("find -exec", "default", "find . -mindepth 1 -maxdepth 1 -type d -exec sh -c 'cd \"$1\" && ./ci.sh' _ {} \\;"),
 ]),
 ("T4", "Run tests in parallel (8 jobs). Which failed?", None, [
  ("old in-cli", "human", "in-old -P 8 * ./ci.sh"),
  ("new in-cli", "human", "indo -P 8 * ./ci.sh"),
  ("new in-cli", "agent", "indo -f -P 8 * ./ci.sh"),
  ("xargs -P", "default", "ls -d */ | xargs -P 8 -I{} sh -c 'cd {} && ./ci.sh 2>&1 | sed \"s|^|{}: |\"'"),
  ("expert xargs -P", "default", "printf '%s\\n' */ | xargs -P 8 -I{} sh -c 'o=$(cd {} && ./ci.sh 2>&1) || { printf \"FAIL %s\\n%s\\n\" {} \"$(echo \"$o\" | tail -n 10)\"; exit 1; }'"),
  ("GNU parallel", "default", "parallel -j8 -k --tag 'cd {} && ./ci.sh' ::: */"),
  ("expert GNU parallel", "default", "parallel -j8 -k 'o=$(cd {} && ./ci.sh 2>&1) || { echo \"FAIL {}\"; echo \"$o\" | tail -n 10; exit 1; }' ::: */"),
 ]),
 ("T5", "Find every TODO in the code", None, [
  ("old in-cli", "human", "in-old * 'git grep -n TODO'"),
  ("new in-cli", "human", "indo * 'git grep -n TODO'"),
  ("new in-cli", "agent", "indo -c * 'git grep -n TODO || true'"),
  ("naive grep -r", "default", "grep -rn TODO */"),
  ("expert grep -r", "default", "grep -rn --exclude-dir={node_modules,.git} TODO */"),
  ("ripgrep", "specialised", "rg -n TODO"),
  ("ripgrep --hidden", "specialised", "rg -n --hidden -g '!.git' TODO"),
 ]),
 ("T6", "Which JS repos still use ava older than v6?", None, [
  ("old in-cli", "human", f"in-old * '{GREP_AVA}'"),
  ("new in-cli", "human", f"indo * '{GREP_AVA}'"),
  ("new in-cli", "agent (no || true)", f"indo -c * '{GREP_AVA}'"),
  ("new in-cli", "agent", f"indo -c * '{GREP_AVA} 2>/dev/null || true'"),
  ("naive loop", "default", 'for d in */; do echo "== $d"; grep \'"ava"\' "$d/package.json"; done'),
  ("grep with glob", "specialised", "grep '\"ava\"' */package.json"),
 ]),
 ("T7", "Which repos are not on main or master?", None, [
  ("old in-cli", "human", "in-old * git branch --show-current"),
  ("new in-cli", "human", "indo * git branch --show-current"),
  ("new in-cli", "agent", "indo -c * git branch --show-current"),
  ("naive loop", "default", 'for d in */; do echo "== $d"; (cd "$d" && git branch); done'),
  ("expert loop", "default", 'for d in */; do echo "${d%/}: $(git -C "$d" branch --show-current)"; done'),
  ("find -exec", "default", "find . -mindepth 1 -maxdepth 1 -type d -exec git -C {} branch --show-current \\;"),
  ("GNU parallel", "default", "parallel -k --tag git -C {} branch --show-current ::: */"),
 ]),
]

SLOW = {"T3", "T4"}


def run(cmd):
    t = time.perf_counter()
    p = subprocess.run(["bash", "-c", cmd], cwd=WS, env=ENV, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return p.stdout + p.stderr, p.returncode, time.perf_counter() - t


def main():
    global TODO_TRUTH
    only = set(sys.argv[1:])
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
    os.makedirs(out_dir, exist_ok=True)
    # Truth for T5: TODO lines in tracked files (git grep), per repo
    TODO_TRUTH = {}
    for r in REPOS:
        p = subprocess.run(["git", "-C", os.path.join(WS, r), "grep", "-c", "TODO"], capture_output=True, text=True)
        n = sum(int(l.rsplit(":", 1)[1]) for l in p.stdout.splitlines())
        if n:
            TODO_TRUTH[r] = n
    results = []
    # bash -c check for the bare name "in"
    for sh in ("bash", "sh"):
        p = subprocess.run([sh, "-c", "in * pwd"], cwd=WS, env=dict(ENV, PATH=f"{BIN}:{ENV['PATH']}"), capture_output=True, text=True)
        results.append({"task": "T0", "question": f"Does `in * pwd` run under `{sh} -c`?", "tool": "in (any version)", "mode": "-",
                        "cmd": "in * pwd", "rc": p.returncode, "out_tokens": tok(p.stdout + p.stderr),
                        "output_head": (p.stdout + p.stderr)[:200]})
    for tid, q, prep, methods in TASKS:
        if only and tid not in only:
            continue
        for tool, mode, cmd in methods:
            times = []
            n = 1 if tid in SLOW else RUNS
            for _ in range(n):
                if prep: prep()
                out, rc, dt = run(cmd)
                times.append(dt)
            ok, rc_ok, got = check(tid, out, rc)
            slug = f"{tid}-{tool}-{mode}".replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "").replace("|", "")
            open(os.path.join(out_dir, slug + ".txt"), "w").write(f"$ {cmd}\n# exit {rc}\n{out}")
            r = {"task": tid, "question": q, "tool": tool, "mode": mode, "cmd": cmd, "cmd_chars": len(cmd),
                 "out_tokens": tok(out), "out_lines": out.count("\n"), "ansi_codes": len(ANSI.findall(out)),
                 "rc": rc, "answer_right": ok, "exit_code_right": rc_ok, "found": sorted(got) if isinstance(got, set) else got,
                 "seconds": round(statistics.median(times), 2), "runs": n}
            results.append(r)
            print(json.dumps(r), flush=True)
    if prep_needed := any(t[2] for t in TASKS):
        reset_fetch()
    name = "results.json" if not only else f"results-{'-'.join(sorted(only))}.json"
    json.dump(results, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), name), "w"), indent=1)

if __name__ == "__main__":
    main()
