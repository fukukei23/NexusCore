#!/bin/bash
# WSL環境でテストを実行するシェルスクリプト
# 使用方法: bash dev_tools/run_tests.sh [テストターゲット]

set -e

PROJECT_ROOT="/home/yn441611/NexusCore"
TEST_TARGET="${1:-tests/}"

cd "$PROJECT_ROOT"

echo "Activating virtual environment: myenv_linux"
source myenv_linux/bin/activate

echo "Running pytest on: $TEST_TARGET"
echo "----------------------------------------"

python -m pytest "$TEST_TARGET" -v

echo "----------------------------------------"
echo "✅ Test execution complete"

