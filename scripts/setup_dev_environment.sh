#!/usr/bin/env bash
# setup_dev_environment.sh
#
# 開発環境をセットアップするスクリプト
# 仮想環境を有効化し、開発依存パッケージをインストールします。

set -e

cd "$(dirname "$0")/.."

echo "=== NexusCore 開発環境セットアップ ==="
echo ""

# 仮想環境を探す（venv を優先）
VENV_PATH=""
if [ -d "venv" ]; then
    VENV_PATH="venv"
    echo "✅ 仮想環境を発見: venv"
elif [ -d ".venv" ]; then
    VENV_PATH=".venv"
    echo "✅ 仮想環境を発見: .venv"
else
    echo "⚠️  仮想環境が見つかりません。venv を作成します..."
    python3 -m venv venv
    VENV_PATH="venv"
    echo "✅ 仮想環境を作成しました: venv"
fi

# 仮想環境を有効化
echo ""
echo "=== 仮想環境を有効化 ==="
source "$VENV_PATH/bin/activate"

echo "Python: $(which python)"
echo "Python version: $(python --version)"
echo ""

# requirements-dev.txt の確認
if [ ! -f "requirements-dev.txt" ]; then
    echo "⚠️  requirements-dev.txt が見つかりません。作成します..."
    cat > requirements-dev.txt << 'EOF'
# Development dependencies
black
ruff
mypy
EOF
    echo "✅ requirements-dev.txt を作成しました"
    echo ""
fi

# 開発依存パッケージをインストール
echo "=== 開発依存パッケージをインストール ==="
pip install --upgrade pip
pip install -r requirements-dev.txt

echo ""
echo "=== インストール確認 ==="
echo "Black: $(black --version 2>&1 || echo 'not installed')"
echo "Ruff: $(ruff --version 2>&1 || echo 'not installed')"
echo "mypy: $(mypy --version 2>&1 || echo 'not installed')"

echo ""
echo "✅ 開発環境のセットアップが完了しました！"
echo ""
echo "次回からは以下のコマンドで仮想環境を有効化してください:"
echo "  source activate          # 推奨（最も簡単）"
echo "  または"
echo "  source $VENV_PATH/bin/activate  # 直接的な方法"
echo ""
echo "詳細は README_VENV.md を参照してください。"

