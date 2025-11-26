#!/bin/bash
# WSL環境用のLinux形式仮想環境セットアップスクリプト
# 使用方法: bash dev_tools/setup_wsl_venv.sh

set -e

PROJECT_ROOT="/home/yn441611/NexusCore"
VENV_NAME="myenv_linux"

cd "$PROJECT_ROOT"

echo "Creating Linux-compatible virtual environment: $VENV_NAME"
python3 -m venv "$VENV_NAME"

echo "Activating virtual environment..."
source "$VENV_NAME/bin/activate"

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing test dependencies..."
pip install pytest pytest-cov pytest-mock -q

echo "Installing project dependencies..."
if [ -f requirements.txt ]; then
    pip install -r requirements.txt -q
fi

echo ""
echo "✅ Virtual environment setup complete!"
echo ""
echo "To activate:"
echo "  source $VENV_NAME/bin/activate"
echo ""
echo "To run tests:"
echo "  source $VENV_NAME/bin/activate"
echo "  python -m pytest tests/"

