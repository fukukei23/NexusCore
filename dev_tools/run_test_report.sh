#!/bin/bash
# JobStateMachine テスト実行スクリプト

cd /home/yn441611/NexusCore
# 仮想環境を有効化（venv を優先）
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

echo "=========================================="
echo "JobStateMachine テスト実行"
echo "=========================================="
echo ""

# テスト実行
PYTHONPATH=src python -m pytest tests/core/test_job_state_machine.py -v --tb=short

# 終了コードを確認
EXIT_CODE=$?

echo ""
echo "=========================================="
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ すべてのテストが成功しました"
else
    echo "❌ テストが失敗しました (終了コード: $EXIT_CODE)"
fi
echo "=========================================="

exit $EXIT_CODE

