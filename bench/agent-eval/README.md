# Agent eval: does indo help a real coding agent?

We gave Claude Code the same multi-repo tasks with and without indo and measured the results. This page explains how, and shows every number. Raw per-run metrics are in [results/runs.csv](results/runs.csv). The per-task chart in the repository README is drawn from these files by [render_readme_charts.py](render_readme_charts.py).

## Short answer

- **54 repos: 1.8x faster on test tasks.** Claude Code with indo and the skill finished slow multi-repo tasks 1.82x faster (95% CI 1.44x to 2.30x). A full test run went from 53.0 s to 16.1 s. Same answers, same cost. See [Round 3](#round-3-54-repos-paired-runs).

- **Correct answers: tied.** Every arm got the same score on every model.
- **Speed: faster with indo, on slow commands.** With the indo Agent Skill, Claude Code (Sonnet 5.5) finished held-out multi-repo test and pull tasks in 22% to 32% less time. A full test run across 20 repos went from 26.9 s to 13.0 s with the prompt note, and from 27.6 s to 12.6 s with the skill (dev runs).
- **Cost: about the same with the skill.** The always-on prompt note cost 6% to 30% more per run. The skill costs about the same as plain bash once the prompt cache is warm.
- **Plain bash agents almost never ran anything in parallel.** In 172 plain bash runs, the agent ran folders in parallel only twice, both times for `git fetch` on the 54-repo workspace. It never ran tests in parallel.
- **The weaker model did not get faster.** Haiku 5.5 used indo in less than half of the runs and saved no time.

## Setup

- **Agent:** Claude Code 2.1.325, `claude -p`, a fresh config folder per run, no MCP servers, no web tools, no subagents.
- **Models:** Sonnet 5.5 (main) and Haiku 5.5 (cheap check). The same model in every arm.
- **Workspace:** the 20 real repos from [../setup_workspace.sh](../setup_workspace.sh) (JavaScript, Go, Python) with local bare remotes. 5 repos are behind, 2 are ahead, 6 are dirty, 1 is on a feature branch, 4 have failing tests, 2 have no license file. Every run starts from the same packed copy ([prepare.sh](prepare.sh)).
- **Arms:**
  - **A, plain bash.** indo is not installed.
  - **B, note.** indo is on PATH and a 585-token note with `indo --help` is added to the system prompt of every request.
  - **C, skill.** indo is on PATH and the [indo Agent Skill](../../skills/indo/SKILL.md) is installed in the agent's skills folder. No note.
- **Order:** random. Up to 3 runs at the same time on one 8-core Linux box.
- **Grading:** a script compares the final `ANSWER:` line with the true answer, computed by [ground_truth.py](ground_truth.py) and [ground_truth_extra.py](ground_truth_extra.py). Tasks that change files are also checked on disk (right commits, nothing else changed).
- **Cost:** from Claude Code's own usage report at list prices. We checked it against the token counts and the public price list.

## Tasks

All prompts are in [tasks.py](tasks.py). "Parallel tasks" are the slow ones where running folders at the same time can help.

| Task | What the agent must do | Parallel task |
|---|---|---|
| T01 to T10 | Dirty repos, behind after fetch, failing tests, branch, unpushed commits, old Node, a dependency, TODO counts, missing license, create a file in Python repos | T03 only |
| H1 | Fetch, fast-forward the repos that are behind, test only those | yes |
| H2 | Repos that fail tests and are also dirty | yes |
| H3 | Ahead and behind counts after fetch | no |
| H4 | Commit only the README edits | no |
| D_govet | `go vet` in every Go repo | yes |
| O_jstests | Tests in every JavaScript repo | yes |
| O_pytests | Tests in every Python repo | yes |
| N_branch, N_toolz | One repo only. indo should not be used. | no |

## Round 1: note vs plain bash (168 runs)

14 tasks (T01 to T10, H1 to H4), 3 runs per task and arm.

| | Sonnet 5.5 plain | Sonnet 5.5 note | Haiku 5.5 plain | Haiku 5.5 note |
|---|---|---|---|---|
| Correct | 42/42 | 42/42 | 41/42 | 41/42 |
| Cost per run vs plain | | 1.06x (95% CI 0.95 to 1.17) | | 1.13x (1.02 to 1.24) |
| Test run across 20 repos (T03) | 26.9 s | 13.0 s | 29.6 s | 15.9 s |
| Runs that used indo | | 41/42 | | 30/42 |

The extra cost was almost all the note itself: 585 more prompt tokens on every request. Details: [results/round1-table.md](results/round1-table.md), [results/round1-summary.json](results/round1-summary.json).

## Round 2: tuning the skill

Each version ran on the dev tasks (T03, D_govet, H2, T02, N_branch), 2 runs each, Sonnet 5.5. Plain bash on the same tasks: 10/10 correct, 21.0 s mean on the parallel tasks, indo never used. The text of every version is in [skill-versions/](skill-versions/).

| Version | Change | Correct | Multi-repo runs that used indo | Used `-P` | Skill body loaded | Mean time, parallel tasks | Mean cost (USD) |
|---|---|---|---|---|---|---|---|
| v1 | Plain description: what indo is and when to use it | 10/10 | 1/8 | 1 | 1 | 20.1 s | 0.0182 |
| v2 | Description starts with "indo is installed" and shows `indo -f -P 8 */ CMD` | 10/10 | 8/8 | 8 | 8 | 12.4 s | 0.0209 |
| v3 | Shorter body, description says the command is enough for most tasks | 10/10 | 8/8 | 8 | 0 | 15.5 s | 0.0186 |
| v4 | Adds the `-c` status example and "keep each command simple" | 10/10 | 6/8 | 6 | 0 | 11.2 s | 0.0221 |
| v5 | Adds "only some folders? skip the others inside the command" | 10/10 | 8/8 | 8 | 0 | 10.5 s | 0.0223 |
| v6 | v5 with the description quoted, so strict YAML parsers accept it, and "up to about 2x" | final, see below | | | | | |

The single-repo control (N_branch) never used indo in any version. Costs in this table include cache warm-up noise, because each version has a new prompt prefix.

What we learned: the description does the work. Once it shows the exact command, Claude Code uses indo without opening the skill. That saves a turn.

## Held-out results

New tasks the skill was not tuned on: O_jstests, O_pytests, H1, H3, T01, N_toolz. 3 runs per task and arm.

**Final skill (v6), Sonnet 5.5, plain bash vs skill (36 runs):**

| Task | Plain: correct, time, cost (USD) | Skill: correct, time, cost (USD) | Skill runs using indo / with -P |
|---|---|---|---|
| O_jstests | 3/3, 10.2 s, 0.0175 | 3/3, 8.9 s, 0.0252 | 3 / 3 |
| O_pytests | 3/3, 20.9 s, 0.0179 | 3/3, 15.5 s, 0.0272 | 3 / 3 |
| H1 pull then test | 3/3, 16.1 s, 0.0274 | 3/3, 12.5 s, 0.0244 | 1 / 1 |
| H3 ahead/behind | 3/3, 5.4 s, 0.0201 | 3/3, 5.1 s, 0.0203 | 3 / 3 |
| T01 dirty | 3/3, 3.4 s, 0.0166 | 3/3, 4.0 s, 0.0174 | 3 / 0 |
| N_toolz (one repo) | 3/3, 5.0 s, 0.0182 | 3/3, 5.0 s, 0.0182 | 0 / 0 |

- Parallel tasks: 15.7 s to 12.3 s, ratio 0.78 (95% CI 0.70 to 0.89).
- All tasks: 10.2 s to 8.5 s, ratio 0.84 (0.77 to 0.92).
- Cost, all tasks: 1.13x as charged (0.99 to 1.29). The first 2 skill runs paid a one-time cache write of the new prompt (about 0.02 USD each). Without those 2 runs the cost ratio is 1.00x (0.98x on the parallel tasks).
- The skill body was never loaded. The description was enough.

**Skill v5, Sonnet 5.5, plain bash vs note vs skill (54 runs):**

| Parallel tasks (O_jstests, O_pytests, H1) | Plain | Note | Skill |
|---|---|---|---|
| Correct | 9/9 | 9/9 | 9/9 |
| Mean time | 16.0 s | 12.5 s | 10.9 s |
| Time vs plain | | 0.78 (0.69 to 0.87) | 0.68 (0.60 to 0.76) |
| Cost vs plain | | 1.30x (1.09 to 1.66) | 1.02x (0.98 to 1.06) |
| Runs that used indo / with -P | 0 / 0 | 9 / 7 | 8 / 8 |

All 6 held-out tasks: 18/18 correct in every arm. Skill vs note cost: 0.90x.

**Skill v5, Haiku 5.5, plain bash vs skill (36 runs):** 18/18 correct in both. Parallel tasks 16.8 s vs 16.5 s (0.98, 0.89 to 1.08). Cost 1.11x (1.05 to 1.18) on parallel tasks. Haiku used indo in 8 of 18 runs. The skill does not help this model yet.

## Round 3: 54 repos, paired runs

A bigger, slower workspace: 54 real repos (18 JavaScript, 16 Go, 18 Python, 3 without tests), pinned in [results/large-repos.lock](results/large-repos.lock). A full sequential test run takes about 45 s. 11 repos fail their tests: 8 for real reasons and 3 with a failing test we committed. 6 repos are behind, 3 ahead, 6 dirty, 2 on a feature branch. Scripts: [setup_large.sh](setup_large.sh), [seed_large.sh](seed_large.sh), [gt_large.py](gt_large.py).

- **Agent:** Claude Code 2.1.325 with Sonnet 5.5.
- **Arms:** A, plain bash. C, indo plus the final skill (v6) in the agent's skills folder.
- **Design:** 8 new tasks, 3 repeats. Each repeat is a pair: A and C on the same task, back to back, in random order. One run at a time, so the arms never compete for the CPU.
- **Cursor agent CLI:** not run. It installed, but it needs a Cursor login or `CURSOR_API_KEY`, and the box has neither. Codex and Gemini CLI were not run either, because there were no credentials.

| Task (54 repos) | Plain: correct, median time | indo + skill: correct, median time | Median speedup | Runs using indo / with -P |
|---|---|---|---|---|
| L1 run all tests, which fail? | 3/3, 53.0 s | 3/3, 16.1 s | 3.3x | 3 / 3 |
| L2 JavaScript tests | 3/3, 24.0 s | 3/3, 13.5 s | 1.8x | 3 / 3 |
| L3 Go tests | 3/3, 6.9 s | 3/3, 5.6 s | 1.2x | 3 / 3 |
| L4 Python tests | 3/3, 31.7 s | 3/3, 14.8 s | 2.1x | 3 / 3 |
| L5 fetch, which are behind? | 3/3, 5.0 s | 3/3, 4.5 s | 1.1x | 3 / 3 |
| L6 pull the behind repos, then test them | 3/3, 14.8 s | 3/3, 14.0 s | 1.1x | 3 / 3 |
| L7 failing tests and behind | 3/3, 55.4 s | 3/3, 16.8 s | 3.3x | 3 / 3 |
| L8 dirty repos | 3/3, 4.2 s | 3/3, 5.0 s | 0.8x | 3 / 0 |

Pooled over pairs (geometric mean of the per-pair ratios, 95% bootstrap CI):

| | Pairs | Speedup with indo | Cost with indo |
|---|---|---|---|
| Slow tasks (L1, L2, L3, L4, L6, L7) | 17 | **1.82x (1.44x to 2.30x)** | 1.02x (0.93 to 1.09) |
| All 8 tasks | 23 | 1.53x (1.24x to 1.90x) | 1.02x (0.95 to 1.07) |

- **Correct answers: 24/24 in both arms.**
- **One outlier is left out of the pooled numbers.** One plain bash Go run (L3, repeat 3) took 355 s with the same command that took 7 s in the other repeats. If we keep it, the slow-task speedup is 2.25x (1.54x to 3.77x). Per-task medians are not affected much.
- **Plain bash ran folders in parallel in 2 of 24 runs.** Both were `git fetch` loops with `&` and `wait`. It never ran tests in parallel. On the 20-repo workspace it was 0 of 148 runs.
- **Where indo did not help:** quick commands. `git status` (L8) was a bit slower with indo, and pull then test (L6) touched only 6 repos.
- **Spend:** 0.99 USD for these 48 runs.

Numbers: [results/large-stats.json](results/large-stats.json), [results/large-sensitivity.json](results/large-sensitivity.json). Headline numbers for all rounds: [results/summary.json](results/summary.json).

## Limits

- Small samples: 3 runs per task and arm, 6 held-out tasks, one 20-repo workspace, one machine.
- One agent (Claude Code). Cursor agent CLI, Codex and Gemini CLI were not tested, because there were no logins or API keys for them.
- Speed depends on the machine and on how slow each folder's command is. Fast commands (git status) gain nothing. Test suites gain the most.
- Up to 3 runs shared the 8 cores, so times are noisy. Both arms ran mixed together in random order.
- Cost depends on the prompt cache. Every new prompt prefix pays one cache write.
- Claude Code accepted v5's unquoted description, but strict YAML parsers did not. v6 quotes it and changes "about 2x" to "up to about 2x". We confirmed v6 on the held-out tasks.

## Run it yourself

```bash
export BENCH_DIR=/tmp/indo-agent-bench ANTHROPIC_KEY_FILE=~/.anthropic_key   # a file with your API key
./prepare.sh && cd "$BENCH_DIR" && python3 ground_truth.py && python3 ground_truth_extra.py
python3 mk_sched.py O_jstests,O_pytests,H1_pull_test,H3_ahead_behind,T01_dirty,N_toolz AC 3 9 final.json
./go.sh claude-sonnet-5-5 final final.json 2 /path/to/indo-cli/skills/indo/SKILL.md
python3 heldout_stats.py claude-sonnet-5-5 AC final
```

Needs Claude Code, git, node and npm, go, and python3 with pytest, hypothesis and termcolor. The Round 2 eval cost about 3.2 USD in API credit at list prices.
