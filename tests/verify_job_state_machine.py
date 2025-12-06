#!/usr/bin/env python3
"""JobStateMachine の動作確認スクリプト"""
import sys
import os

# パスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    print("=" * 60)
    print("JobStateMachine 動作確認")
    print("=" * 60)

    try:
        # インポートテスト
        print("\n[1] インポートテスト...")
        from nexuscore.core.job_state_machine import (
            JobStateMachine,
            PendingState,
            RunningState,
            CompletedState,
            FailedState,
        )
        print("✓ インポート成功")

        # 基本動作テスト
        print("\n[2] 基本動作テスト...")
        machine = JobStateMachine(job_id="verify-test-1")
        assert isinstance(machine.state, PendingState), "初期状態は PendingState"
        assert machine.get_current_state() == "pending", "状態名は 'pending'"
        print("✓ 初期状態: PendingState")

        # 状態遷移テスト
        print("\n[3] 状態遷移テスト...")
        machine.start()
        assert isinstance(machine.state, RunningState), "状態は RunningState"
        assert machine.get_current_state() == "running", "状態名は 'running'"
        print("✓ Pending → Running")

        machine.complete(details={"test": "success"})
        assert isinstance(machine.state, CompletedState), "状態は CompletedState"
        assert machine.get_current_state() == "completed", "状態名は 'completed'"
        print("✓ Running → Completed")

        # 失敗ケーステスト
        print("\n[4] 失敗ケーステスト...")
        machine2 = JobStateMachine(job_id="verify-test-2")
        machine2.start()
        machine2.fail("Test error")
        assert isinstance(machine2.state, FailedState), "状態は FailedState"
        assert machine2.get_current_state() == "failed", "状態名は 'failed'"
        print("✓ Running → Failed")

        print("\n" + "=" * 60)
        print("✅ すべての検証が成功しました！")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

