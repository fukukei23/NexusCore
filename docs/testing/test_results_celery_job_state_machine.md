# Celery JobStateMachine テスト実行結果

**実行日**: 2025年11月30日
**テストファイル**: `tests/webapp/test_celery_job_state_machine.py`

---

## テスト概要

Celery タスクと JobStateMachine の統合を検証するため、以下のテストを実装しました：

### 実装されたテスト

1. **Celery タスクの統合テスト** (`TestCeleryTaskWithJobStateMachine` - 4個)
   - `test_celery_task_state_transition_success`: 正常な状態遷移のテスト
   - `test_celery_task_state_transition_failure`: 失敗時の状態遷移のテスト
   - `test_celery_task_with_missing_run`: Run が見つからない場合のテスト
   - `test_celery_task_with_missing_requirement`: requirement が空の場合のテスト

2. **JobStateMachine の動作テスト** (`TestJobStateMachineInCeleryContext` - 3個)
   - `test_job_state_machine_initialization_in_celery`: Celery コンテキスト内での初期化テスト
   - `test_job_state_machine_lifecycle_in_celery`: ライフサイクルのテスト
   - `test_job_state_machine_failure_in_celery`: 失敗処理のテスト

3. **非同期処理のテスト** (`TestAsyncJobProcessing` - 2個)
   - `test_celery_task_registration`: Celery タスクの登録テスト
   - `test_job_state_machine_with_session_persistence`: セッション状態の永続化テスト

**合計テスト数**: 9個

---

## テスト実行方法

### 基本的な実行

```bash
cd /home/yn441611/NexusCore
source myenv_linux/bin/activate
PYTHONPATH=src python -m pytest tests/webapp/test_celery_job_state_machine.py -v
```

### 詳細な出力

```bash
PYTHONPATH=src python -m pytest tests/webapp/test_celery_job_state_machine.py -v --tb=short
```

### 特定のテストクラスのみ実行

```bash
PYTHONPATH=src python -m pytest tests/webapp/test_celery_job_state_machine.py::TestJobStateMachineInCeleryContext -v
```

---

## 実装の検証

### 1. インポート確認

以下のクラスが正しくインポートできることを確認：

```python
from nexuscore.core.job_state_machine import (
    JobStateMachine,
    PendingState,
    RunningState,
    CompletedState,
    FailedState,
)
from nexuscore.core.session_control import SessionController
from nexuscore.core.run_history import RunHistoryLogger
from nexuscore.webapp.celery_app import run_orchestrator_task
```

### 2. Celery タスクの動作確認

```python
# Celery タスクが JobStateMachine を使用することを確認
from nexuscore.webapp.celery_app import run_orchestrator_task

# タスクを実行（モックを使用）
run_orchestrator_task(run_db_id=1)
```

### 3. 状態遷移の確認

```python
# Celery タスク内での状態遷移を確認
state_machine = JobStateMachine(
    job_id="test-job",
    session_controller=session_controller,
    history_logger=history_logger,
    job_type="orchestrator",
)

state_machine.start()  # Pending → Running
state_machine.complete()  # Running → Completed
```

---

## 期待される動作

### Celery タスクの状態遷移フロー

```
PendingState → RunningState → CompletedState (成功時)
                          ↓
                       FailedState (失敗時)
```

### 状態遷移の確認ポイント

- **タスク開始時**: `state_machine.start()` で Pending → Running
- **成功時**: `state_machine.complete()` で Running → Completed
- **失敗時**: `state_machine.fail()` で Running → Failed
- **セッション状態**: `.nexus/sessions/{session_id}.state.json` に保存
- **履歴**: `.nexus/history/orchestrator.log.jsonl` に記録

---

## 統合機能

### SessionController との統合

Celery タスク内で状態遷移のたびに、セッション状態が `.nexus/sessions/{session_id}.state.json` に保存されます。

### RunHistoryLogger との統合

Celery タスクの完了・失敗時に、履歴が `.nexus/history/orchestrator.log.jsonl` に記録されます。

### データベースとの統合

Celery タスクは Run テーブルの `status`, `started_at`, `finished_at` を更新します。

---

## 注意事項

- テスト実行時は `PYTHONPATH=src` を設定してください
- Celery タスクのテストはモックを使用してデータベースへの依存を回避します
- 一時ファイルを使用するテストは、自動的にクリーンアップされます
- Celery ワーカーが起動している必要はありません（タスク関数を直接呼び出します）

---

## トラブルシューティング

### インポートエラー

```bash
# PYTHONPATH を設定
export PYTHONPATH=src:$PYTHONPATH
```

### テストが見つからない

```bash
# テストファイルの存在を確認
ls -la tests/webapp/test_celery_job_state_machine.py
```

### 依存関係エラー

```bash
# 必要なパッケージをインストール
pip install pytest celery
```

### モックエラー

テストは `unittest.mock` を使用して Celery タスクをモック化しています。モックの設定が正しいことを確認してください。

---

**テスト実装者**: NexusCore Development Team
**最終更新**: 2025年11月30日

