#!/bin/bash
# NexusCore プロジェクトディレクトリで自動的に仮想環境を有効化するスクリプト
# このスクリプトは .bashrc から呼び出されます

NEXUSCORE_PROJECT_ROOT="/home/yn441611/NexusCore"

# 現在のディレクトリが NexusCore プロジェクト内かチェック
if [[ "$PWD" == "$NEXUSCORE_PROJECT_ROOT"* ]]; then
    # 仮想環境が既に有効化されているかチェック
    if [[ -z "$VIRTUAL_ENV" ]]; then
        # venv を優先して検出・有効化（絶対パスを使用）
        if [ -d "$NEXUSCORE_PROJECT_ROOT/venv" ]; then
            source "$NEXUSCORE_PROJECT_ROOT/venv/bin/activate"
        elif [ -d "$NEXUSCORE_PROJECT_ROOT/.venv" ]; then
            source "$NEXUSCORE_PROJECT_ROOT/.venv/bin/activate"
        fi
        # myenv_linux は削除されたため、フォールバックから除外
    fi
fi
