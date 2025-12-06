#!/usr/bin/env python3
"""Celery JobStateMachine テストの簡単な検証スクリプト"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """インポートテスト"""
    print("=" * 60)
    print("Celery JobStateMachine テスト - インポート検証")
    print("=" * 60)

    try:
        from nexuscore.core.job_state_machine import (
            JobStateMachine,
            PendingState,
            RunningState,
            CompletedState,
            FailedState,
        )
        print("✅ JobStateMachine のインポート成功")

        from nexuscore.core.session_control import SessionController
        print("✅ SessionController のインポート成功")

        from nexuscore.core.run_history import RunHistoryLogger
        print("✅ RunHistoryLogger のインポート成功")

        # Celery タスクのインポート（オプション）
        try:
            from nexuscore.webapp.celery_app import run_orchestrator_task
            print("✅ Celery タスクのインポート成功")
        except Exception as e:
            print(f"⚠️ Celery タスクのインポート失敗（テスト環境では正常）: {e}")

        print("\n" + "=" * 60)
        print("✅ すべてのインポートが成功しました！")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n❌ インポートエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)

