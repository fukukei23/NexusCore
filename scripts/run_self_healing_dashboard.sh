#!/usr/bin/env bash
# run_self_healing_dashboard.sh
#
# NexusCore Self-Healing Dashboard を簡単に起動するためのスクリプト。
# 例:
#   ./scripts/run_self_healing_dashboard.sh
#   ./scripts/run_self_healing_dashboard.sh /path/to/project

set -e

PROJECT_ROOT="${1:-.}"

echo "Launching Self-Healing Dashboard for project_root=${PROJECT_ROOT}"

# プロジェクトルートを絶対パスに変換
if [ ! -d "$PROJECT_ROOT" ]; then
    echo "エラー: プロジェクトルートが見つかりません: $PROJECT_ROOT"
    exit 1
fi

PROJECT_ROOT=$(cd "$PROJECT_ROOT" && pwd)
echo "Using project_root: $PROJECT_ROOT"

# 仮想環境を有効化（venv を優先）
if [ -d "venv" ]; then
    source venv/bin/activate || true
elif [ -d ".venv" ]; then
    source .venv/bin/activate || true
fi

# Streamlitを実行
# プロジェクトルートを環境変数として渡す
export NEXUS_PROJECT_ROOT="$PROJECT_ROOT"

# Streamlitの引数としても渡す（環境変数と併用）
streamlit run src/nexuscore/ui/self_healing_dashboard.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.headless true \
    -- --project-root "$PROJECT_ROOT"

