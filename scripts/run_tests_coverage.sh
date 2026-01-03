#!/usr/bin/env bash
# run_tests_coverage.sh
#
# カバレッジ付きテスト実行スクリプト（時間がかかります）

set -e

cd "$(dirname "$0")/.."

# 仮想環境を有効化（venv を優先）
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

echo "=== カバレッジ付きテスト実行 ==="
echo "⚠️  時間がかかります..."
echo ""

# オプション: 特定のテストファイルやディレクトリを指定
TEST_PATH="${1:-tests}"

# pytest をカバレッジ付きで実行
pytest \
    "$TEST_PATH" \
    -v \
    --tb=short \
    --cov=src \
    --cov-report=term-missing \
    --cov-report=html \
    "$@"

echo ""
echo "✅ テスト完了"
echo "📊 カバレッジレポート: htmlcov/index.html"

