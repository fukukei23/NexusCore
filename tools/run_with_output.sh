#!/bin/bash
# run_with_output.sh
#
# WSL環境でCursorのrun_terminal_cmdで出力が取得できない問題を解決するための
# シェルスクリプトラッパー。
#
# 使用方法:
#   ./tools/run_with_output.sh <command> [args...]
#
# 例:
#   ./tools/run_with_output.sh pytest tests/ -v
#   ./tools/run_with_output.sh python tools/run_browser_use.py --site MONCLER_OFFICIAL

set -euo pipefail

# ログファイル名を生成
LOG_FILE="${LOG_FILE:-output_$(date +%Y%m%d_%H%M%S).log}"

# Pythonのバッファリングを無効化
export PYTHONUNBUFFERED=1

echo "🚀 実行中: $*"
echo "📝 ログファイル: $LOG_FILE"
echo "--------------------------------------------------------------------------------"

# コマンドを実行し、ログファイルにも出力
"$@" 2>&1 | tee "$LOG_FILE"

EXIT_CODE=${PIPESTATUS[0]}

echo "--------------------------------------------------------------------------------"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ 正常終了"
else
    echo "❌ エラー終了 (終了コード: $EXIT_CODE)"
fi

echo "📝 ログファイル: $LOG_FILE"

exit $EXIT_CODE

