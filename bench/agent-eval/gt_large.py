#!/usr/bin/env python3
"""Ground truth for the 54-repo tasks (L*)."""
import os, json, subprocess, shutil
from pathlib import Path
L = Path(os.environ.get("LARGE_DIR", "/tmp/indo-large")); W = L / "gt_ws"
if W.exists(): shutil.rmtree(W)
W.mkdir(); subprocess.run(["tar", "xzf", str(L / "template.tgz"), "-C", str(W)], check=True)
R = W / "repos"; repos = sorted(p.name for p in R.iterdir() if p.is_dir())
run = lambda c, r: subprocess.run(c, cwd=R / r, shell=True, capture_output=True, text=True)
sh = lambda c, r: run(c, r).stdout.strip()
for r in repos: sh(f"git remote set-url origin {W}/remotes/{r}.git", r)
heads = {r: sh("git rev-parse HEAD", r) for r in repos}
status = {r: sh("git status --porcelain", r) for r in repos}
dirty = [r for r in repos if status[r]]
fail = [r for r in repos if run("timeout 300 ./ci.sh", r).returncode]
fail2 = [r for r in repos if run("timeout 300 ./ci.sh", r).returncode]
assert fail == fail2, (fail, fail2)
js = [r for r in repos if (R / r / "package.json").exists()]
go = [r for r in repos if sh("git ls-files \"*.go\"", r)]
py = [r for r in repos if any((R / r / f).exists() for f in ("pyproject.toml", "setup.py", "setup.cfg"))]
for r in repos: sh("git fetch -q origin", r)
behind = [r for r in repos if sh("git rev-list --count HEAD..@{u}", r) not in ("", "0")]
ups = {r: sh("git rev-parse @{u}", r) for r in repos if sh("git rev-parse @{u}", r)}
failb = sorted(set(fail) & set(behind))
pulled_fail = []
for r in behind:
    sh("git merge -q --ff-only @{u}", r)
    if run("timeout 300 ./ci.sh", r).returncode: pulled_fail.append(r)
ans = {"L1_tests": fail, "L2_jstests": sorted(set(fail) & set(js)), "L3_gotests": sorted(set(fail) & set(go)), "L4_pytests": sorted(set(fail) & set(py)),
       "L5_behind": behind, "L6_pull_test": pulled_fail, "L7_fail_behind": failb, "L8_dirty": dirty}
out = {"repos": repos, "answers": ans, "H1_behind": behind, "template_heads": heads, "template_status": status, "upstream_heads": ups, "groups": {"js": js, "go": go, "py": py}}
json.dump(out, open(L / "ground_truth.json", "w"), indent=1); shutil.rmtree(W); print(json.dumps(ans, indent=1), len(repos), "go:", go, "py:", py)
