#!/usr/bin/env python3
"""Ground truth for the compound (H*), dev (D*), held-out (O*) and single-repo (N*) tasks. Run after ground_truth.py."""
import os, json, re, subprocess, shutil
from pathlib import Path
B = Path(os.environ.get("BENCH_DIR", "/tmp/indo-agent-bench")); W = B / "gt_extra"
if W.exists(): shutil.rmtree(W)
W.mkdir(); subprocess.run(["tar", "xzf", str(B / "template.tgz"), "-C", str(W)], check=True)
R = W / "repos"; repos = sorted(p.name for p in R.iterdir() if p.is_dir())
run = lambda c, r: subprocess.run(c, cwd=R / r, shell=True, capture_output=True, text=True)
sh = lambda c, r: run(c, r).stdout.strip()
for r in repos: sh(f"git remote set-url origin {W}/remotes/{r}.git", r)
heads = {r: sh("git rev-parse HEAD", r) for r in repos}
status = {r: sh("git status --porcelain", r) for r in repos}
readme_mod = sorted(r for r, s in status.items() if s and any(l.split()[0] == "M" and "readme" in l.split()[-1].lower() for l in s.splitlines()))
gor = [r for r in repos if (R / r / "go.mod").exists() or list((R / r).glob("*.go"))]
jsr = [r for r in repos if (R / r / "package.json").exists()]
pyr = [r for r in repos if (R / r / "pyproject.toml").exists() or (R / r / "setup.py").exists()]
vet = [r for r in gor if run("go vet ./...", r).returncode]
js = [r for r in jsr if run("./ci.sh", r).returncode]
py = [r for r in pyr if run("./ci.sh", r).returncode]
toolz_passed = re.search(r"(\d+) passed", run("./ci.sh", "toolz").stdout).group(1)
for r in repos: sh("git fetch -q origin", r)
ab, noup = {}, []
for r in repos:
    o = sh("git rev-list --left-right --count HEAD...@{u}", r).split()
    if not o: noup.append(r); continue
    if int(o[0]) or int(o[1]): ab[r] = f"{o[0]}/{o[1]}"
behind = sorted(r for r in ab if ab[r].split("/")[1] != "0")
ups = {r: sh("git rev-parse @{u}", r) for r in repos if r not in noup}
fails = []
for r in behind:
    sh("git merge -q --ff-only @{u}", r)
    if run("./ci.sh", r).returncode: fails.append(r)
gt = json.load(open(B / "ground_truth.json"))
t3, dirty = set(gt["answers"]["T03_tests"]), set(gt["answers"]["T01_dirty"])
gt["answers"].update({"H1_pull_test": sorted(fails), "H2_fail_dirty": sorted(t3 & dirty), "H3_ahead_behind": ab, "H4_commit_readme": readme_mod,
                      "D_govet": vet, "O_jstests": js, "O_pytests": py, "N_branch": sh("git branch --show-current", "go-humanize"), "N_toolz": toolz_passed})
gt.update({"H1_behind": behind, "template_heads": heads, "template_status": status, "upstream_heads": ups, "no_upstream": noup})
json.dump(gt, open(B / "ground_truth.json", "w"), indent=1); shutil.rmtree(W); print(json.dumps(gt["answers"], indent=1))
