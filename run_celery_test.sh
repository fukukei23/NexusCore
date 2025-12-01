#!/bin/bash
# Celery JobStateMachine テスト実行スクリプト

cd /home/yn441611/NexusCore
source myenv_linux/bin/activate

echo "=========================================="
echo "Celery JobStateMachine テスト実行"
echo "=========================================="
echo ""

# テスト実行
PYTHONPATH=src python -m pytest tests/webapp/test_celery_job_state_machine.py -v --tb=short

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

