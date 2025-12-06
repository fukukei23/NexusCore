#!/usr/bin/env bash
# run_tests_with_report.sh
#
# テストを実行し、結果レポートを自動生成するスクリプト
#
# 使用方法: bash dev_tools/run_tests_with_report.sh [テストターゲット]

set -e

PROJECT_ROOT="/home/yn441611/NexusCore"
TEST_TARGET="${1:-tests/}"

cd "$PROJECT_ROOT"

echo "=== テスト実行（結果レポート自動生成） ==="
echo ""

# 仮想環境を有効化（venv を優先）
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# 結果ディレクトリの準備
RESULTS_DIR="${PROJECT_ROOT}/test_results"
mkdir -p "$RESULTS_DIR"

# 一時ファイルの準備
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_FILE="${RESULTS_DIR}/pytest_output_${TIMESTAMP}.txt"

echo "🧪 テストターゲット: $TEST_TARGET"
echo "📁 結果出力先: $RESULTS_DIR"
echo ""

# pytest を実行して標準出力を保存
echo "Running pytest..."
echo "----------------------------------------"

if python -m pytest "$TEST_TARGET" -v --tb=short 2>&1 | tee "$OUTPUT_FILE"; then
    PYTEST_EXIT_CODE=0
else
    PYTEST_EXIT_CODE=$?
fi

echo "----------------------------------------"
echo ""

# 結果レポートを生成
echo "📊 テスト結果レポートを生成中..."
if python -m dev_tools.test_result_generator "$OUTPUT_FILE" "$TEST_TARGET" "$RESULTS_DIR"; then
    REPORT_EXIT_CODE=0
else
    REPORT_EXIT_CODE=$?
    echo "⚠️  レポート生成に失敗しました（テスト結果は正常に取得できています）"
fi

# 生成されたレポートファイルを探す
LATEST_REPORT=$(ls -t "${RESULTS_DIR}/TEST_RESULT_${TIMESTAMP}"*.md 2>/dev/null | head -1)

if [ -n "$LATEST_REPORT" ]; then
    echo ""
    echo "✅ テスト結果レポート: $LATEST_REPORT"
    echo ""
    echo "📄 レポートの最初の50行を表示:"
    echo "----------------------------------------"
    head -50 "$LATEST_REPORT"
    echo "----------------------------------------"
    echo ""
    echo "💡 完全なレポートを確認するには:"
    echo "   cat $LATEST_REPORT"
fi

# 一時ファイルを削除
rm -f "$OUTPUT_FILE"

# pytest の終了コードを返す（レポート生成の成否は無視）
exit $PYTEST_EXIT_CODE

