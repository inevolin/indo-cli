#!/usr/bin/env bash
# Build the 20-repo benchmark workspace used by bench.py.
# Needs: git, node+npm, go, python3 with pytest, hypothesis and termcolor.
# Usage: ./setup_workspace.sh /path/to/bench   (creates src/, remotes/, bin/, refs.txt)
set -euo pipefail
B="${1:-/workspace/bench}"; HERE="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$B/src" "$B/remotes" "$B/bin"; cd "$B/src"
REPOS="sindresorhus/slugify sindresorhus/camelcase sindresorhus/escape-string-regexp sindresorhus/is-plain-obj
sindresorhus/p-limit sindresorhus/pretty-bytes google/uuid pkg/errors hashicorp/go-version Masterminds/semver
dustin/go-humanize more-itertools/more-itertools benjaminp/six kjd/idna hukkin/tomli pytoolz/toolz github/gitignore
sindresorhus/awesome-nodejs tldr-pages/tldr-python-client mathiasbynens/dotfiles"
for r in $REPOS; do git clone -q --depth 30 "https://github.com/$r" "$(basename "$r")" & done; wait
for d in slugify camelcase escape-string-regexp is-plain-obj p-limit pretty-bytes; do (cd "$d" && npm install --no-audit --no-fund --silent) & done; wait

# One uniform test entry point per repo (kept out of git status via .git/info/exclude)
for d in */; do d=${d%/}
  if [ -f "$d/package.json" ]; then grep -q '"ava"' "$d/package.json" && c='npx --no-install ava' || c='node --test'
  elif [ -f "$d/go.mod" ] || ls "$d"/*.go >/dev/null 2>&1; then c='[ -f go.mod ] || go mod init github.com/pkg/errors >/dev/null 2>&1; go test ./...'
  elif [ -f "$d/pyproject.toml" ] || [ -f "$d/setup.py" ]; then c='python3 -m pytest -q -p no:cacheprovider'
  else c='echo "no tests"'; fi
  printf '#!/usr/bin/env bash\n%s\n' "$c" > "$d/ci.sh"; chmod +x "$d/ci.sh"
  printf 'ci.sh\ngo.mod\ngo.sum\n' >> "$d/.git/info/exclude"
done
printf '#!/usr/bin/env bash\nPYTHONPATH=src python3 -m pytest -q -p no:cacheprovider\n' > tomli/ci.sh

# Failing tests: errors (go vet in new Go), toolz (no package metadata),
# tldr-python-client (missing dependency), slugify (bug added below)
sed -i "38s/'gv'), '')/'gv'), '_')/" slugify/index.js

# Local bare remotes so fetch/pull are fast and repeatable
cd "$B"
git config --global advice.detachedHead false
for d in src/*/; do n=$(basename "$d")
  git clone -q --bare --no-local "$d" "remotes/$n.git"
  (cd "$d" && git remote set-url origin "$B/remotes/$n.git" && git fetch -q origin && git branch -q -u "origin/$(git branch --show-current)")
done
for d in src/*/; do n=$(basename "$d"); git -C "$d" for-each-ref --format="$n %(refname) %(objectname)" refs/remotes; done > refs.txt
# Behind: 5 repos get 2 new upstream commits
for n in uuid six p-limit toolz gitignore; do rm -rf /tmp/up && git clone -q "remotes/$n.git" /tmp/up
  (cd /tmp/up && for k in 1 2; do echo "upstream change $k" >> UPSTREAM_NOTES.md; git add -A; git commit -qm "upstream change $k"; done; git push -q); done
# Ahead: 2 repos have a local unpushed commit
for n in camelcase go-version; do (cd "src/$n" && echo "local note" >> LOCAL_NOTES.md && git add -A && git commit -qm "local unpushed work"); done
# Dirty: 3 edited READMEs, 2 untracked files, plus the slugify bug
for n in pretty-bytes semver more-itertools; do (cd "src/$n" && echo "WIP edit" >> "$(git ls-files | grep -iE readme | head -1)"); done
echo scratch > src/idna/scratch.txt; mkdir -p src/dotfiles/tmp && echo x > src/dotfiles/tmp/notes.txt
# One repo on a feature branch
git -C src/go-humanize checkout -q -b feature/si-units

ln -sf "$HERE/in.sh" bin/indo
git -C "$HERE" show main:in.sh > bin/in-old && chmod +x bin/in-old
echo "Workspace ready in $B/src"
