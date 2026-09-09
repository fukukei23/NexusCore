#!/usr/bin/env bash
# run_harness_task.py のテストに対する手動mutation check（automation-health方式）
# 使い方: bash scripts/test_mutation_run_harness.sh
# 各変異を投入→テスト実行→git restoreで戻す。KILLED=テストが捕捉/SURVIVED=テスト弱点
set -u
cd "$(dirname "$0")/.." || exit 1
FILE="scripts/run_harness_task.py"
TESTS="tests/harness/test_run_harness_wrapper.py"

declare -a NAMES=() RESULTS=()
check() { # $1=名前 $2=sed式
  python3 - "$2" <<'PY'
import re, sys
patch = sys.argv[1].replace("\\n", "\n")
p = "scripts/run_harness_task.py"
s = open(p).read()
old, new = patch.split("|||")
assert old in s, f"MUTATION TARGET NOT FOUND: {old[:60]}"
open(p, "w").write(s.replace(old, new, 1))
PY
  if [ $? -ne 0 ]; then RESULTS+=("TARGET_NOT_FOUND"); NAMES+=("$1"); git checkout -- "$FILE"; return; fi
  PYTHONPATH=src .venv/bin/python -m pytest "$TESTS" -q >/dev/null 2>&1
  rc=$?
  if [ $rc -ne 0 ]; then RESULTS+=("KILLED"); else RESULTS+=("SURVIVED"); fi
  NAMES+=("$1")
  git checkout -- "$FILE"
}

# M1-M9: critical挙動への意図的変異
check "M1 stamp_eligible hard_time_limit無効化" \
  'if any(w.startswith("hard_time_limit") for w in warnings):|||if False:'
check "M2 stamp_eligible harness_exit無効化" \
  'if any(w.startswith("harness_exit") for w in warnings):|||if False:'
check "M3 stamp_eligible abort_reason無視" \
  'if final.get("abort_reason") is not None:\n        return False|||if False:\n        return False'
check "M4 check_daily_stamp 常時True(同日skip無効化)" \
  'try:\n        return sp.read_text().strip() != today_jst()|||return True'
check "M5 mark_done [x]化せずTrue返却" \
  'lines[idx] = lines[idx].replace("- [ ]", "- [x]", 1)|||pass'
check "M6 watchdog 常時ok" \
  'if len(recent) >= 10 and uniq < WATCHDOG_STOP_UNIQUE:|||if False:'
check "M7 normalize 何もしない" \
  'return re.sub(r"[\s\W_]+", "", t, flags=re.UNICODE)|||return t'
check "M8 task_hash 定数化" \
  'return hashlib.sha256(normalize(text).encode()).hexdigest()[:16]|||return "deadbeef"'
check "M9 pick_topic 均等化無視" \
  'least = [t for t in open_topics if done_cats.get(t["category"], 0) == min_done]|||least = open_topics'
check "M10 budget_mode 短冊優先無効化(先頭固定)" \
  'return min(open_topics, key=lambda t: len(t["text"])), "budget_mode_shortest"|||return open_topics[0], "budget_mode_shortest"'

echo ""
echo "===== mutation check 結果 ====="
killed=0; survived=0
for i in "${!NAMES[@]}"; do
  echo "${RESULTS[$i]}: ${NAMES[$i]}"
  if [ "${RESULTS[$i]}" = "KILLED" ]; then killed=$((killed+1)); else survived=$((survived+1)); fi
done
echo "-----"
echo "KILLED=$killed SURVIVED=$survived"
[ $survived -eq 0 ]
