#!/bin/bash
# FastAPI サーバーを起動するスクリプト
# 使用方法: bash scripts/start_fastapi_server.sh

set -e

cd "$(dirname "$0")/.."

# 仮想環境を有効化
if [ -f "activate" ]; then
    source activate
elif [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ 仮想環境が見つかりません"
    exit 1
fi

# PYTHONPATH を設定
export PYTHONPATH="${PYTHONPATH:-}:src"

# FastAPI サーバーを起動
echo "🚀 Starting FastAPI server on http://127.0.0.1:8000"
echo "📖 OpenAPI docs: http://127.0.0.1:8000/api/docs"
echo "📄 OpenAPI JSON: http://127.0.0.1:8000/api/openapi.json"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

uvicorn nexuscore.api.fastapi_app:app \
    --reload \
    --host 127.0.0.1 \
    --port 8000

