#!/usr/bin/env python3
"""JobStateMachine の簡単な動作確認スクリプト"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from nexuscore.core.job_state_machine import (
    CompletedState,
    FailedState,
    JobStateMachine,
    PendingState,
    RunningState,
)


def test_basic():
    """基本的な動作確認"""
    print("=" * 60)
    print("JobStateMachine 基本動作テスト")
    print("=" * 60)

    # テスト1: 初期状態
    print("\n[テスト1] 初期状態の確認")
    machine = JobStateMachine(job_id="test-job-1")
    assert isinstance(machine.state, PendingState), "初期状態は PendingState であるべき"
    assert machine.get_current_state() == "pending", "状態名は 'pending' であるべき"
    print("✓ 初期状態は PendingState")

    # テスト2: Pending → Running
    print("\n[テスト2] Pending → Running の遷移")
    machine.start()
    assert isinstance(machine.state, RunningState), "状態は RunningState であるべき"
    assert machine.get_current_state() == "running", "状態名は 'running' であるべき"
    assert machine.metadata.started_at is not None, "started_at が設定されているべき"
    print("✓ Pending → Running の遷移成功")

    # テスト3: Running → Completed
    print("\n[テスト3] Running → Completed の遷移")
    machine.complete(details={"test": "data"})
    assert isinstance(machine.state, CompletedState), "状態は CompletedState であるべき"
    assert machine.get_current_state() == "completed", "状態名は 'completed' であるべき"
    assert machine.metadata.finished_at is not None, "finished_at が設定されているべき"
    assert machine.metadata.details.get("test") == "data", "details が正しく保存されているべき"
    print("✓ Running → Completed の遷移成功")

    # テスト4: 失敗ケース
    print("\n[テスト4] Running → Failed の遷移")
    machine2 = JobStateMachine(job_id="test-job-2")
    machine2.start()
    machine2.fail("Test error", details={"error_code": 500})
    assert isinstance(machine2.state, FailedState), "状態は FailedState であるべき"
    assert machine2.get_current_state() == "failed", "状態名は 'failed' であるべき"
    assert machine2.metadata.error == "Test error", "エラーメッセージが正しく保存されているべき"
    print("✓ Running → Failed の遷移成功")

    print("\n" + "=" * 60)
    print("すべてのテストが成功しました！")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        test_basic()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ テスト失敗: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
