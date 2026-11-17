#!/bin/bash
# usage: go.sh MODEL TAG SCHEDULE SLOTS [SKILL_FILE]
cd "${BENCH_DIR:-/tmp/indo-agent-bench}"
MODEL=$1 RUN_TAG=$2 SKILL_FILE=${5:-} LEDGER=ledger_skill.json CAP_USD=10 SETTING_SOURCES=user,project python3 run.py $3 $4
