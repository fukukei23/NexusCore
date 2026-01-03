#!/usr/bin/env bash
# activate_venv.sh
#
# 仮想環境を簡単に有効化するスクリプト（activate のエイリアス）
# 使い方: source activate_venv.sh または . activate_venv.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 仮想環境を探す（venv を優先）
if [ -d "$SCRIPT_DIR/venv" ]; then
    source "$SCRIPT_DIR/venv/bin/activate"
    echo "✅ 仮想環境を有効化しました: venv"
elif [ -d "$SCRIPT_DIR/.venv" ]; then
    source "$SCRIPT_DIR/.venv/bin/activate"
    echo "✅ 仮想環境を有効化しました: .venv"
# myenv_linux は削除されたため、フォールバックから除外
else
    echo "❌ 仮想環境が見つかりません"
    echo "   以下のコマンドで作成してください:"
    echo "   python3 -m venv .venv"
    return 1 2>/dev/null || exit 1
fi

