#!/usr/bin/env bash
# Build the 50-repo workspace for the large agent eval. Records the exact commits in repos.lock.
# Usage: ./setup_large.sh /path/to/large   (creates build/src, build/remotes)
set -uo pipefail
L="${1:-/tmp/indo-large}"; mkdir -p "$L/build/src" "$L/build/remotes"; cd "$L/build/src"
JS="sindresorhus/slugify sindresorhus/camelcase sindresorhus/escape-string-regexp sindresorhus/is-plain-obj sindresorhus/p-limit
sindresorhus/pretty-bytes sindresorhus/strip-ansi sindresorhus/ansi-regex sindresorhus/string-width sindresorhus/decamelize
sindresorhus/filenamify sindresorhus/p-map sindresorhus/indent-string sindresorhus/dot-prop sindresorhus/quick-lru
sindresorhus/wrap-ansi sindresorhus/slash sindresorhus/map-obj"
GO="google/uuid pkg/errors hashicorp/go-version Masterminds/semver dustin/go-humanize google/go-cmp spf13/pflag kr/pretty
mattn/go-isatty rivo/uniseg gorilla/mux cespare/xxhash hashicorp/golang-lru davecgh/go-spew pmezard/go-difflib golang/groupcache"
PY="more-itertools/more-itertools benjaminp/six kjd/idna hukkin/tomli pytoolz/toolz tldr-pages/tldr-python-client
andialbrecht/sqlparse PyCQA/pyflakes PyCQA/pycodestyle PyCQA/mccabe asottile/tokenize-rt asottile/astpretty hukkin/tomli-w
tkem/cachetools jquast/wcwidth mahmoud/boltons pyparsing/pyparsing erikrose/parsimonious"
OTHER="github/gitignore sindresorhus/awesome-nodejs mathiasbynens/dotfiles"
for r in $JS $GO $PY $OTHER; do git clone -q --depth 1 "https://github.com/$r" "$(basename "$r")" & done; wait
for r in $JS; do d=$(basename "$r"); (cd "$d" && npm install --no-audit --no-fund --silent --ignore-scripts >/dev/null 2>&1) & done; wait
for d in */; do d=${d%/}
  if [ -f "$d/package.json" ]; then grep -q '"ava"' "$d/package.json" && c='npx --no-install ava' || c='node --test'
  elif [ -f "$d/go.mod" ] || git -C "$d" ls-files '*.go' | grep -q .; then c='[ -f go.mod ] || go mod init "example.com/$(basename "$PWD")" >/dev/null 2>&1; go test ./...'
  elif [ -f "$d/pyproject.toml" ] || [ -f "$d/setup.py" ] || [ -f "$d/setup.cfg" ]; then c='PYTHONPATH=src:. python3 -m pytest -q -p no:cacheprovider -x -q'
  else c='echo "no tests"'; fi
  printf '#!/usr/bin/env bash\n%s\n' "$c" > "$d/ci.sh"; chmod +x "$d/ci.sh"
  printf 'ci.sh\ngo.mod\ngo.sum\n' >> "$d/.git/info/exclude"
done
for d in */; do echo "$(basename "$d") $(git -C "$d" rev-parse HEAD) $(git -C "$d" config remote.origin.url)"; done > "$L/repos.lock"
echo "cloned $(ls -d */ | wc -l) repos"
