#!/usr/bin/env bash
# test_e2e_self_healing.sh
#
# Self-Healing E2E テストを実行するスクリプト
# サーバを起動し、モック Webhook を送信して結果を確認します。

set -e

PROJECT_ROOT="${1:-$(pwd)}"
cd "$PROJECT_ROOT"

echo "=== Self-Healing E2E テスト ==="
echo "Project root: $PROJECT_ROOT"

# 仮想環境を有効化
if [ -d "myenv_linux" ]; then
    source myenv_linux/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# 環境変数を設定
export NEXUS_PROJECT_ROOT="$PROJECT_ROOT"

# 設定ファイルの確認
if [ ! -f ".nexus/self_healing.config.json" ]; then
    echo "⚠️  設定ファイルが見つかりません。.nexus/self_healing.config.json.example をコピーします。"
    mkdir -p .nexus
    cp .nexus/self_healing.config.json.example .nexus/self_healing.config.json 2>/dev/null || {
        echo '{"label": "self-healing", "allowed_target_branches": ["main"], "test_command": "pytest -q", "allow_test_modification": false, "allow_deletions": false}' > .nexus/self_healing.config.json
    }
fi

# テスト用のリポジトリ情報を取得
REPO_FULL_NAME="${REPO_FULL_NAME:-$(git remote get-url origin 2>/dev/null | sed 's/.*github.com[:/]\(.*\)\.git/\1/' | sed 's/.*github.com\/\(.*\)/\1/')}"
if [ -z "$REPO_FULL_NAME" ]; then
    REPO_FULL_NAME="test/repo"
    echo "⚠️  リポジトリ情報が取得できません。デフォルト値を使用: $REPO_FULL_NAME"
fi

HEAD_SHA="${HEAD_SHA:-$(git rev-parse HEAD 2>/dev/null || echo '0123456789abcdef')}"
PR_NUMBER="${PR_NUMBER:-1}"
BASE_BRANCH="${BASE_BRANCH:-main}"

echo ""
echo "=== テストパラメータ ==="
echo "Repository: $REPO_FULL_NAME"
echo "PR Number: $PR_NUMBER"
echo "HEAD SHA: $HEAD_SHA"
echo "Base Branch: $BASE_BRANCH"
echo ""

# サーバをバックグラウンドで起動
echo "=== サーバ起動 ==="
SERVER_PID=""
cleanup() {
    if [ -n "$SERVER_PID" ]; then
        echo ""
        echo "=== サーバを停止します ==="
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

python src/nexuscore/api/server.py > /tmp/nexus_server.log 2>&1 &
SERVER_PID=$!

echo "サーバ PID: $SERVER_PID"
echo "ログファイル: /tmp/nexus_server.log"

# サーバが起動するまで待機
echo "サーバの起動を待機中..."
for i in {1..10}; do
    if curl -s http://127.0.0.1:5001/api/v1/status/test > /dev/null 2>&1; then
        echo "✅ サーバが起動しました"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "❌ サーバの起動に失敗しました"
        cat /tmp/nexus_server.log
        exit 1
    fi
    sleep 1
done

# モック Webhook を送信
echo ""
echo "=== モック Webhook 送信 ==="
python tools/mock_github_pr_webhook.py \
    --url http://127.0.0.1:5001/api/github/webhook \
    --repo-full-name "$REPO_FULL_NAME" \
    --pr-number "$PR_NUMBER" \
    --head-sha "$HEAD_SHA" \
    --label "self-healing" \
    --base-branch "$BASE_BRANCH" \
    2>&1 | tee /tmp/webhook_response.log

echo ""
echo "=== サーバログ（最新10行） ==="
tail -10 /tmp/nexus_server.log || echo "ログが見つかりません"

echo ""
echo "=== 実行履歴の確認 ==="
if [ -f ".nexus/history/self_healing.log.jsonl" ]; then
    echo "最新の実行履歴:"
    tail -1 .nexus/history/self_healing.log.jsonl | python -m json.tool 2>/dev/null || tail -1 .nexus/history/self_healing.log.jsonl
else
    echo "⚠️  実行履歴ファイルが見つかりません"
fi

echo ""
echo "=== E2E テスト完了 ==="

