# JobStateMachine 実装完了レポート

**実装日**: 2025年1月
**目的**: Orchestrator の再設計 - ステートマシン設計によるジョブ管理の改善

---

## 実装概要

Orchestrator のジョブ管理を改善するため、ステートマシンパターンを導入しました。これにより、ジョブの進行状況を明確に管理し、エラーハンドリングやリトライロジックを簡潔に実装できるようになりました。

---

## 実装内容

### 1. JobStateMachine と State クラス

**ファイル**: `src/nexuscore/core/job_state_machine.py`

#### 実装した状態

- **PendingState**: ジョブ待機状態
- **RunningState**: ジョブ実行中
- **CompletedState**: ジョブ完了状態（終端状態）
- **FailedState**: ジョブ失敗状態（終端状態）

#### 状態遷移ルール

```
PendingState → RunningState (start())
RunningState → CompletedState (complete())
RunningState → FailedState (fail())
```

#### 主な機能

- `transition_to()`: 状態遷移を実行（遷移可能性をチェック）
- `start()`: ジョブを開始（Pending → Running）
- `complete()`: ジョブを完了（Running → Completed）
- `fail()`: ジョブを失敗として記録（Running → Failed）

### 2. SessionController との統合

状態遷移のたびに、セッション状態を `.nexus/sessions/{session_id}.state.json` に保存します。

```python
session_controller.checkpoint(
    phase=f"state_{new_state_name}",
    metadata={
        "state": new_state_name,
        "job_id": self.job_id,
        "job_type": self.job_type,
        **self.metadata.details,
    }
)
```

これにより、ジョブの中断・再開が可能になります。

### 3. RunHistoryLogger との統合

ジョブの完了・失敗時に、履歴を `.nexus/history/{kind}.log.jsonl` に記録します。

- **完了時**: `status="success"` で記録
- **失敗時**: `status="error"` で記録（エラーメッセージを含む）

### 4. Celery タスクの拡張

**ファイル**: `src/nexuscore/webapp/celery_app.py`

既存の Celery タスク（`nexuscore.run_orchestrator`）を拡張し、`JobStateMachine` を使用するように変更しました。

#### 変更点

- `JobStateMachine` の初期化
- ジョブ開始時に `state_machine.start()` を呼び出し
- 成功時に `state_machine.complete()` を呼び出し
- 失敗時に `state_machine.fail()` を呼び出し

これにより、Celery タスクの実行状況が明確に管理されるようになりました。

---

## 使用方法

### 基本的な使用例

```python
from nexuscore.core.job_state_machine import JobStateMachine
from nexuscore.core.session_control import SessionController
from nexuscore.core.run_history import RunHistoryLogger

# SessionController と RunHistoryLogger を初期化
session_controller = SessionController(
    session_id="job-123",
    root_dir=".nexus/sessions",
)
history_logger = RunHistoryLogger(project_root="/path/to/project")

# JobStateMachine を初期化
state_machine = JobStateMachine(
    job_id="job-123",
    session_controller=session_controller,
    history_logger=history_logger,
    job_type="orchestrator",
)

# ジョブを開始
state_machine.start()

try:
    # ジョブの処理を実行
    result = do_work()
    state_machine.complete(details={"result": result})
except Exception as e:
    state_machine.fail(error_message=str(e), details={"exception": type(e).__name__})
```

### Celery タスクでの使用

既存の Celery タスクは自動的に `JobStateMachine` を使用します。追加の設定は不要です。

```python
from nexuscore.webapp.celery_app import run_orchestrator_task

# タスクをキューに追加
run_orchestrator_task.delay(run_db_id=123)
```

---

## ワーカーの水平スケーリング

### Kubernetes での設定

**ファイル**: `k8s/orchestrator-worker-deployment.yaml`

Kubernetes を使用してワーカーを水平スケーリングできます。

#### デプロイ

```bash
kubectl apply -f k8s/orchestrator-worker-deployment.yaml
```

#### オートスケーリングの設定

```bash
kubectl autoscale deployment orchestrator-worker \
  --cpu-percent=70 \
  --min=2 \
  --max=10
```

#### 手動スケーリング

```bash
kubectl scale deployment orchestrator-worker --replicas=5
```

### Celery ワーカーの起動

```bash
# ローカル環境
celery -A nexuscore.webapp.celery_app worker --loglevel=info --concurrency=4

# Kubernetes 環境（Deployment で自動起動）
```

---

## テスト

### ユニットテスト

**ファイル**: `tests/core/test_job_state_machine.py`

以下のテストを実装しました：

- 基本状態遷移テスト
- SessionController との統合テスト
- RunHistoryLogger との統合テスト
- 完全統合テスト

#### テスト実行

```bash
cd /home/yn441611/NexusCore
source myenv_linux/bin/activate
python -m pytest tests/core/test_job_state_machine.py -v
```

---

## 既存コードとの互換性

### 後方互換性

- 既存の `SessionController` と `RunHistoryLogger` の API は変更していません
- 既存の Celery タスクは、`JobStateMachine` を使用するように拡張しましたが、外部インターフェースは変更していません

### 移行ガイド

既存のコードを `JobStateMachine` を使用するように移行する場合：

1. `JobStateMachine` をインポート
2. セッションコントローラーと履歴ロガーを初期化
3. `JobStateMachine` を初期化
4. `start()`, `complete()`, `fail()` メソッドを使用

---

## 今後の拡張予定

### リトライ機能

失敗時に自動リトライする機能を追加予定：

```python
class RetryableJobStateMachine(JobStateMachine):
    def fail(self, error_message: str, retry_count: int = 0):
        if retry_count < self.max_retries:
            # リトライ可能な場合は RunningState に戻す
            self.transition_to(RunningState)
        else:
            super().fail(error_message)
```

### 進捗管理

ジョブの進捗を管理する機能を追加予定：

```python
state_machine.update_progress(percentage=50, message="Processing...")
```

### サブジョブ管理

複数のサブジョブを管理する機能を追加予定：

```python
state_machine.add_subjob(subjob_id="sub-1")
state_machine.complete_subjob(subjob_id="sub-1")
```

---

## まとめ

`JobStateMachine` の実装により、以下の改善を実現しました：

1. ✅ **状態管理の明確化**: ジョブの進行状況が明確に管理される
2. ✅ **エラーハンドリングの簡潔化**: 状態遷移によりエラーハンドリングが簡潔に
3. ✅ **セッション管理の統合**: 状態がセッションに保存され、中断・再開が可能
4. ✅ **履歴管理の統合**: ジョブの履歴が自動的に記録される
5. ✅ **Celery との統合**: 既存の Celery タスクが自動的に `JobStateMachine` を使用

これにより、Orchestrator のスケーラビリティと可維持性が向上しました。

---

**実装者**: NexusCore Development Team
**レビュー推奨日**: 実装完了後1週間以内

