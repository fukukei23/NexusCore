#!/bin/bash
# WSL環境でテストを実行するシェルスクリプト
# 使用方法: bash dev_tools/run_tests.sh [テストターゲット] [--no-report]

set -e

PROJECT_ROOT="/home/yn441611/NexusCore"
TEST_TARGET="${1:-tests/}"
GENERATE_REPORT=true

# --no-report オプションのチェック
if [ "$2" = "--no-report" ] || [ "$1" = "--no-report" ]; then
    GENERATE_REPORT=false
    # --no-report が最初の引数の場合は、TEST_TARGET を再設定
    if [ "$1" = "--no-report" ]; then
        TEST_TARGET="${2:-tests/}"
    fi
fi

cd "$PROJECT_ROOT"

# 仮想環境を自動検出（venv を優先）
if [ -d "venv" ]; then
    echo "Activating virtual environment: venv"
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "Activating virtual environment: .venv"
    source .venv/bin/activate
else
    echo "⚠️  No virtual environment found. Please create one first."
    exit 1
fi

# コマンド実行の開始マーカー
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "▶ COMMAND: python -m pytest $TEST_TARGET -v --tb=short"
echo "▶ TIMESTAMP: $(date '+%Y-%m-%d %H:%M:%S')"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 結果ディレクトリの準備
RESULTS_DIR="${PROJECT_ROOT}/test_results"
mkdir -p "$RESULTS_DIR"

# 一時ファイルの準備
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_FILE="${RESULTS_DIR}/pytest_output_${TIMESTAMP}.txt"

# pytest を実行して標準出力を保存
if python -m pytest "$TEST_TARGET" -v --tb=short 2>&1 | tee "$OUTPUT_FILE"; then
    PYTEST_EXIT_CODE=0
else
    PYTEST_EXIT_CODE=$?
fi

# コマンド実行の終了マーカー
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $PYTEST_EXIT_CODE -eq 0 ]; then
    echo "▶ COMMAND END: SUCCESS (exit code: $PYTEST_EXIT_CODE)"
else
    echo "▶ COMMAND END: FAILED (exit code: $PYTEST_EXIT_CODE)"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ Test execution complete"
echo ""

# 結果レポートを生成（オプション）
if [ "$GENERATE_REPORT" = true ]; then
    echo "📊 テスト結果レポートを生成中..."
    if python -m dev_tools.test_result_generator "$OUTPUT_FILE" "$TEST_TARGET" "$RESULTS_DIR" 2>/dev/null; then
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
        echo "📄 レポートのサマリー:"
        echo "----------------------------------------"
        # サマリー部分だけを抽出して表示
        grep -A 15 "^## サマリー" "$LATEST_REPORT" | head -20 || head -30 "$LATEST_REPORT"
        echo "----------------------------------------"
        echo ""
        echo "💡 完全なレポートを確認するには:"
        echo "   cat $LATEST_REPORT"
    fi
fi

# 一時ファイルを削除
rm -f "$OUTPUT_FILE"

# pytest の終了コードを返す
exit $PYTEST_EXIT_CODE

