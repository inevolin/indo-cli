#!/bin/bash
# tests/test_agent_mode.sh - exit codes, colors, grouped parallel output,
# short output modes (--compact, --summary, --fail-only), --version,
# folder/command collision warning and running under "bash -c".

if [[ -f "./in.sh" ]]; then
    IN_TOOL="$(pwd)/in.sh"
elif [[ -f "../in.sh" ]]; then
    IN_TOOL="$(cd .. && pwd)/in.sh"
else
    echo "Error: Could not find in.sh"; exit 1
fi

TEST_DIR="$(pwd)/tmp_agent_test"
FAILED=0
pass() { echo "[PASS] $1"; }
fail() { echo "[FAIL] $1"; FAILED=$((FAILED + 1)); }
check() { if eval "$2"; then pass "$1"; else fail "$1"; echo "  output was: ${out:-}"; fi; }

rm -rf "$TEST_DIR"; mkdir -p "$TEST_DIR"; cd "$TEST_DIR" || exit 1
mkdir -p a b c empty
echo "ok" > a/status; echo "ok" > b/status; echo "bad" > c/status
ESC=$(printf '\033')

# --- exit codes ---
out=$("$IN_TOOL" a b 'true' 2>&1); rc=$?
check "exit 0 when every folder works" '[[ $rc -eq 0 ]]'
out=$("$IN_TOOL" a b c 'grep -q ok status' 2>&1); rc=$?
check "exit 1 when one folder fails" '[[ $rc -eq 1 ]]'
check "failure count is reported" '[[ "$out" == *"1 of 3 folders failed: c"* ]]'
out=$("$IN_TOOL" -P 3 a b c 'grep -q ok status' 2>&1); rc=$?
check "exit 1 when one folder fails in parallel" '[[ $rc -eq 1 && "$out" == *"1 of 3 folders failed: c"* ]]'
out=$("$IN_TOOL" a,missing_dir 'true' 2>&1); rc=$?
check "missing folder counts as a failure" '[[ $rc -eq 1 && "$out" == *"not found"* ]]'
out=$("$IN_TOOL" -d a c 'false' 2>&1); rc=$?
check "dry run exits 0" '[[ $rc -eq 0 && "$out" == *"[DRY]"* ]]'

# --- colors ---
out=$("$IN_TOOL" a b c 'cat status' 2>&1)
check "no color codes when output is not a terminal" '[[ "$out" != *"$ESC"* ]]'
out=$("$IN_TOOL" --color always a 'cat status' 2>&1)
check "--color always forces color" '[[ "$out" == *"$ESC"* ]]'
out=$("$IN_TOOL" --color=always --no-color a 'cat status' 2>&1)
check "--no-color wins when given last" '[[ "$out" != *"$ESC"* ]]'
out=$(NO_COLOR=1 "$IN_TOOL" --color=auto a 'cat status' 2>&1)
check "NO_COLOR is respected" '[[ "$out" != *"$ESC"* ]]'
out=$("$IN_TOOL" --color=sometimes a 'true' 2>&1); rc=$?
check "bad --color value is an error" '[[ $rc -eq 2 ]]'

out=$("$IN_TOOL" -c a 'printf "\033[31mred\033[0m\n"' 2>&1)
check "captured output has forced colors removed when color is off" '[[ "$out" == "a: red" ]]'
out=$("$IN_TOOL" -c --color always a 'printf "\033[31mred\033[0m\n"' 2>&1)
check "forced colors are kept with --color always" '[[ "$out" == *"$ESC"* ]]'

# --- version ---
out=$("$IN_TOOL" --version); rc=$?
check "--version prints a version" '[[ $rc -eq 0 && "$out" =~ [0-9]+\.[0-9]+\.[0-9]+ ]]'
out=$("$IN_TOOL" -V)
check "-V prints a version" '[[ "$out" =~ [0-9]+\.[0-9]+\.[0-9]+ ]]'

# --- options after the command belong to the command ---
out=$("$IN_TOOL" a grep --help 2>&1)
check "--help after the command goes to the command" '[[ "$out" == *"PATTERNS"* || "$out" == *"grep"* ]] && [[ "$out" != *"Run a command in one or more directories"* ]]'

# --- grouped parallel output ---
out=$("$IN_TOOL" -P 3 a b c 'echo start-$(basename $PWD); sleep 0.$((RANDOM % 4)); echo end-$(basename $PWD)' 2>&1)
expected="in a \$ echo start-\$(basename \$PWD); sleep 0.\$((RANDOM % 4)); echo end-\$(basename \$PWD)
start-a
end-a"
check "parallel output is grouped per folder" '[[ "$out" == "$expected"* ]]'
order=$(echo "$out" | grep -E '^(start|end)-' | tr '\n' ' ')
check "parallel output keeps folder order" '[[ "$order" == "start-a end-a start-b end-b start-c end-c " ]]'

# --- compact mode ---
out=$("$IN_TOOL" -c a b c empty 'cat status 2>/dev/null; true' 2>&1)
check "compact prefixes each line with the folder" '[[ "$out" == "a: ok"$'"'"'\n'"'"'"b: ok"$'"'"'\n'"'"'"c: bad" ]]'
out=$("$IN_TOOL" -c a empty 'grep -h ok status 2>/dev/null; true' 2>&1)
check "compact skips folders with no output" '[[ "$out" == "a: ok" ]]'
out=$("$IN_TOOL" -c a c 'grep -q ok status' 2>&1); rc=$?
check "compact reports failures and exit code" '[[ $rc -eq 1 && "$out" == *"c: FAIL (exit 1)"* ]]'
printf 'no newline' > a/nonl
out=$("$IN_TOOL" -c a b 'cat nonl 2>/dev/null; echo' 2>&1)
check "compact handles output without final newline" '[[ "$out" == "a: no newline"$'"'"'\n'"'"'"b: " ]]'

# --- summary / fail-only ---
out=$("$IN_TOOL" -s a b c 'cat status; grep -q ok status' 2>&1); rc=$?
check "summary: one ok line per working folder" '[[ "$out" == *"ok   a: ok"* && "$out" == *"ok   b: ok"* ]]'
check "summary: failed folder shows FAIL and its output" '[[ "$out" == *"FAIL c (exit 1)"*"  bad"* ]]'
check "summary: final count line" '[[ "$out" == *"2/3 ok, 1 failed: c" && $rc -eq 1 ]]'
out=$("$IN_TOOL" -f -P 2 a b c 'cat status; grep -q ok status' 2>&1); rc=$?
check "fail-only hides working folders" '[[ "$out" != *"ok   a"* && "$out" == *"FAIL c"* && $rc -eq 1 ]]'
out=$("$IN_TOOL" -f a b 'true' 2>&1); rc=$?
check "fail-only prints one line when all work" '[[ "$out" == "2/2 ok" && $rc -eq 0 ]]'
out=$("$IN_TOOL" --summary --tail 2 c 'seq 1 9; false' 2>&1)
check "--tail limits failure output" '[[ "$out" == *"  8"*"  9"* && "$out" != *"  7"* ]]'
out=$("$IN_TOOL" --summary --tail 0 c 'seq 1 9; false' 2>&1)
check "--tail 0 shows no failure output" '[[ "$out" == "FAIL c (exit 1)"$'"'"'\n'"'"'"0/1 ok, 1 failed: c" ]]'
out=$("$IN_TOOL" -f --tail 2 c 'echo "AssertionError: boom"; echo "    at run (node:internal/x:1:2)"; echo "    at Foo.bar (/a/b.js:10:5)"; false' 2>&1)
check "stack frame lines are skipped in failure output" '[[ "$out" == *"AssertionError: boom"* && "$out" != *"node:internal"* ]]'
out=$("$IN_TOOL" -s a/ 'echo hi' 2>&1)
check "trailing slash is dropped from folder names" '[[ "$out" == *"ok   a: hi"* ]]'

# --- folder/command collision ---
mkdir -p coll/git coll/api
out=$(cd coll && "$IN_TOOL" * git status 2>&1)
check "warns when a folder name is also a command" '[[ "$out" == *"both a folder and a command"* ]]'
out=$(cd coll && "$IN_TOOL" api,git -- git --version 2>&1)
check "no warning when -- is used" '[[ "$out" != *"both a folder and a command"* ]]'
out=$(cd coll && "$IN_TOOL" api git pwd 2>&1)
check "no warning when the command is valid" '[[ "$out" != *"both a folder and a command"* ]]'

# --- bash -c (how AI agents run commands) ---
mkdir -p bin; ln -sf "$IN_TOOL" bin/indo
out=$(PATH="$TEST_DIR/bin:$PATH" bash -c 'indo -s a b "cat status"' 2>&1); rc=$?
check "indo works under bash -c" '[[ $rc -eq 0 && "$out" == *"2/2 ok"* ]]'
out=$(PATH="$TEST_DIR/bin:$PATH" bash -c 'indo --help' 2>&1)
check "help shows the name it was called with" '[[ "$out" == "Usage: indo"* ]]'

# --- option validation ---
out=$("$IN_TOOL" -P x a true 2>&1); rc=$?
check "-P needs a number" '[[ $rc -eq 2 ]]'
out=$("$IN_TOOL" --bogus a true 2>&1); rc=$?
check "unknown option is an error" '[[ $rc -eq 2 && "$out" == *"Unknown option"* ]]'
out=$("$IN_TOOL" -P2 a b 'true' 2>&1); rc=$?
check "-P2 (no space) works" '[[ $rc -eq 0 ]]'

cd ..; rm -rf "$TEST_DIR"
if [[ $FAILED -eq 0 ]]; then echo "All agent mode tests passed."; exit 0; fi
echo "$FAILED agent mode tests failed."; exit 1
