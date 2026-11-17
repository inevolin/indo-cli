#!/usr/bin/env python3
"""Ground truth from a fresh copy of the template, using git/jq-free Python + git plumbing (no indo)."""
import json, os, re, subprocess, sys, tarfile, shutil
from pathlib import Path
B = Path(os.environ.get("BENCH_DIR", "/tmp/indo-agent-bench")); W = B / "gt_ws"
def sh(c, cwd): return subprocess.run(c, cwd=cwd, shell=True, capture_output=True, text=True)
if W.exists(): shutil.rmtree(W)
W.mkdir(); subprocess.run(["tar", "xzf", str(B / "template.tgz"), "-C", str(W)], check=True)
R = W / "repos"
repos = sorted(p.name for p in R.iterdir() if p.is_dir())
for r in repos: sh(f"git remote set-url origin {W}/remotes/{r}.git", R / r)
gt = {}
gt["T01_dirty"] = [r for r in repos if sh("git status --porcelain", R / r).stdout.strip()]
gt["T04_branch"] = [r for r in repos if sh("git branch --show-current", R / r).stdout.strip() not in ("main", "master")]
gt["T05_ahead"] = [r for r in repos if int(sh("git rev-list --count @{u}..HEAD", R / r).stdout.strip() or 0) > 0]
for r in repos: sh("git fetch -q origin", R / r)
gt["T02_behind"] = [r for r in repos if int(sh("git rev-list --count HEAD..@{u}", R / r).stdout.strip() or 0) > 0]
def pj(r):
    p = R / r / "package.json"; return json.loads(p.read_text()) if p.exists() else None
def minver(s): m = re.search(r"(\d+)", s or ""); return int(m.group(1)) if m else None
gt["T06_node"] = [r for r in repos if pj(r) and minver((pj(r).get("engines") or {}).get("node")) is not None and minver(pj(r)["engines"]["node"]) < 20]
gt["T07_dep"] = [r for r in repos if pj(r) and any("tsd" in (pj(r).get(k) or {}) for k in ("dependencies", "devDependencies", "peerDependencies"))]
todo = {}
for r in repos:
    files = sh("git ls-files -z", R / r).stdout.split("\0")
    n = 0
    for f in files:
        p = R / r / f
        if f and p.is_file():
            try: n += sum(1 for line in p.read_text(errors="strict").splitlines() if "TODO" in line)
            except Exception: pass
    if n: todo[r] = n
gt["T08_todo"] = todo
gt["T09_license"] = [r for r in repos if not any(re.match(r"(licen[cs]e|copying)", f.name, re.I) for f in (R / r).iterdir() if f.is_file())]
gt["T10_touch"] = [r for r in repos if (R / r / "pyproject.toml").exists() or (R / r / "setup.py").exists()]
fails = []
for r in repos:
    p = subprocess.run("./ci.sh", cwd=R / r, shell=True, capture_output=True, text=True, timeout=600)
    if p.returncode != 0: fails.append(r)
gt["T03_tests"] = fails
json.dump({"repos": repos, "answers": gt}, open(B / "ground_truth.json", "w"), indent=1)
print(json.dumps(gt, indent=1)); shutil.rmtree(W)
