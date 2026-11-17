#!/usr/bin/env bash
# Seed the 50-repo workspace (after setup_large.sh): 3 committed test failures, local bare remotes,
# 6 repos behind, 3 ahead, 6 dirty, 2 on a feature branch. Then pack template.tgz.
set -euo pipefail
L="${1:-/tmp/indo-large}"; cd "$L/build/src"
c() { git -C "$1" add -A && git -C "$1" -c user.name=bench -c user.email=bench@example.com commit -qm "$2"; }
printf "\ntest('bench regression', t => {\n\tt.is(getProperty({a: 1}, 'a'), 2);\n});\n" >> dot-prop/test.js; c dot-prop "add a test"
printf 'package difflib\n\nimport "testing"\n\nfunc TestBenchRegression(t *testing.T) {\n\tif SplitLines("a\\nb")[0] != "b" {\n\t\tt.Fatal("bench regression")\n\t}\n}\n' > go-difflib/difflib/bench_test.go; c go-difflib "add a test"
printf 'import cachetools\n\n\ndef test_bench_regression():\n    assert cachetools.LRUCache(maxsize=1).maxsize == 2\n' > cachetools/tests/test_bench.py; c cachetools "add a test"
find . -name __pycache__ -type d -prune -exec rm -rf {} + ; find . -name .pytest_cache -prune -exec rm -rf {} + ; rm -rf more-itertools/.hypothesis
cd "$L/build"
for d in src/*/; do n=$(basename "$d")
  git clone -q --bare --no-local "$d" "remotes/$n.git"
  (cd "$d" && git remote set-url origin "$L/build/remotes/$n.git" && git fetch -q origin && git branch -q -u "origin/$(git branch --show-current)")
done
for n in uuid six p-limit toolz gitignore sqlparse; do rm -rf /tmp/up && git clone -q "remotes/$n.git" /tmp/up
  (cd /tmp/up && for k in 1 2; do echo "upstream change $k" >> UPSTREAM_NOTES.md; git add -A; git -c user.name=bench -c user.email=bench@example.com commit -qm "upstream change $k"; done; git push -q); done
for n in camelcase go-version boltons; do (cd "src/$n" && echo "local note" >> LOCAL_NOTES.md && c . "local unpushed work"); done
for n in pretty-bytes semver more-itertools pflag; do (cd "src/$n" && echo "WIP edit" >> "$(git ls-files | grep -iE '^readme' | head -1)"); done
echo scratch > src/idna/scratch.txt; mkdir -p src/dotfiles/tmp && echo x > src/dotfiles/tmp/notes.txt
git -C src/go-humanize checkout -q -b feature/si-units; git -C src/mux checkout -q -b feature/routes
mv src repos && tar czf "$L/template.tgz" repos remotes && echo "template ready: $L/template.tgz"
