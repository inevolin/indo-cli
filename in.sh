#!/usr/bin/env bash

################################################################################
# indo-cli (in.sh) - Execute commands on multiple targets (files or directories)
#
# Purpose:
#   A lightweight CLI tool that runs shell commands across multiple targets
#   simultaneously or in parallel. Supports glob patterns, comma-separated lists,
#   auto-creation of directories, and parallel execution.
#
# Usage:
#   indo [OPTIONS] [DIRECTORIES...] [--] COMMAND...
#
# Features:
#   - Flexible directory targeting (globs, comma lists, exact paths)
#   - Parallel execution with -P option
#   - Subshell isolation (doesn't change your current directory)
#   - Compatible with Bash 3.2+
#
# License: MIT
# Repository: https://github.com/inevolin/indo-cli
################################################################################

set -u  # Exit on undefined variables

version="1.2.0"

# Default settings
parallelism=1
dry_run=0
verbose=0
shell_mode=0
output_mode="human"   # human | compact | summary | fail-only
tail_lines=10
color_mode="auto"     # auto | always | never
[[ -n "${NO_COLOR:-}" ]] && color_mode="never"

cmd_name=$(basename "$0")
cmd_name="${cmd_name%.sh}"
# The old name "in" (and the in.sh file itself) shows the main name "indo".
[[ "$cmd_name" == "in" ]] && cmd_name="indo"

print_usage() {
    echo "Usage: $cmd_name [OPTIONS] [DIRECTORIES...] [--] COMMAND..."
    echo
    echo "Run a command in one or more directories."
    echo
    echo "Arguments:"
    echo "  DIRECTORIES   Glob patterns, comma-separated lists, or direct paths."
    echo "  COMMAND       The command to run in each directory."
    echo
    echo "Options:"
    echo "  -d, --dry            Dry run (print commands without executing)"
    echo "  -h, --help           Show this help message"
    echo "  -P, --parallel N     Run in parallel with N jobs (default: 1)"
    echo "  -v, --verbose        Show verbose output"
    echo "  -V, --version        Show the version"
    echo "      --color WHEN     auto (default), always or never. NO_COLOR=1 also works"
    echo "      --no-color       Same as --color never"
    echo
    echo "Short output (for scripts and AI agents):"
    echo "  -c, --compact        One line per output line, prefixed with the folder."
    echo "                       Folders with no output are skipped."
    echo "  -s, --summary        One line per folder: ok or FAIL. Failed folders"
    echo "                       also show their last lines of output."
    echo "  -f, --fail-only      Like --summary, but only show failed folders."
    echo "      --tail N         Lines of output to show per failed folder (default: 10)"
    echo
    echo "Exit code: 0 if the command worked in every folder, 1 if it failed in any."
    echo
    echo "Examples:"
    echo "  $cmd_name project* git status"
    echo "  $cmd_name frontend,backend npm install"
    echo "  $cmd_name -P 4 repos/* git pull"
    echo "  $cmd_name repos/* 'ls *.json'   (expand globs inside directory using quotes)"
    echo "  $cmd_name -c repos/* 'git status -s'   (only dirty repos, one line per file)"
    echo "  $cmd_name -f -P 8 packages/* 'npm test'   (only show what failed)"
}

################################################################################
# Option Parsing
# Only leading options are parsed. Everything after the first non-option
# belongs to the directories or the command, so "indo * grep --help" passes
# --help to grep untouched.
################################################################################

while [[ $# -gt 0 ]]; do
    case "$1" in
    -d|--dry) dry_run=1; shift ;;
    -h|--help) print_usage; exit 0 ;;
    -V|--version) echo "$cmd_name $version (indo-cli)"; exit 0 ;;
    -v|--verbose) verbose=1; shift ;;
    -c|--compact) output_mode="compact"; shift ;;
    -s|--summary) output_mode="summary"; shift ;;
    -f|--fail-only) output_mode="fail-only"; shift ;;
    --no-color) color_mode="never"; shift ;;
    --color=*) color_mode="${1#--color=}"; shift ;;
    --color)
        if [[ $# -lt 2 ]]; then echo "[error] --color needs a value" >&2; exit 2; fi
        color_mode="$2"; shift 2 ;;
    --tail=*) tail_lines="${1#--tail=}"; shift ;;
    --tail)
        if [[ $# -lt 2 ]]; then echo "[error] --tail needs a number" >&2; exit 2; fi
        tail_lines="$2"; shift 2 ;;
    -P|--parallel)
        if [[ $# -lt 2 ]]; then echo "[error] $1 needs a number" >&2; exit 2; fi
        parallelism="$2"; shift 2 ;;
    -P*) parallelism="${1#-P}"; shift ;;
    --parallel=*) parallelism="${1#--parallel=}"; shift ;;
    --) break ;;
    -?*)
        # Combined short flags such as -sv or -dP4 are not supported; be explicit.
        echo "[error] Unknown option: $1" >&2
        print_usage >&2
        exit 2 ;;
    *) break ;;
    esac
done

case "$color_mode" in auto|always|never) ;; *)
    echo "[error] --color must be auto, always or never" >&2; exit 2 ;; esac
if ! [[ "$parallelism" =~ ^[0-9]+$ ]] || [[ "$parallelism" -lt 1 ]]; then
    echo "[error] -P needs a positive number" >&2; exit 2
fi
if ! [[ "$tail_lines" =~ ^[0-9]+$ ]]; then
    echo "[error] --tail needs a number" >&2; exit 2
fi

# Colors: on for terminals, off for pipes, files and agents.
color_out=0; color_err=0
if [[ "$color_mode" == "always" ]]; then
    color_out=1; color_err=1
elif [[ "$color_mode" == "auto" ]]; then
    [[ -t 1 ]] && color_out=1
    [[ -t 2 ]] && color_err=1
fi
if [[ $color_out -eq 1 ]]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; BLUE='\033[0;34m'; YELLOW='\033[1;33m'; NC='\033[0m'
else
    RED=''; GREEN=''; BLUE=''; YELLOW=''; NC=''
fi
if [[ $color_err -eq 1 ]]; then
    eRED='\033[0;31m'; eYELLOW='\033[1;33m'; eGRAY='\033[1;30m'; eNC='\033[0m'
else
    eRED=''; eYELLOW=''; eGRAY=''; eNC=''
fi

log() {
    if [[ $verbose -eq 1 ]]; then
        echo -e "${eGRAY}[$cmd_name] $1${eNC}" >&2
    fi
}

error() {
    echo -e "${eRED}[error] $1${eNC}" >&2
}

warn() {
    echo -e "${eYELLOW}[warning] $1${eNC}" >&2
}

if [[ $# -eq 0 ]]; then
    print_usage
    exit 1
fi

################################################################################
# Argument Separation (Directories vs Command)
#
# Challenge: Distinguish between directory arguments and command arguments.
# Example: "in dir1 dir2 git pull" - where do dirs end and command begin?
#
# Solution: Two modes:
#   1. Explicit mode: Use "--" separator (e.g., "in dir1 dir2 -- git pull")
#   2. Implicit mode: Auto-detect based on heuristics:
#      - Existing directories
#      - Patterns containing commas (dir1,dir2)
#      - Glob characters (*, ?, [)
#      - First arg when --create is used (even if it doesn't exist)
################################################################################

raw_dirs=()
command_args=()
split_found=0

# Check for explicit separator "--"
args=("$@")
explicit_split_index=-1
for ((i=0; i<$#; i++)); do
    if [[ "${args[i]}" == "--" ]]; then
        explicit_split_index=$i
        break
    fi
done

if [[ $explicit_split_index -ge 0 ]]; then
    # Explicit mode: Everything before "--" is directories, after is command
    for ((i=0; i<$explicit_split_index; i++)); do
        raw_dirs+=("${args[i]}")
    done
    for ((i=$explicit_split_index+1; i<$#; i++)); do
        command_args+=("${args[i]}")
    done
else
    # Implicit mode: Use heuristics to detect where directories end
    parsing_dirs=1
    for arg in "$@"; do
        if [[ $parsing_dirs -eq 1 ]]; then
            is_dir_spec=0
            
            # Heuristic 1: Is it an existing file/directory OR a symlink?
            # We treat all existing paths as potential targets.
            # We also include broken symlinks (-L) to prevent them from being mistaken for commands.
            # Directories are kept; files/links are filtered out and warned about later.
            if [[ -e "$arg" || -L "$arg" ]]; then 
                is_dir_spec=1
            fi
            
            # Heuristic 2: Contains comma? (e.g., "dir1,dir2,dir3")
            if [[ "$arg" == *","* ]]; then
                is_dir_spec=1
            fi

            # Heuristic 3: Contains glob characters? (*, ?, [)
            # Handles quoted globs like "project*" that shell didn't expand
            if [[ "$arg" == *"*"* ]] || [[ "$arg" == *"?"* ]] || [[ "$arg" == *"["* ]]; then
                is_dir_spec=1
            fi

            # Heuristic 4: --create flag special case
            # Removed (feature removed)

            # Apply the verdict: Is this arg a target spec or start of command?
            if [[ $is_dir_spec -eq 1 ]]; then
                raw_dirs+=("$arg")
            else
                # First non-target arg marks start of command
                parsing_dirs=0
                command_args+=("$arg")
            fi
        else
            # Already in command mode, add all remaining args
            command_args+=("$arg")
        fi
    done
fi

# Heuristic Correction: 
# If we finished parsing and found NO command, but we have multiple "directories",
# check if the last "directory" is actually a command (e.g. it was a file, or a glob string).
if [[ ${#command_args[@]} -eq 0 ]] && [[ ${#raw_dirs[@]} -gt 1 ]]; then
    last_idx=$((${#raw_dirs[@]} - 1))
    potential_cmd="${raw_dirs[last_idx]}"
    
    # If the last argument is NOT a directory, assume it's the command
    # This catches:
    # 1. "ls *.txt" (matched glob heuristic, but isn't a dir)
    # 2. "script.sh" (matched exist heuristic, but isn't a dir)
    if [[ ! -d "$potential_cmd" ]]; then
        command_args+=("$potential_cmd")
        unset 'raw_dirs[last_idx]'
        raw_dirs=("${raw_dirs[@]}") # Re-index
    fi
fi

# Collision check: a folder whose name is also a command.
# Example: folders api/ git/ web/ and "in * git status". The shell expands * to
# "api git web", then "git" (typed by you) is an existing folder too, so it is
# read as a folder and "status" becomes the command. Warn so this is never silent.
if [[ $explicit_split_index -lt 0 && ${#raw_dirs[@]} -gt 0 && ${#command_args[@]} -gt 0 ]]; then
    last_dir="${raw_dirs[${#raw_dirs[@]}-1]}"
    if [[ -d "$last_dir" && "$last_dir" != *"/"* && "$last_dir" != *","* ]] \
        && command -v "$last_dir" >/dev/null 2>&1 \
        && ! command -v "${command_args[0]%% *}" >/dev/null 2>&1; then
        warn "'$last_dir' is both a folder and a command. It was read as a folder, so the command is '${command_args[*]}'. Use -- to be explicit: $cmd_name DIRS -- $last_dir ${command_args[*]}"
    fi
fi

# Validate we have both directories and a command
if [[ ${#raw_dirs[@]} -eq 0 ]]; then
    error "No target directories specified."
    exit 1
fi

if [[ ${#command_args[@]} -eq 0 ]]; then
    error "No command specified."
    exit 1
fi

# Auto-enable shell mode for single argument commands
if [[ ${#command_args[@]} -eq 1 ]]; then
    # We only auto-enable if not already verbose logging to avoid noise unless requested
    if [[ $verbose -eq 1 ]]; then
        # Check if log function is defined before calling, or just use echo
        # Using standard echo for consistency with other parts if log is internal
        log "Auto-enabling shell mode for single command string"
    fi
    shell_mode=1
fi

################################################################################
# Directory Resolution
# Expands comma-separated lists and glob patterns into actual directory paths.
# Example: "dir1,dir*" becomes ["dir1", "dir2", "dir3"] if those exist.
################################################################################
target_dirs=()

for raw in "${raw_dirs[@]}"; do
    # Step 1: Split comma-separated directory lists
    # Example: "dir1,dir2,dir3" → ["dir1", "dir2", "dir3"]
    IFS=',' read -ra PARTS <<< "$raw"
    
    for part in "${PARTS[@]}"; do
        # Step 2: Expand glob patterns
        # Note: If the shell already expanded globs (unquoted), we got separate args.
        # This handles quoted globs like "project*" or globs from comma splits like "dir1,proj*"
        
        if [[ "$part" == *"*"* ]] || [[ "$part" == *"?"* ]] || [[ "$part" == *"["* ]]; then
            # Contains wildcard characters - attempt glob expansion
            expanded=( $part )  # Let bash expand the pattern
            
            if [[ "${expanded[0]}" == "$part" && ! -e "$part" ]]; then
                # Expansion failed (no matches) and --create not set
                log "Pattern '$part' matched no files."
            else
                # Expansion succeeded
                for e in "${expanded[@]}"; do
                    # Add directories only
                    if [[ -d "$e" ]]; then
                        target_dirs+=("$e")
                    elif [[ -f "$e" ]]; then
                        warn "Ignoring file '$e' (only directories are supported)."
                    elif [[ -L "$e" ]]; then
                        warn "Ignoring broken symlink '$e'."
                    fi
                 done
             fi
        else
            # No wildcards - add as-is if directory or creating
            if [[ -d "$part" ]]; then
                target_dirs+=("$part")
            elif [[ -f "$part" ]]; then
                warn "Ignoring file '$part' (only directories are supported)."
            elif [[ -L "$part" ]]; then
                warn "Ignoring broken symlink '$part'."
            else
                 # If it doesn't exist...
                 target_dirs+=("$part")
            fi
        fi
    done
done

# Deduplicate targets while preserving order
# Example: ["dir1", "dir2", "dir1"] → ["dir1", "dir2"]
# Uses awk to track seen entries and only print first occurrence
if [[ ${#target_dirs[@]} -gt 0 ]]; then
    unique_dirs=()
    while IFS= read -r line; do
        unique_dirs+=("$line")
    done < <(printf "%s\n" "${target_dirs[@]}" | awk '!x[$0]++')
else
    unique_dirs=()
fi

if [[ ${#unique_dirs[@]} -eq 0 ]]; then
    error "No valid directories found."
    exit 1
fi

log "Target directories: ${unique_dirs[*]}"
log "Command: ${command_args[*]}"

################################################################################
# Command Execution
# Runs the specified command in each target directory using subshells.
#
# Human mode, one job:  output streams live, with a header per folder.
# Everything else:      output is captured per folder, then printed as one
#                       block per folder, in the order the folders were given.
#                       Parallel output never interleaves.
################################################################################

# Display name: drop trailing slashes from globs like */
display_name() {
    local n="$1"
    while [[ "$n" == */ && "$n" != "/" ]]; do n="${n%/}"; done
    printf '%s' "$n"
}

# Run the command in one folder. Prints the command output, returns its exit code.
exec_in_dir() {
    local target="$1"
    shift
    if [[ ! -d "$target" ]]; then
        echo "[error] Target directory not found: $target" >&2
        return 66
    fi
    (
        cd "$target" || exit 1
        if [[ $shell_mode -eq 1 ]]; then
            # Join args with spaces and execute via shell
            # This allows globs like "*.txt" to be expanded inside the directory
            eval "$*"
        else
            "$@"
        fi
    )
}

print_header() {
    echo -e "${YELLOW}in ${1} \$ ${NC}${command_args[*]}"
}

ok_count=0
fail_count=0
failed_names=()

record_result() {
    local name="$1" rc="$2"
    if [[ $rc -eq 0 ]]; then
        ok_count=$((ok_count + 1))
    else
        fail_count=$((fail_count + 1))
        failed_names+=("$name")
    fi
}

# Some tools force color even into pipes (for example pytest when FORCE_COLOR
# is set). When our own colors are off, strip color codes from captured output.
ESC_CHAR=$(printf '\033')
strip_ansi() {
    sed "s/${ESC_CHAR}\[[0-9;?]*[a-zA-Z]//g" "$1" > "$1.clean" && mv "$1.clean" "$1"
}

# Print the captured result of folder number $1
flush_result() {
    local i="$1"
    local d="${unique_dirs[i]}"
    local name rc out
    name=$(display_name "$d")
    rc=$(cat "$tmp_dir/$i.rc" 2>/dev/null || echo 1)
    out="$tmp_dir/$i.out"
    [[ $color_out -eq 0 && -s "$out" ]] && strip_ansi "$out"
    record_result "$name" "$rc"

    case "$output_mode" in
    human)
        print_header "$d"
        cat "$out"
        if [[ $rc -ne 0 ]]; then
            echo -e "${RED}✘ ${name}: exit ${rc}${NC}"
        fi
        ;;
    compact)
        # Skip folders with no output. Prefix each line with the folder.
        if [[ -s "$out" ]]; then
            awk -v p="${name}: " '{ print p $0 }' "$out"
        fi
        if [[ $rc -ne 0 ]]; then
            echo "${name}: FAIL (exit ${rc})"
        fi
        ;;
    summary|fail-only)
        if [[ $rc -eq 0 ]]; then
            if [[ "$output_mode" == "summary" ]]; then
                local last
                last=$(grep -v '^[[:space:]]*$' "$out" | tail -n 1 | cut -c1-160)
                if [[ -n "$last" ]]; then
                    echo -e "${GREEN}ok${NC}   ${name}: ${last}"
                else
                    echo -e "${GREEN}ok${NC}   ${name}"
                fi
            fi
        else
            echo -e "${RED}FAIL${NC} ${name} (exit ${rc})"
            if [[ $tail_lines -gt 0 ]]; then
                # Skip blank lines and JS/Python-style stack frame lines, keep the last N
                grep -v -E '^[[:space:]]*$|^[[:space:]]+at .*:[0-9]+:[0-9]+\)?( \{)?$' "$out" \
                    | tail -n "$tail_lines" | cut -c1-300 | sed 's/^/  /'
            fi
        fi
        ;;
    esac
}

# Run folder number $1 into capture files (used by captured modes)
capture_one() {
    local i="$1"
    local rc
    exec_in_dir "${unique_dirs[i]}" "${command_args[@]}" > "$tmp_dir/$i.out" 2>&1 < /dev/null
    rc=$?
    # Write rc last, atomically: its presence means "done"
    echo "$rc" > "$tmp_dir/$i.rc.tmp" && mv "$tmp_dir/$i.rc.tmp" "$tmp_dir/$i.rc"
    return "$rc"
}

n_dirs=${#unique_dirs[@]}

if [[ $dry_run -eq 1 ]]; then
    for d in "${unique_dirs[@]}"; do
        echo -e "${YELLOW}[DRY] in ${d} \$ ${NC}${command_args[*]}"
    done
    exit 0
fi

if [[ "$output_mode" == "human" && $parallelism -eq 1 ]]; then
    # Classic mode: stream output live (interactive commands keep working)
    for d in "${unique_dirs[@]}"; do
        print_header "$d"
        exec_in_dir "$d" "${command_args[@]}"
        rc=$?
        record_result "$(display_name "$d")" "$rc"
        if [[ $rc -ne 0 ]]; then
            echo -e "${RED}✘ $(display_name "$d"): exit ${rc}${NC}"
        fi
    done
else
    tmp_dir=$(mktemp -d 2>/dev/null || mktemp -d -t indo-cli)
    trap 'rm -rf "$tmp_dir"' EXIT
    trap 'rm -rf "$tmp_dir"; exit 130' INT TERM

    has_wait_n=0
    if [[ ${BASH_VERSINFO[0]} -gt 4 ]] || { [[ ${BASH_VERSINFO[0]} -eq 4 ]] && [[ ${BASH_VERSINFO[1]} -ge 3 ]]; }; then
        has_wait_n=1
    fi

    next_flush=0
    flush_ready() {
        while [[ $next_flush -lt $n_dirs && -f "$tmp_dir/$next_flush.rc" ]]; do
            flush_result "$next_flush"
            next_flush=$((next_flush + 1))
        done
    }

    pids=()
    active=0
    for ((i=0; i<n_dirs; i++)); do
        capture_one "$i" &
        pids[i]=$!
        active=$((active + 1))
        if [[ $active -ge $parallelism ]]; then
            if [[ $has_wait_n -eq 1 ]]; then
                wait -n 2>/dev/null
            else
                # Bash < 4.3: wait for the oldest unflushed job
                wait "${pids[next_flush]}" 2>/dev/null
            fi
            active=$((active - 1))
            flush_ready
        fi
    done
    for ((i=next_flush; i<n_dirs; i++)); do
        wait "${pids[i]}" 2>/dev/null
        flush_ready
    done
    flush_ready
fi

total=$((ok_count + fail_count))
if [[ "$output_mode" == "summary" || "$output_mode" == "fail-only" ]]; then
    if [[ $fail_count -eq 0 ]]; then
        echo "${ok_count}/${total} ok"
    else
        echo "${ok_count}/${total} ok, ${fail_count} failed: ${failed_names[*]}"
    fi
elif [[ $fail_count -gt 0 ]]; then
    msg="${fail_count} of ${total} folders failed: ${failed_names[*]}"
    if [[ "$output_mode" == "compact" ]]; then
        echo "$msg" >&2
    else
        echo -e "${eRED}✘ ${msg}${eNC}" >&2
    fi
fi

[[ $fail_count -eq 0 ]]
