#!/usr/bin/env bash
# Build the agent eval workspace: the 20-repo bench plus 2 removed license files, packed as template.tgz.
# Usage: BENCH_DIR=/tmp/indo-agent-bench ./prepare.sh
set -euo pipefail
B="${BENCH_DIR:-/tmp/indo-agent-bench}"; HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$B"; cp "$HERE/../../in.sh" "$B/indo.sh"; cp "$HERE"/*.py "$HERE/go.sh" "$B/"
bash "$HERE/../setup_workspace.sh" "$B/build"
cd "$B/build/src"
(cd tomli && git rm -q LICENSE LICENSE-HEADER && git commit -qm "remove license file" && git push -q origin HEAD)
(cd escape-string-regexp && git rm -q license && git commit -qm "remove license file" && git push -q origin HEAD)
find . -name __pycache__ -type d -prune -exec rm -rf {} + ; find . -name .pytest_cache -prune -exec rm -rf {} +
cd "$B/build" && rm -rf bin refs.txt && mv src repos && tar czf "$B/template.tgz" repos remotes
echo "Now run: cd $B && python3 ground_truth.py"
