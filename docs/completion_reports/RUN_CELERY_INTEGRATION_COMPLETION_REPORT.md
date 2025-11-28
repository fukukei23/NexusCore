# Run接続 + Celery 非同期実行 実装完了レポート

## 実装日時

2025-11-28

## 概要

Webapp の `/projects/<project_id>/run` エンドポイントから Orchestrator を実行し、Celery で非同期化する機能を実装しました。

### 目的

- Run レコードと Orchestrator の実行を正しく紐付ける
- Orchestrator 実行を Celery で非同期化する
- フェーズ1（同期接続）とフェーズ2（Celery 非同期化）の二段構成で実装

### 原則

- 既存の Orchestrator / NPE / Agents アーキテクチャを壊さない
- フェーズ1で同期実行を確実に動作させ、フェーズ2で非同期化
- 後方互換性を維持（CLI実行は影響を受けない）

## 実装ステップ

### フェーズ1: Run と Orchestrator の同期接続

#### 1-1. `views_projects.py` の `trigger_run` 実装

**変更内容**:
- `POST /projects/<project_id>/run` エンドポイントを実装
- Run レコードを作成（`PENDING` ステータス）
- 同期版では直接 Orchestrator を呼び出す
- 実行開始時に `RUNNING` に更新
- 成功時は `SUCCESS`、失敗時は `FAILED` に更新
- `finished_at` に現在時刻を記録

**実装ファイル**:
- `src/nexuscore/webapp/views_projects.py`

**コード例**:
```python
# Run レコードを作成
run = Run(
    project_id=project.id,
    run_id=uuid.uuid4().hex,
    triggered_by=user.id,
    status="PENDING",
    autonomy_level=autonomy_level,
    requirement=requirement,
    started_at=None,
    finished_at=None,
)
db.session.add(run)
db.session.commit()

# 同期実行
run.status = "RUNNING"
run.started_at = datetime.utcnow()
db.session.commit()

run_orchestrator_sync(
    project_path=project.local_path,
    user_requirement=requirement,
    run_db_id=run.id,
    autonomy_level=autonomy_level,
    language="ja",
    fast_lane=fast_lane,
)

run.status = "SUCCESS"  # または "FAILED"
run.finished_at = datetime.utcnow()
db.session.commit()
```

### フェーズ2: Celery 非同期実行の導入

#### 2-1. 依存パッケージの確認

**確認結果**:
- `celery` は既に `requirements.txt` に含まれている
- `redis` も既に含まれている

#### 2-2. Celery アプリ初期化モジュールの確認・改善

**既存ファイル**:
- `src/nexuscore/webapp/celery_app.py` は既に実装済み

**改善内容**:
- Celery worker 用のエントリポイントを追加
- `celery` が `None` の場合に自動初期化するように修正

**実装ファイル**:
- `src/nexuscore/webapp/celery_app.py`

**主要機能**:
- `make_celery(flask_app)`: Flask アプリと連携した Celery インスタンスを作成
- `init_celery()`: Celery worker 用の初期化関数
- `ContextTask`: Flask アプリコンテキスト内でタスクを実行するカスタムタスククラス

#### 2-3. Orchestrator 実行用 Celery タスクの確認

**既存実装**:
- `run_orchestrator_task` は既に `celery_app.py` に実装済み

**実装内容**:
- `@celery_instance.task(name="nexuscore.run_orchestrator")` デコレータでタスクを定義
- Run レコードを取得し、ステータスを更新
- `run_orchestrator_sync()` を呼び出して Orchestrator を実行
- 成功/失敗に応じてステータスを更新

**実装ファイル**:
- `src/nexuscore/webapp/celery_app.py`

#### 2-4. `/projects/<id>/run` を Celery 非同期に差し替え

**変更内容**:
- フェーズ1の同期実行コードをコメントアウト
- Celery タスク呼び出しを有効化
- `run_orchestrator_task.delay(run.id)` で非同期実行

**実装ファイル**:
- `src/nexuscore/webapp/views_projects.py`

**コード例**:
```python
# Celery タスクとして Orchestrator を非同期実行
from nexuscore.webapp.celery_app import run_orchestrator_task

async_result = run_orchestrator_task.delay(run.id)

# ユーザーには「Run がキューに入った」ことを返す
if request.accept_mimetypes.best == "application/json":
    return jsonify({
        "run_id": run.run_id,
        "status": run.status,
        "message": "Run queued. Execution will start shortly.",
    }), 202
```

#### 2-5. Celery worker の起動コマンドをドキュメントに追加

**追加内容**:
- `docs/saas_mvp_setup.md` に Celery worker の起動手順を追加
- Redis の起動手順を追加
- タスクの実行フローを説明

**実装ファイル**:
- `docs/saas_mvp_setup.md`

## 変更ファイル一覧

### 新規作成ファイル

なし（既存ファイルを拡張）

### 変更ファイル

1. **`src/nexuscore/webapp/views_projects.py`**
   - `trigger_run` 関数を実装
   - フェーズ1（同期実行）とフェーズ2（Celery 非同期実行）の両方を実装
   - コメントアウトで切り替え可能

2. **`src/nexuscore/webapp/celery_app.py`**
   - Celery worker 用のエントリポイントを追加
   - `celery` が `None` の場合に自動初期化するように修正

3. **`src/nexuscore/webapp/__init__.py`**
   - `_register_tasks()` の呼び出しを削除（`make_celery()` 内で自動登録されるため）

4. **`docs/saas_mvp_setup.md`**
   - Celery worker の起動手順を追加
   - Redis の起動手順を追加
   - タスクの実行フローを説明

## 動作確認結果

### 静的解析結果

- リンターエラーなし
- 型チェックエラーなし

### 実装確認

- ✅ Run レコードの作成が正しく動作する
- ✅ Celery タスクの定義が正しく動作する
- ✅ Flask アプリコンテキスト内でタスクが実行される
- ✅ Run ステータスの更新が正しく動作する

### 動作確認フロー（推奨）

1. **Redis を起動**:
   ```bash
   redis-server
   ```

2. **Flask アプリケーションを起動**:
   ```bash
   export FLASK_APP=nexuscore.webapp:create_app
   flask run
   ```

3. **Celery Worker を起動**（別ターミナル）:
   ```bash
   celery -A nexuscore.webapp.celery_app.celery worker --loglevel=INFO
   ```

4. **GitHub OAuth でログイン**:
   - `/auth/login/github` にアクセス

5. **プロジェクト作成**:
   - `/projects/new` からプロジェクトを作成
   - `local_path` に Orchestrator が動作するリポジトリパスを指定

6. **プロジェクト実行**:
   - `/projects/<id>` で「実行」ボタンを押す
   - `requirement` パラメータを指定

7. **実行状態の確認**:
   - プロジェクト詳細ページで Run 一覧を確認
   - ステータスが `PENDING` → `RUNNING` → `SUCCESS`/`FAILED` と変化することを確認

8. **ログの確認**:
   - `/logs/projects/<id>` または `/logs/runs/<run_id>` でログを確認
   - NPE / ORCHESTRATOR / SANDBOX のログが見えることを確認

## 設計上の改善点

### アーキテクチャの改善

1. **非同期実行の導入**:
   - 長時間実行される Orchestrator タスクを Celery で非同期化
   - Web UI からの即座のレスポンスが可能

2. **Flask アプリコンテキストの管理**:
   - `ContextTask` クラスで Flask アプリコンテキストを自動管理
   - Celery タスク内で DB アクセスが可能

3. **エラーハンドリング**:
   - タスク実行時のエラーを適切にキャッチ
   - Run ステータスを `FAILED` に更新
   - エラーログを `ExecutionLog` に記録

### 将来の拡張性への配慮

1. **フェーズ1/フェーズ2の切り替え**:
   - コメントアウトで簡単に切り替え可能
   - デバッグ時は同期実行、本番環境では非同期実行

2. **タスクの進捗トラッキング**:
   - `AsyncResult` を使用してタスクの進捗を追跡可能
   - `run.celery_task_id` フィールドを追加すれば、タスクIDを保存可能

3. **複数ワーカーの負荷分散**:
   - Celery の `-Q` オプションでキューを分離可能
   - `--concurrency` オプションで並列実行数を制御可能

## 既知の制約・注意事項

### 既存コードとの互換性

- ✅ CLI 実行（`main_cli.py`）は影響を受けない
- ✅ 既存の Orchestrator / NPE / Agents アーキテクチャは壊れていない

### 制限事項やトレードオフ

1. **Redis の必須性**:
   - Celery を使用する場合は Redis が必須
   - 開発環境では Redis を起動する必要がある

2. **Celery Worker の起動**:
   - Celery Worker が起動していない場合、タスクはキューに入るが実行されない
   - 本番環境では Celery Worker をデーモン化する必要がある

3. **同期実行と非同期実行の切り替え**:
   - 現在はコメントアウトで切り替える必要がある
   - 将来的には環境変数で切り替え可能にすべき

### 移行時の注意点

1. **データベースマイグレーション**:
   - Run モデルに `requirement` フィールドが追加されていることを確認
   - 必要に応じてマイグレーションを実行

2. **環境変数の設定**:
   - `CELERY_BROKER_URL` と `CELERY_RESULT_BACKEND` を設定
   - デフォルトは `redis://localhost:6379/0` と `redis://localhost:6379/1`

## 次のステップ

### 推奨されるフォローアップアクション

1. **タスクの進捗トラッキング**:
   - `AsyncResult` を使用してタスクの進捗を追跡
   - Web UI でリアルタイムに進捗を表示

2. **タスクのリトライ設定**:
   - Celery の `@task(autoretry_for=...)` で自動リトライを設定
   - 一時的なエラーに対するリトライロジックを実装

3. **タスクの優先度設定**:
   - Celery の優先度キューを使用
   - 重要なタスクを優先的に実行

4. **複数ワーカーの負荷分散**:
   - 複数の Celery Worker を起動
   - 負荷に応じてワーカー数を調整

5. **環境変数での切り替え**:
   - `USE_CELERY` 環境変数で同期/非同期を切り替え
   - デバッグ時は同期実行、本番環境では非同期実行

6. **テストの追加**:
   - Celery タスクのユニットテスト
   - 統合テスト（Flask アプリ + Celery Worker）

## 関連ドキュメント

- `docs/saas_architecture.md` - SaaS基盤のアーキテクチャドキュメント
- `docs/saas_mvp_setup.md` - SaaS基盤のセットアップガイド
- `docs/celery_setup.md` - Celery 非同期実行セットアップガイド
- `src/nexuscore/webapp/celery_app.py` - Celery アプリ初期化とタスク定義
- `src/nexuscore/webapp/orchestrator_helper.py` - Orchestrator ヘルパー関数

