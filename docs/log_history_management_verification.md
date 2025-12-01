# ログと履歴管理の確認ガイド

## 概要

NexusCore のジョブ履歴とログ管理機能の動作確認とトラブルシューティングガイドです。

## 1. ジョブ履歴の保存

### 1.1 保存先

ジョブの履歴は以下の場所に保存されます：

- **履歴ファイル**: `<project_root>/.nexus/history/{kind}.log.jsonl`
  - `kind`: ジョブの種類（例: "orchestrator", "self_healing"）
  - 形式: JSONL（1行 = 1実行の RunRecord）

- **セッション状態**: `<project_root>/.nexus/sessions/{session_id}.state.json`
  - セッションの現在状態（フェーズ、メタデータなど）

### 1.2 記録される情報

**RunRecord に含まれる情報:**
- `run_id`: ジョブの実行ID
- `session_id`: セッションID
- `kind`: ジョブの種類
- `status`: 状態（"success", "error", "fixed", "not_fixed" など）
- `started_at`: 開始時刻（Unix timestamp）
- `finished_at`: 終了時刻（Unix timestamp）
- `summary`: サマリー
- `details`: 詳細情報（辞書形式）

**SessionState に含まれる情報:**
- `session_id`: セッションID
- `status`: セッション状態（"running", "paused", "stopped"）
- `last_phase`: 最後のフェーズ（例: "after_planning", "state_completed"）
- `last_updated`: 最終更新時刻（Unix timestamp）
- `metadata`: メタデータ（辞書形式）

### 1.3 状態遷移の記録

ジョブの状態遷移は以下のように記録されます：

1. **Pending → Running**: ジョブ開始時
2. **Running → Completed**: ジョブ成功時
3. **Running → Failed**: ジョブ失敗時

各状態遷移時に：
- `RunHistoryLogger` が履歴を記録
- `SessionController` がセッション状態を保存

## 2. RunHistoryLogger と SessionController の連携

### 2.1 統合の仕組み

`JobStateMachine` が `RunHistoryLogger` と `SessionController` を統合：

```python
# celery_app.py での使用例
session_controller = SessionController(
    session_id=job_id,
    root_dir=session_dir,
)
history_logger = RunHistoryLogger(project_root=project.local_path)

state_machine = JobStateMachine(
    job_id=job_id,
    session_controller=session_controller,
    history_logger=history_logger,
    job_type="orchestrator",
)
```

### 2.2 動作フロー

1. **ジョブ開始時**:
   - `state_machine.start()` → Pending → Running
   - `SessionController.checkpoint()` でセッション状態を保存
   - `RunHistoryLogger` で状態遷移を記録

2. **フェーズごと**:
   - `SessionController.checkpoint(phase="after_planning", metadata={...})` でチェックポイントを保存

3. **ジョブ完了時**:
   - `state_machine.complete()` → Running → Completed
   - `RunHistoryLogger.log_run()` で最終履歴を記録
   - `SessionController.checkpoint()` で最終状態を保存

4. **ジョブ失敗時**:
   - `state_machine.fail()` → Running → Failed
   - `RunHistoryLogger.log_run()` でエラー履歴を記録
   - `SessionController.checkpoint()` でエラー状態を保存

## 3. 確認項目

### 3.1 ジョブの開始時に履歴が保存されているか

```bash
# 履歴ファイルを確認
cat <project_root>/.nexus/history/orchestrator.log.jsonl | jq .

# 最新の履歴を確認
tail -1 <project_root>/.nexus/history/orchestrator.log.jsonl | jq .
```

**確認ポイント:**
- `run_id` が正しく記録されているか
- `started_at` が記録されているか
- `status` が "success" または "error" になっているか

### 3.2 状態遷移時に履歴が保存されているか

```bash
# セッション状態を確認
cat <project_root>/.nexus/sessions/<session_id>.state.json | jq .

# 履歴ファイルを確認
cat <project_root>/.nexus/history/orchestrator.log.jsonl | jq .
```

**確認ポイント:**
- `last_phase` が正しく更新されているか
- `metadata` に必要な情報が含まれているか
- 履歴ファイルに状態遷移が記録されているか

### 3.3 エラーハンドリング時に履歴が適切に記録されているか

```bash
# エラー履歴を確認
cat <project_root>/.nexus/history/orchestrator.log.jsonl | jq 'select(.status == "error")'

# エラーメッセージを確認
cat <project_root>/.nexus/history/orchestrator.log.jsonl | jq 'select(.status == "error") | .summary'
```

**確認ポイント:**
- `status` が "error" になっているか
- `summary` にエラーメッセージが含まれているか
- `details.error` にエラー詳細が記録されているか

### 3.4 セッション情報が適切に保存され、再開時に復元されること

```bash
# セッション状態を確認
cat <project_root>/.nexus/sessions/<session_id>.state.json | jq .

# セッションの再開をシミュレート
python -c "
from nexuscore.core.session_control import SessionController
controller = SessionController(session_id='<session_id>', root_dir='<project_root>/.nexus/sessions')
# 状態ファイルが存在することを確認
"
```

**確認ポイント:**
- セッション状態ファイルが存在するか
- `last_phase` が正しく保存されているか
- `metadata` が正しく保存されているか
- 再開時に状態が復元できるか

## 4. トラブルシューティング

### 4.1 履歴が保存されない場合

**原因:**
- ディレクトリの権限不足
- ディスク容量不足
- `RunHistoryLogger` の初期化エラー

**対処:**
```bash
# ディレクトリの権限を確認
ls -la <project_root>/.nexus/history/

# ディスク容量を確認
df -h

# ログを確認
tail -f <project_root>/.nexus/history/orchestrator.log.jsonl
```

### 4.2 セッション状態が保存されない場合

**原因:**
- ディレクトリの権限不足
- `SessionController` の初期化エラー
- チェックポイントが呼ばれていない

**対処:**
```bash
# ディレクトリの権限を確認
ls -la <project_root>/.nexus/sessions/

# セッション状態ファイルを確認
ls -la <project_root>/.nexus/sessions/*.state.json

# コードでチェックポイントが呼ばれているか確認
grep -r "checkpoint" src/nexuscore/
```

### 4.3 履歴ファイルが破損している場合

**対処:**
```python
# RunHistoryLogger の load_runs メソッドは破損した行をスキップする
from nexuscore.core.run_history import RunHistoryLogger

history_logger = RunHistoryLogger(project_root="<project_root>")
records = history_logger.load_runs("orchestrator")
# 破損した行は自動的にスキップされる
```

## 5. テスト

統合テストを実行して、ログと履歴管理が正しく動作することを確認：

```bash
# 統合テストを実行
PYTHONPATH=src python -m pytest tests/integration/test_log_history_management.py -v

# 特定のテストを実行
PYTHONPATH=src python -m pytest tests/integration/test_log_history_management.py::TestLogHistoryManagement::test_job_history_saved_to_jsonl -v
```

## 6. データベースへの保存（将来の拡張）

現在は JSONL ファイルに保存していますが、将来的にデータベースに保存する場合：

```sql
CREATE TABLE job_history (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(255) NOT NULL,
    session_id VARCHAR(255) NOT NULL,
    tenant_id INT,
    user_id INT,
    job_type VARCHAR(255),
    job_state VARCHAR(255),
    status VARCHAR(255),
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    summary TEXT,
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_job_history_job_id ON job_history(job_id);
CREATE INDEX idx_job_history_session_id ON job_history(session_id);
CREATE INDEX idx_job_history_tenant_id ON job_history(tenant_id);
CREATE INDEX idx_job_history_created_at ON job_history(created_at);
```

## 7. 関連ファイル

- `src/nexuscore/core/run_history.py`: RunHistoryLogger の実装
- `src/nexuscore/core/session_control.py`: SessionController の実装
- `src/nexuscore/core/job_state_machine.py`: JobStateMachine の実装
- `src/nexuscore/webapp/celery_app.py`: Celery タスクでの使用例
- `tests/integration/test_log_history_management.py`: 統合テスト

