#!/bin/bash
# WSL 起動時に自動的に venv を有効化する設定を追加するスクリプト

set -e

BASHRC_FILE="$HOME/.bashrc"
PROJECT_ROOT="/home/yn441611/NexusCore"

echo "=== WSL 自動 venv 有効化設定 ==="
echo ""

# 既存の設定を削除
if grep -q "# ==== NexusCore auto activate venv ====" "$BASHRC_FILE" 2>/dev/null; then
    echo "既存の設定を削除中..."
    sed -i '/# ==== NexusCore auto activate venv ====/,/^}$/d' "$BASHRC_FILE"
    sed -i '/_nexuscore_auto_activate/d' "$BASHRC_FILE"
    sed -i '/_nexuscore_cd_hook/d' "$BASHRC_FILE"
fi

# 新しい設定を追加
echo "新しい設定を追加中..."
cat >> "$BASHRC_FILE" << 'BASHRC_EOF'

# ==== NexusCore auto activate venv ====
# NexusCore プロジェクトディレクトリで自動的に仮想環境を有効化
# cd コマンド実行後に自動的に仮想環境を有効化
cd() {
    # 元の cd コマンドを実行
    builtin cd "$@"
    # NexusCore プロジェクトディレクトリで自動的に仮想環境を有効化
    if [ -f "$HOME/NexusCore/.cursor/auto_activate_venv.sh" ]; then
        source "$HOME/NexusCore/.cursor/auto_activate_venv.sh"
    fi
}

# 起動時にも自動有効化（NexusCore ディレクトリにいる場合）
if [[ "$PWD" == "$HOME/NexusCore"* ]] && [[ -z "$VIRTUAL_ENV" ]]; then
    if [ -f "$HOME/NexusCore/.cursor/auto_activate_venv.sh" ]; then
        source "$HOME/NexusCore/.cursor/auto_activate_venv.sh"
    fi
fi
BASHRC_EOF

echo "✅ .bashrc に設定を追加しました"
echo ""
echo "設定を有効にするには、以下のいずれかを実行してください："
echo "  1. 新しいターミナルを開く（推奨）"
echo "  2. source ~/.bashrc を実行"
echo ""
echo "NexusCore プロジェクトディレクトリに cd すると、"
echo "自動的に仮想環境（venv）が有効化されます。"
