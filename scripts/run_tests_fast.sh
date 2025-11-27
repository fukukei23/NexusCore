#!/usr/bin/env bash
# run_tests_fast.sh
#
# 高速なテスト実行スクリプト（カバレッジなし、並列実行）

set -e

cd "$(dirname "$0")/.."

# 仮想環境を有効化
if [ -d "myenv_linux" ]; then
    source myenv_linux/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "=== 高速テスト実行（カバレッジなし） ==="
echo ""

# オプション: 特定のテストファイルやディレクトリを指定
TEST_PATH="${1:-tests}"

# pytest を高速モードで実行
pytest \
    "$TEST_PATH" \
    -v \
    --tb=short \
    -n auto \
    --no-cov \
    --disable-warnings \
    "$@"

echo ""
echo "✅ テスト完了"

