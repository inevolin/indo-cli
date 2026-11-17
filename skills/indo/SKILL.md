---
name: indo
description: "The indo CLI is installed. It runs one command in every subfolder. Use it instead of a for loop whenever a command must run in 2 or more repos or folders. Slow commands (tests, builds, go vet, git fetch or pull): `indo -f -P 8 */ 'CMD'` runs them in parallel, up to about 2x faster, and prints only the failed folders plus a count line. Only some folders? Skip the others inside the command: `indo -f -P 8 */ '[ -f package.json ] || exit 0; npm test'`. Status or search: `indo -c */ 'git status -s'` prints one line per result, prefixed with the folder. Keep each indo command simple and combine the results afterwards. Read this skill for other flags."
---

# indo

`indo [flags] DIRS... [--] COMMAND` runs COMMAND inside each folder.

- `-P N` runs N folders at a time. Output stays grouped per folder, in order.
- `-f` shows only failed folders with their last lines, then `N/M ok, K failed: a b`.
- `-s` shows one `ok` or `FAIL` line per folder.
- `-c` prefixes each output line with the folder name and skips folders with no output. Good for status and search: `indo -c */ 'git status -s'`.
- `--tail N` sets the lines shown per failed folder (default 10).

Rules:
- Quote commands with pipes, `&&`, `>` or globs meant for inside each folder.
- Exit code is 1 if any folder failed. `grep` with no match is a failure, so add `|| true`.
- `@{u}` fails in a folder with no upstream branch. That folder shows as failed.
- For one folder, run the command directly.
