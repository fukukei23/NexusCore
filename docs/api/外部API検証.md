# 外部統合 API 動作確認手順

## 前提条件

1. データベースにユーザーが登録されていること
2. データベースにプロジェクトが登録されていること
3. Flask アプリが起動していること（またはテスト環境で実行）

## 1. モジュールのインポート確認

```bash
cd /home/yn441611/NexusCore
source myenv_linux/bin/activate

# インポート確認
python3 -c "
import sys
sys.path.insert(0, 'src')
from nexuscore.webapp.auth_api import api_key_required
from nexuscore.webapp.api_external import external_api_bp
print('✅ モジュールのインポート成功')
print(f'Blueprint URL prefix: {external_api_bp.url_prefix}')
"
```

## 2. Flask-CORS のインストール確認

```bash
pip list | grep -i flask-cors
# または
python3 -c "import flask_cors; print('✅ Flask-CORS インストール済み')"
```

未インストールの場合は：
```bash
pip install flask-cors
```

## 3. API キーの発行

```bash
# 利用可能なユーザーを確認（存在しないユーザー名を指定すると一覧が表示される）
python tools/generate_api_key.py --user nonexistent --name "Test"

# 実際のユーザーで API キーを発行
python tools/generate_api_key.py --user <your-github-login> --name "Test API Key"
```

出力例：
```
✅ API key generated successfully!

User: testuser (id: 1)
Key Name: Test API Key
Key ID: 1

⚠️  IMPORTANT: Save this API key now. It will not be shown again!

API Key: nexus_abc123def456...
```

## 4. テストの実行

```bash
# ユニットテストを実行
python -m pytest tests/webapp/test_external_api.py -v

# 詳細な出力が必要な場合
python -m pytest tests/webapp/test_external_api.py -v -s
```

## 5. 実際の API エンドポイントの動作確認

### 5-1. Flask アプリを起動

```bash
cd /home/yn441611/NexusCore
source myenv_linux/bin/activate

# Flask アプリを起動（別ターミナルで）
export FLASK_APP=src/nexuscore/webapp
export FLASK_ENV=development
flask run --host=0.0.0.0 --port=5000
```

### 5-2. API エンドポイントのテスト

**準備**: 上記で発行した API キーを `YOUR_API_KEY` に置き換えてください。

#### GET /api/v1/projects（プロジェクト一覧取得）

```bash
curl -v \
  -H "X-Api-Key: YOUR_API_KEY" \
  http://localhost:5000/api/v1/projects
```

**期待されるレスポンス**:
```json
{
  "projects": [
    {
      "id": 1,
      "name": "Test Project",
      "repo_url": "https://github.com/test/repo",
      "local_path": "/path/to/project",
      "created_at": "2025-01-01T00:00:00"
    }
  ]
}
```

#### POST /api/v1/projects/<id>/run（Run 発火）

```bash
curl -v -X POST \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "requirement": "Test self-healing run",
    "autonomy_level": 2,
    "fast_lane": true
  }' \
  http://localhost:5000/api/v1/projects/1/run
```

**期待されるレスポンス**:
```json
{
  "run_id": "abc123def456...",
  "project_id": 1,
  "status": "PENDING",
  "queue_mode": "async"
}
```

#### GET /api/v1/projects/<id>/runs/latest（最新 Run 取得）

```bash
curl -v \
  -H "X-Api-Key: YOUR_API_KEY" \
  http://localhost:5000/api/v1/projects/1/runs/latest
```

**期待されるレスポンス**:
```json
{
  "run": {
    "id": 123,
    "run_id": "abc123def456...",
    "status": "SUCCESS",
    "started_at": "2025-01-01T00:00:00",
    "finished_at": "2025-01-01T00:05:00"
  }
}
```

または Run が存在しない場合:
```json
{
  "run": null
}
```

### 5-3. エラーケースの確認

#### API キーなし

```bash
curl -v http://localhost:5000/api/v1/projects
```

**期待されるレスポンス**: 401 Unauthorized
```json
{
  "error": "Invalid or missing API key"
}
```

#### 無効な API キー

```bash
curl -v \
  -H "X-Api-Key: invalid-token" \
  http://localhost:5000/api/v1/projects
```

**期待されるレスポンス**: 401 Unauthorized

#### requirement 未指定

```bash
curl -v -X POST \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{}' \
  http://localhost:5000/api/v1/projects/1/run
```

**期待されるレスポンス**: 400 Bad Request
```json
{
  "error": "requirement is required"
}
```

#### 存在しないプロジェクト

```bash
curl -v \
  -H "X-Api-Key: YOUR_API_KEY" \
  http://localhost:5000/api/v1/projects/999/runs/latest
```

**期待されるレスポンス**: 404 Not Found
```json
{
  "error": "Project not found"
}
```

## 6. CORS の確認

ブラウザの開発者ツールで確認：

```javascript
// ブラウザのコンソールで実行
fetch('http://localhost:5000/api/v1/projects', {
  headers: {
    'X-Api-Key': 'YOUR_API_KEY'
  }
})
.then(r => r.json())
.then(console.log)
.catch(console.error)
```

**期待される動作**:
- CORS エラーが発生しない
- レスポンスが正常に取得できる

## 7. 確認チェックリスト

- [ ] モジュールのインポートが成功する
- [ ] Flask-CORS がインストールされている
- [ ] API キーが発行できる
- [ ] ユニットテストが全て通過する
- [ ] GET /api/v1/projects が動作する
- [ ] POST /api/v1/projects/<id>/run が動作する
- [ ] GET /api/v1/projects/<id>/runs/latest が動作する
- [ ] API キーなしで 401 が返る
- [ ] 無効な API キーで 401 が返る
- [ ] requirement 未指定で 400 が返る
- [ ] 存在しないプロジェクトで 404 が返る
- [ ] CORS が正しく設定されている

## トラブルシューティング

### インポートエラー

```
ModuleNotFoundError: No module named 'nexuscore'
```

**解決方法**:
```bash
export PYTHONPATH=/home/yn441611/NexusCore/src:$PYTHONPATH
```

### データベースエラー

```
sqlalchemy.exc.OperationalError: no such table: users
```

**解決方法**:
```bash
flask db upgrade
```

### CORS エラー

ブラウザで CORS エラーが発生する場合、Flask-CORS が正しく設定されているか確認：

```python
# src/nexuscore/webapp/__init__.py で確認
from flask_cors import CORS
CORS(app, resources={r"/api/v1/*": {"origins": "*"}})
```

