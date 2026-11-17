# indo-cli: run one command in many folders

![Demo](.github/assets/demo.gif)

```bash
indo * git status            # in every folder
indo -P 8 repos/* git pull   # 8 at a time
indo -f * 'npm test'         # show only what failed
```

- **One short command.** No `for` loops, no `find -exec`, no `xargs` quoting.
- **Honest exit codes.** 0 only if the command worked in every folder.
- **Made for AI agents too.** Short output modes cut test output by 94% on 20 real repos ([benchmark](#benchmark)).
- **Zero dependencies.** One Bash script. Bash 3.2+.

> **Why `indo` and not `in`?** `in` is a reserved word in Bash, so `in * ls` is a syntax error there (and in `bash -c`, which AI agents use). The installer adds `indo`, plus an `in` link that works in zsh.

## Install

```bash
curl -sL https://raw.githubusercontent.com/inevolin/indo-cli/main/install.sh | bash
```

No sudo? Install to your home folder:

```bash
curl -sL https://raw.githubusercontent.com/inevolin/indo-cli/main/install.sh | DEST_DIR=~/.local/bin bash
```

Want another name? Pass it: `... | bash -s -- mycmd`. Then only that name is installed.

> **Renamed from in-cli.** This project used to be called in-cli (github.com/inevolin/in-cli). Old links redirect here. Old installs keep working, and running the installer again updates them and keeps the `in` link. Version 1.2.0 is the first release under the new name.

## Rules of thumb

1. **Quote the command** if it has `&&`, `||`, `;`, `|`, `>` or a `*` meant for inside the folder: `indo * 'ls *.json'`.
2. **Use `--`** when a folder has the same name as a command: `indo * -- git status`.
3. **Use `-f`** for tests and builds. You see only the failed folders and one count line.
4. **Use `-c`** for status and search. One line per result, empty folders skipped.
5. **Add `|| true` to searches.** `grep` exits 1 when it finds nothing, and `indo` counts that as a failure.

## Usage

```bash
indo [OPTIONS] [DIRECTORIES...] [--] COMMAND...
```

| Flag | What it does |
|------|-------------|
| `-P`, `--parallel N` | Run N folders at a time. Output stays grouped per folder, in order. |
| `-c`, `--compact` | Prefix each output line with the folder. Skip folders with no output. |
| `-s`, `--summary` | One line per folder: `ok` or `FAIL`. Failed folders show their last lines. |
| `-f`, `--fail-only` | Like `-s`, but only failed folders. |
| `--tail N` | Lines to show per failed folder (default 10). |
| `--color WHEN` | `auto` (default), `always` or `never`. `--no-color` and `NO_COLOR=1` also work. |
| `-d`, `--dry` | Print the commands, run nothing. |
| `-v`, `--verbose` | Debug logs. |
| `-V`, `--version` | Show the version. |
| `-h`, `--help` | Show help. |

**Exit code:** 0 if the command worked in every folder. 1 if it failed in any folder. The last line says how many failed and where.

### Examples

See [EXAMPLES.md](EXAMPLES.md) for 50+ real-world examples.

```bash
# Git
indo -c * 'git status -s'                 # only dirty repos, one line per file
indo -P 8 repos/* git pull
indo -c * git branch --show-current

# Packages and builds
indo frontend,backend yarn build
indo -f -P 4 packages/* 'pnpm test'

# Chaining (quote it)
indo packages/* "pnpm update && git commit -am 'update' && git push"

# Preview first
indo -d packages/* "rm -rf node_modules"

# Shell features inside each folder
indo src/* "ls -l | grep .ts"
indo ./* "wc -l *.json > stats.txt"
```

### Wildcards

Your shell expands `*.txt` **before** `indo` runs, in your current folder.

- ❌ `indo projects/* ls *.txt` expands `*.txt` here, not inside each project.
- ✅ `indo projects/* "ls *.txt"` quotes it, so it expands inside each folder.

### Output for scripts and AI agents

On a terminal you get colors and live output. In a pipe, a file or an agent's shell, colors are off. With `-c`, `-s` and `-f`, output is captured per folder and printed as one clean block:

```text
$ indo -f --tail 3 -P 8 errors six toolz uuid ./ci.sh
FAIL errors (exit 1)
  ./errors_test.go:220:31: non-constant format string in call to github.com/pkg/errors.WithMessagef
  FAIL	github.com/pkg/errors [build failed]
  FAIL
FAIL toolz (exit 1)
  SKIPPED [1] toolz/tests/test_functoolz.py:737: annotationlib is new in Python 3.14
  FAILED toolz/tests/test_package.py::test_has_version - importlib.metadata.Pac...
  1 failed, 191 passed, 1 skipped in 0.27s
2/4 ok, 2 failed: errors toolz
```

## Benchmark

We ran 7 everyday tasks on 20 real open source repos (JavaScript, Go, Python) with real test suites, some failing tests and some dirty repos. Every command ran through `bash -c`, the way AI agents run commands. Full report: [ANALYSIS.md](ANALYSIS.md).

![Benchmark](.github/assets/benchmark.png)

| Task (20 repos) | Plain loop | Old `in` | Expert shell | **`indo` short output** |
|---|---|---|---|---|
| Which repos are dirty? | 875 tok | 1,095 tok | 44 tok, 121 chars | **48 tok, 25 chars** |
| Fetch all. Which are behind? | 1,126 tok | 681 tok | 221 tok, 118 chars | **221 tok, 57 chars** |
| Run tests. Which failed? | 8,014 tok ✗ | 8,254 tok ✗ | 418 tok, 120 chars | **460 tok, 17 chars** |
| Same, 8 jobs in parallel | 10,433 tok ✗ | 8,270 tok ✗ | 418 tok, 106 chars | **460 tok, 22 chars** |
| Who is not on main? | 154 tok | 411 tok | 111 tok, 73 chars | **111 tok, 35 chars** |

`tok` = output tokens (tiktoken cl100k_base). ✗ = wrong answer or wrong exit code.

**Where plain tools win:** for one search, `rg` or `grep '"x"' */package.json` is shorter. An expert loop uses about 6% fewer tokens, but is 2 to 7 times longer to type. GNU parallel with `-k --tag` is just as correct, but harder to remember.

## Why not find or xargs?

Running `git status` in every subfolder:

```bash
find . -mindepth 1 -maxdepth 1 -type d -exec git -C {} status \;   # no folder names, exit code always 0
ls -d */ | xargs -I {} sh -c 'cd {} && git status'                 # no folder names
indo * git status                                                   # names, grouped, honest exit code
```

## Changelog

- **1.2.0** Renamed the project from in-cli to indo-cli. `indo` is the main command. The `in` link still works.
- **1.1.0** Short output modes (`-c`, `-s`, `-f`), honest exit codes, `--version`, and `indo` as the default install name.

## Uninstall

```bash
sudo rm -f "$(command -v indo)" "$(dirname "$(command -v indo)")/in"
```

## Testing

```bash
./tests.sh
```

## Requirements

- Bash 3.2 or newer
- Linux, macOS, BSD, or Windows (WSL, Git Bash, Cygwin)
- No other dependencies

## Contributing

Pull requests are welcome.

## License

MIT. See [LICENSE](LICENSE).
