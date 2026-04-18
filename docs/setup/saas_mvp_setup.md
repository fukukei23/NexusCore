# NexusCore SaaS基盤 MVP - セットアップガイド

## 概要

NexusCore SaaS基盤のMVP（最小実装）をセットアップする手順です。

既存の Orchestrator / NPE / Agents アーキテクチャは壊さずに、
Web UI と API を提供するための Flask アプリケーションを追加しました。

## 前提条件

- Python 3.12+
- 既存の NexusCore プロジェクトが動作していること
- GitHub OAuth アプリケーション（認証用）

## セットアップ手順

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

新しく追加された依存関係：
- Flask-SQLAlchemy
- Flask-Migrate
- authlib

### 2. 環境変数の設定

`.env` ファイルに以下を追加：

```bash
# Flask設定
FLASK_SECRET_KEY=your-secret-key-here
DATABASE_URI=sqlite:///db.sqlite3

# GitHub OAuth設定
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
GITHUB_REDIRECT_URI=http://localhost:5000/auth/github/callback

# Celery 設定（オプション、デフォルト値あり）
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
NEXUS_USE_CELERY=1  # 1=非同期（Celery）、0=同期実行（デバッグ用）
```

**環境変数の説明**:
- `CELERY_BROKER_URL`: Celery のブローカーURL（デフォルト: `redis://localhost:6379/0`）
- `CELERY_RESULT_BACKEND`: Celery の結果バックエンドURL（デフォルト: `redis://localhost:6379/1`）
- `NEXUS_USE_CELERY`: 同期/非同期の切り替え（デフォルト: `1`=非同期）
  - `1`: Celery で非同期実行（本番環境推奨）
  - `0`: 同期実行（デバッグ用、トレースしやすい）

### 3. データベースの初期化

```bash
# Flaskアプリケーションコンテキストで実行
python -c "
from nexuscore.webapp import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
    print('Database initialized successfully')
"
```

または、Flask-Migrate を使用：

```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 4. Redis の起動（Celery 用）

Celery を使用する場合は、Redis を起動する必要があります：

```bash
# Redis を起動（WSL/Linux の場合）
redis-server

# または、Docker を使用する場合
docker run -d -p 6379:6379 redis:latest
```

環境変数で Celery のブローカー/バックエンドを設定：

```bash
export CELERY_BROKER_URL="redis://localhost:6379/0"
export CELERY_RESULT_BACKEND="redis://localhost:6379/1"
```

### 5. アプリケーションの起動

#### 5-1. Flask アプリケーションの起動

```bash
# Flaskアプリケーションを起動
python -c "
from nexuscore.webapp import create_app
app = create_app()
app.run(host='0.0.0.0', port=5000, debug=True)
"
```

または、`run_webapp.py` スクリプトを作成：

```python
# run_webapp.py
from nexuscore.webapp import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
```

#### 5-2. Celery Worker の起動（非同期実行用）

別のターミナルで Celery Worker を起動します：

```bash
# Celery Worker を起動
celery -A nexuscore.webapp.celery_app.celery worker --loglevel=INFO
```

または、環境変数を使用：

```bash
export FLASK_APP=nexuscore.webapp:create_app
celery -A nexuscore.webapp.celery_app.celery worker --loglevel=INFO
```

**注意**: Celery Worker は Flask アプリケーションとは別プロセスで実行されます。

### 6. Gradioダッシュボードの起動（オプション）

```bash
python -m nexuscore.ui.nexus_dashboard --project_id 1 --project_path /path/to/project
```

または、Pythonコードから：

```python
from nexuscore.ui.nexus_dashboard import launch_dashboard

launch_dashboard(project_id=1, project_path="/path/to/project", server_port=7860)
```

## 使用方法

### 1. GitHub OAuth ログイン

1. ブラウザで `http://localhost:5000/auth/login/github` にアクセス
2. GitHub で認証
3. 認証後、プロジェクト一覧ページにリダイレクト

### 2. プロジェクトの作成

1. `/projects/new` にアクセス
2. プロジェクト名、リポジトリURL、ローカルパスを入力
3. 「Create」ボタンをクリック

### 3. プロジェクトの実行

1. プロジェクト詳細ページから「Run」ボタンをクリック
2. 要件（requirement）を入力
3. 実行が開始される（Celery 非同期実行）

**注意**: Celery Worker が起動していない場合、タスクはキューに入りますが実行されません。
Worker を起動すると、キューに入ったタスクが順次実行されます。

### 4. ログの確認

1. `/logs/projects/<project_id>` でプロジェクト単位のログを確認
2. `/logs/runs/<run_id>` で特定のRunのログを確認
3. ソース（NPE / Orchestrator / Agent）やレベル（INFO / WARNING / ERROR）でフィルタ可能

### 5. ダッシュボードの確認

1. `/dashboard/` で統計情報を確認
2. `/dashboard/gradio/<project_id>` でGradioダッシュボードを確認

## API エンドポイント

### 認証

- `GET /auth/login/github` - GitHub OAuth ログイン開始
- `GET /auth/github/callback` - GitHub OAuth コールバック
- `GET /auth/logout` - ログアウト

### プロジェクト管理

- `GET /projects/` - プロジェクト一覧
- `GET /projects/<project_id>` - プロジェクト詳細
- `GET /projects/new` - 新規プロジェクト作成フォーム
- `POST /projects/new` - 新規プロジェクト作成
- `POST /projects/<project_id>/run` - プロジェクト実行トリガー

### ログビューア

- `GET /logs/projects/<project_id>` - プロジェクト単位のログ一覧
- `GET /logs/runs/<run_id>` - 特定のRunのログ一覧

### ダッシュボード

- `GET /dashboard/` - ダッシュボード
- `GET /dashboard/gradio/<project_id>` - Gradioダッシュボード（iframe）

## 既存コードとの統合

### NPE ログのDB書き込み

既存の `log_transaction` 関数は自動的にDBにも書き込むよう拡張されています。
Flaskアプリコンテキストが存在する場合のみDBに書き込むため、
既存のCLI実行は影響を受けません。

### Orchestrator ログのDB書き込み

`nexuscore.core.orchestrator_db_hook.log_orchestrator_event` を使用して、
Orchestrator のイベントをDBに記録できます。

例：

```python
from nexuscore.core.orchestrator_db_hook import log_orchestrator_event

log_orchestrator_event(
    phase="Requirement",
    level="INFO",
    message="Requirement analysis completed",
    payload_json={"task_id": "123", "specs": ["spec1", "spec2"]},
    run_id=run_id,
)
```

## トラブルシューティング

### データベースエラー

- SQLiteファイルのパーミッションを確認
- `db.sqlite3` ファイルが存在するか確認

### OAuth エラー

- GitHub OAuth アプリケーションの設定を確認
- `GITHUB_CLIENT_ID` と `GITHUB_CLIENT_SECRET` が正しく設定されているか確認
- `GITHUB_REDIRECT_URI` が GitHub OAuth アプリケーションの設定と一致しているか確認

### ログがDBに書き込まれない

- Flaskアプリコンテキストが存在するか確認
- `ExecutionLog` テーブルが作成されているか確認

## Celery 非同期実行の詳細

詳細は `docs/celery_setup.md` を参照してください。

### 実運用環境での起動方法

#### Docker Compose を使用する場合

```bash
# docker-compose.saas.yml を使用
docker-compose -f docker-compose.saas.yml up -d
```

これにより、以下が自動的に起動します：
- Redis（Celery ブローカー/バックエンド）
- Flask Web アプリケーション（Gunicorn）
- Celery Worker
- PostgreSQL（オプション）

#### systemd を使用する場合

```bash
# サービスファイルを配置
sudo cp docs/saas_celery_systemd.service /etc/systemd/system/nexuscore-celery.service

# サービスを有効化・起動
sudo systemctl daemon-reload
sudo systemctl enable nexuscore-celery
sudo systemctl start nexuscore-celery

# ログ確認
sudo journalctl -u nexuscore-celery -f
```

#### supervisor を使用する場合

```bash
# 設定ファイルを配置
sudo cp docs/saas_celery_supervisor.conf /etc/supervisor/conf.d/nexuscore-celery.conf

# サービスを有効化・起動
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start nexuscore-celery:*

# ログ確認
sudo tail -f /var/log/nexuscore/celery-worker.log
```

### 基本的な起動手順

1. **Redis を起動**:
   ```bash
   redis-server
   ```

2. **Flask アプリケーションを起動**:
   ```bash
   python -c "from nexuscore.webapp import create_app; app = create_app(); app.run(host='0.0.0.0', port=5000, debug=True)"
   ```

3. **Celery Worker を起動**（別ターミナル）:
   ```bash
   celery -A nexuscore.webapp.celery_app.celery worker --loglevel=INFO
   ```

### タスクの実行フロー

1. ユーザーが `/projects/<project_id>/run` に POST リクエストを送信
2. Run レコードが作成され、ステータスが `PENDING` に設定
3. Celery タスク `nexuscore.run_orchestrator` がキューに入る
4. Celery Worker がタスクを受け取り、実行開始
5. Run ステータスが `RUNNING` → `SUCCESS` / `FAILED` に更新
6. 実行ログが `ExecutionLog` テーブルに記録される

## 次のステップ

- [ ] テンプレートエンジン（Jinja2）を使用したHTMLレンダリング
- [ ] APIキー管理UIの実装
- [x] Celery を使用した非同期タスク実行（実装完了）
- [ ] パッチ適用前プレビュー機能の完全実装
- [ ] テストの追加

