# Celery 非同期実行セットアップガイド

## 概要

NexusCore SaaS基盤では、長時間実行される Orchestrator タスクを Celery で非同期実行します。

## 前提条件

- Redis が起動していること（Celery のブローカー/バックエンドとして使用）
- Flask アプリケーションが正常に動作していること

## セットアップ手順

### 1. Redis のインストールと起動

#### Ubuntu/WSL

```bash
sudo apt-get update
sudo apt-get install redis-server

# Redis を起動
sudo systemctl start redis-server
# または
redis-server
```

#### macOS

```bash
brew install redis
brew services start redis
```

#### Windows

Redis for Windows をダウンロードしてインストール、または WSL を使用。

### 2. 依存パッケージのインストール

```bash
cd /home/yn441611/NexusCore
source myenv_linux/bin/activate
pip install celery redis
```

### 3. 環境変数の設定（オプション）

デフォルトでは `redis://localhost:6379/0` を使用しますが、環境変数で変更可能です：

```bash
export CELERY_BROKER_URL="redis://localhost:6379/0"
export CELERY_RESULT_BACKEND="redis://localhost:6379/1"
```

または `.env` ファイルに記載：

```
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

### 4. データベースマイグレーション

Run モデルに `requirement` フィールドを追加したので、マイグレーションを実行します：

```bash
cd /home/yn441611/NexusCore
source myenv_linux/bin/activate

# マイグレーションファイルを生成
flask db migrate -m "Add requirement field to Run model"

# マイグレーションを適用
flask db upgrade
```

### 5. Flask アプリケーションの起動

```bash
cd /home/yn441611/NexusCore
source myenv_linux/bin/activate

export FLASK_APP=nexuscore.webapp:create_app
export FLASK_ENV=development  # オプション
flask run
```

### 6. Celery Worker の起動

別のターミナルで Celery Worker を起動します：

```bash
cd /home/yn441611/NexusCore
source myenv_linux/bin/activate

celery -A nexuscore.webapp.celery_app.celery worker --loglevel=INFO
```

## 動作確認フロー

1. **GitHub OAuth でログイン**
   - `/auth/login/github` にアクセスしてログイン

2. **プロジェクト作成**
   - `/projects/new` からプロジェクトを作成
   - `local_path` に Orchestrator が動作するリポジトリパスを指定

3. **プロジェクト実行**
   - `/projects/<id>` で「実行」ボタンを押す
   - `requirement` パラメータを指定

4. **実行状態の確認**
   - プロジェクト詳細ページで Run 一覧を確認
   - ステータスが `PENDING` → `RUNNING` → `SUCCESS`/`FAILED` と変化することを確認

5. **ログの確認**
   - `/logs/projects/<id>` または `/logs/runs/<run_id>` でログを確認
   - NPE / ORCHESTRATOR / SANDBOX のログが見えることを確認

## Celery Worker のオプション

### キューの指定

```bash
celery -A nexuscore.webapp.celery_app.celery worker -Q nexuscore --loglevel=INFO
```

### 並列実行

```bash
celery -A nexuscore.webapp.celery_app.celery worker --concurrency=4 --loglevel=INFO
```

### デーモン化（本番環境）

```bash
celery -A nexuscore.webapp.celery_app.celery worker --detach --loglevel=INFO --logfile=/var/log/celery/worker.log
```

## トラブルシューティング

### Redis 接続エラー

```
ConnectionError: Error connecting to Redis
```

**解決方法**:
- Redis が起動しているか確認: `redis-cli ping` (応答: `PONG`)
- Redis のホストとポートを確認
- ファイアウォール設定を確認

### Celery Worker がタスクを受け取らない

**確認事項**:
- Celery Worker が正常に起動しているか
- Flask アプリと Celery Worker が同じ Redis インスタンスを使用しているか
- Celery Worker のログを確認

### タスクが失敗する

**確認事項**:
- Run レコードの `requirement` フィールドが設定されているか
- プロジェクトの `local_path` が正しいか
- Orchestrator の実行ログを確認

## 関連ファイル

- `src/nexuscore/webapp/celery_app.py` - Celery アプリ初期化とタスク定義
- `src/nexuscore/webapp/orchestrator_helper.py` - Orchestrator ヘルパー関数
- `src/nexuscore/webapp/views_projects.py` - プロジェクト実行エンドポイント
- `src/nexuscore/config/config.py` - Celery 設定（CELERY_BROKER_URL など）

## 次のステップ

- [ ] Celery Beat による定期実行タスクの追加
- [ ] タスクの進捗トラッキング（Celery の `AsyncResult` を使用）
- [ ] タスクのリトライ設定
- [ ] タスクの優先度設定
- [ ] 複数ワーカーの負荷分散

