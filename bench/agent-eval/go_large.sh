#!/bin/bash
# Before: setup_large.sh, seed_large.sh, LARGE_DIR=... python3 gt_large.py, python3 mk_paired.py L1_tests,...,L8_dirty 3 54 sched/large.json
cd ${BENCH_DIR:-/tmp/indo-agent-bench}
MODEL=claude-sonnet-5-5 RUN_TAG=large SKILL_FILE=${SKILL_FILE:?set SKILL_FILE to skills/indo/SKILL.md} LEDGER=ledger_large.json CAP_USD=8 SETTING_SOURCES=user,project \
TEMPLATE=${LARGE_DIR:-/tmp/indo-large}/template.tgz GT_FILE=${LARGE_DIR:-/tmp/indo-large}/ground_truth.json python3 run.py sched/large.json 1
