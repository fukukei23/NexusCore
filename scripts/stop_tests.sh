#!/usr/bin/env bash
# stop_tests.sh
#
# 実行中のテストを安全に停止するスクリプト

echo "=== 実行中のテストを検索中 ==="

# pytest プロセスを検索
PIDS=$(ps aux | grep -E 'pytest|python.*test' | grep -v grep | awk '{print $2}')

if [ -z "$PIDS" ]; then
    echo "✅ 実行中のテストプロセスはありません"
    exit 0
fi

echo "実行中のテストプロセス:"
ps aux | grep -E 'pytest|python.*test' | grep -v grep

echo ""
read -p "これらのプロセスを停止しますか？ (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    for PID in $PIDS; do
        echo "停止中: PID $PID"
        kill -TERM "$PID" 2>/dev/null || true
    done

    sleep 2

    # まだ残っている場合は強制終了
    REMAINING=$(ps aux | grep -E 'pytest|python.*test' | grep -v grep | awk '{print $2}')
    if [ -n "$REMAINING" ]; then
        echo "強制終了中..."
        for PID in $REMAINING; do
            kill -KILL "$PID" 2>/dev/null || true
        done
    fi

    echo "✅ テストプロセスを停止しました"
else
    echo "キャンセルしました"
fi

