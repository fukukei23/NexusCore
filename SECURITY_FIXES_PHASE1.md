# フェーズ1: セキュリティ修正タスク指示書

**実行者**: Claude Code / AI Agent
**期限**: 1週間
**優先度**: 🔴 CRITICAL
**前提条件**: すべての変更後にテストを実行し、既存機能が壊れていないことを確認

---

## タスク1: コマンドインジェクション脆弱性の修正

### 📋 タスク概要
**タスクID**: SEC-FIX-001
**重要度**: 🔴 CRITICAL
**難易度**: ⭐☆☆☆☆（簡単）
**推定時間**: 15分

### 🎯 目的
`src/nexuscore/ui/unified_gradio_ui.py` の subprocess.run で shell=True を使用している箇所を修正し、コマンドインジェクション脆弱性（CVSS 9.8相当）を修正する。

### 📁 対象ファイル
- **修正**: `src/nexuscore/ui/unified_gradio_ui.py`

### 🔧 具体的な変更内容

#### Before（316-327行目付近）
```python
if test_file.strip():
    cmd = f"{command} {test_file}"  # ❌ 文字列結合
else:
    cmd = command

result = subprocess.run(
    cmd,
    shell=True,  # ❌ コマンドインジェクションの危険性
    capture_output=True,
    text=True,
    cwd=Path.cwd(),
)
```

#### After（期待される修正）
```python
# コマンドをリスト形式に変更
if test_file.strip():
    cmd_list = [command, test_file]
else:
    cmd_list = [command]

result = subprocess.run(
    cmd_list,  # ✅ リスト形式でコマンドを渡す
    shell=False,  # ✅ shell=False に変更
    capture_output=True,
    text=True,
    cwd=Path.cwd(),
)
```

### ✅ 検証基準
- [ ] `shell=True` が `shell=False` に変更されている
- [ ] コマンドが文字列からリスト形式に変更されている
- [ ] 既存の UI 機能が正常に動作する
- [ ] テストファイル名にスペースが含まれる場合も正しく動作する
- [ ] `grep -r "shell=True" src/nexuscore/ui/` の結果が0件

### 🧪 テスト方法
```bash
# 静的チェック
grep -r "shell=True" src/nexuscore/ui/unified_gradio_ui.py

# 期待結果: 0件（見つからない）

# ユニットテストがあれば実行
pytest tests/ui/ -v
```

### 📝 制約条件
- UI の動作を変更しない
- エラーメッセージは既存のまま維持
- 他のファイルに影響を与えない

### 🔗 参考資料
- [OWASP Command Injection](https://owasp.org/www-community/attacks/Command_Injection)
- Python subprocess ドキュメント: shell=False の使用推奨

---

## タスク2: API認証システムの実装

### 📋 タスク概要
**タスクID**: SEC-FIX-002
**重要度**: 🔴 CRITICAL
**難易度**: ⭐⭐⭐☆☆（中）
**推定時間**: 2-3時間

### 🎯 目的
`src/nexuscore/api/server.py` の `/api/v1/execute` エンドポイントに JWT認証を追加し、認証なしでの任意コード実行を防ぐ。

### 📁 対象ファイル
- **修正**: `src/nexuscore/api/server.py`
- **新規作成**: `src/nexuscore/api/auth.py`（認証ユーティリティ）
- **新規作成**: `tests/api/test_auth.py`（認証テスト）

### 🔧 具体的な変更内容

#### Step 1: 認証ユーティリティの作成

**新規ファイル**: `src/nexuscore/api/auth.py`
```python
"""
API認証ユーティリティ
"""
from functools import wraps
from flask import request, jsonify
import os
import jwt
from datetime import datetime, timedelta

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-in-production")
ALGORITHM = "HS256"

def require_auth(f):
    """
    API認証デコレータ

    使用方法:
        @app.route('/api/v1/secure-endpoint', methods=['POST'])
        @require_auth
        def secure_endpoint():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Authorization ヘッダーからトークンを取得
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return jsonify({"error": "Authorization header missing"}), 401

        # "Bearer <token>" 形式を想定
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return jsonify({"error": "Invalid authorization header format"}), 401

        token = parts[1]

        try:
            # トークンを検証
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            # デコードされたペイロードを request にアタッチ（必要に応じて）
            request.auth_payload = payload
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        return f(*args, **kwargs)

    return decorated_function


def generate_token(user_id: str, expires_in_hours: int = 24) -> str:
    """
    JWTトークンを生成する

    Args:
        user_id: ユーザーID
        expires_in_hours: トークンの有効期限（時間）

    Returns:
        JWT トークン文字列
    """
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=expires_in_hours),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
```

#### Step 2: server.py の修正

**修正箇所**: `src/nexuscore/api/server.py`

**Before（146-171行目付近）**
```python
@app.route('/api/v1/execute', methods=['POST'])
def execute_task():  # ❌ 認証なし
    data = request.json
    if not data or 'requirement' not in data or 'project_path' not in data:
        return jsonify({"error": "Missing required fields"}), 400

    # ... 処理継続
```

**After（期待される修正）**
```python
from nexuscore.api.auth import require_auth  # ✅ インポート追加

@app.route('/api/v1/execute', methods=['POST'])
@require_auth  # ✅ 認証デコレータを追加
def execute_task():
    data = request.json
    if not data or 'requirement' not in data or 'project_path' not in data:
        return jsonify({"error": "Missing required fields"}), 400

    # project_path の検証を追加
    project_path = os.path.abspath(data['project_path'])

    # ✅ パストラバーサル対策: 許可されたディレクトリ以下かチェック
    allowed_base = os.getenv("NEXUS_ALLOWED_PROJECT_BASE", "/workspace")
    if not project_path.startswith(os.path.abspath(allowed_base)):
        return jsonify({"error": "Project path not allowed"}), 403

    # ... 処理継続
```

#### Step 3: トークン生成エンドポイントの追加（開発用）

**追加箇所**: `src/nexuscore/api/server.py` の末尾

```python
# 開発用: トークン生成エンドポイント（本番では削除すべき）
@app.route('/api/v1/dev/generate-token', methods=['POST'])
def generate_dev_token():
    """開発用トークン生成（本番環境では無効化すること）"""
    if os.getenv("FLASK_ENV") == "production":
        return jsonify({"error": "Not available in production"}), 403

    from nexuscore.api.auth import generate_token
    data = request.json
    user_id = data.get('user_id', 'dev-user')
    token = generate_token(user_id)
    return jsonify({"token": token})
```

### ✅ 検証基準
- [ ] `/api/v1/execute` に認証なしでアクセスすると401エラーを返す
- [ ] 有効なトークンがあれば正常に動作する
- [ ] 無効なトークンは401エラーを返す
- [ ] 期限切れトークンは401エラーを返す
- [ ] パストラバーサル攻撃が防がれる（`../../etc/passwd` など）

### 🧪 テスト方法

**新規ファイル**: `tests/api/test_auth.py`
```python
"""API認証のテスト"""
import pytest
from src.nexuscore.api.auth import generate_token, require_auth
from flask import Flask, jsonify

def test_generate_token():
    """トークン生成のテスト"""
    token = generate_token("test-user")
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0

def test_require_auth_without_token(client):
    """認証なしアクセスのテスト"""
    response = client.post('/api/v1/execute', json={
        'requirement': 'test',
        'project_path': '/tmp/test'
    })
    assert response.status_code == 401
    assert 'Authorization header missing' in response.json['error']

def test_require_auth_with_valid_token(client):
    """有効なトークンでのアクセステスト"""
    token = generate_token("test-user")
    response = client.post('/api/v1/execute',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'requirement': 'test',
            'project_path': '/workspace/test'
        }
    )
    # 400エラーでも認証は通っている（他のバリデーションエラー）
    assert response.status_code != 401

def test_path_traversal_blocked(client):
    """パストラバーサル攻撃のテスト"""
    token = generate_token("test-user")
    response = client.post('/api/v1/execute',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'requirement': 'test',
            'project_path': '../../etc/passwd'
        }
    )
    assert response.status_code == 403
    assert 'not allowed' in response.json['error']
```

**実行コマンド**:
```bash
# PyJWT のインストール
pip install pyjwt

# requirements.txt に追加
echo "pyjwt>=2.8.0,<3.0.0" >> requirements.txt

# テスト実行
pytest tests/api/test_auth.py -v
```

### 📝 制約条件
- 既存の API レスポンス形式を変更しない
- 認証エラーは標準的な HTTP ステータスコード（401, 403）を使用
- トークンの有効期限は環境変数で設定可能にする

### ⚠️ 重要な注意事項
- **JWT_SECRET_KEY は本番環境で必ず変更すること**
- `/api/v1/dev/generate-token` は開発環境のみで有効化
- 本番環境では OAuth2 や外部認証サービスの使用を推奨

---

## タスク3: Kubernetes ConfigMap を Secret に変更

### 📋 タスク概要
**タスクID**: SEC-FIX-003
**重要度**: 🔴 HIGH
**難易度**: ⭐⭐☆☆☆（易）
**推定時間**: 30分

### 🎯 目的
`k8s/orchestrator-worker-deployment.yaml` の ConfigMap に平文で保存されているデータベースパスワードを Kubernetes Secret に変更し、機密情報を暗号化する。

### 📁 対象ファイル
- **修正**: `k8s/orchestrator-worker-deployment.yaml`
- **新規作成**: `k8s/nexuscore-secrets.yaml`

### 🔧 具体的な変更内容

#### Step 1: Secret 定義ファイルの作成

**新規ファイル**: `k8s/nexuscore-secrets.yaml`
```yaml
# ==============================================================================
# Kubernetes Secret for NexusCore
# ==============================================================================
# 使用方法:
#   1. この値を実際の本番環境の値に置き換える
#   2. kubectl apply -f k8s/nexuscore-secrets.yaml
#   3. kubectl get secret nexuscore-secrets で確認
#
# 注意:
#   - このファイルは .gitignore に追加すべき
#   - 本番環境では外部シークレット管理サービス（AWS Secrets Manager等）の使用を推奨
# ==============================================================================

apiVersion: v1
kind: Secret
metadata:
  name: nexuscore-secrets
  namespace: default  # 必要に応じて変更
type: Opaque
stringData:
  # データベース接続URI（平文で記述、k8sが自動的にbase64エンコード）
  database_uri: "postgresql://user:CHANGE_THIS_PASSWORD@postgres-service:5432/nexuscore"

  # Redis接続URL
  redis_url: "redis://redis-service:6379/0"

  # Celery Broker URL
  celery_broker_url: "redis://redis-service:6379/0"

  # Celery Result Backend URL
  celery_result_backend: "redis://redis-service:6379/1"

  # JWT Secret Key（APIトークン生成用）
  jwt_secret_key: "CHANGE_THIS_TO_RANDOM_STRING_IN_PRODUCTION"

---
# ==============================================================================
# Secret のテンプレート（本番環境用）
# ==============================================================================
# 本番環境では以下のコマンドで Secret を作成することを推奨:
#
# kubectl create secret generic nexuscore-secrets \
#   --from-literal=database_uri="postgresql://user:SECURE_PASSWORD@postgres:5432/nexuscore" \
#   --from-literal=redis_url="redis://redis:6379/0" \
#   --from-literal=celery_broker_url="redis://redis:6379/0" \
#   --from-literal=celery_result_backend="redis://redis:6379/1" \
#   --from-literal=jwt_secret_key="$(openssl rand -base64 32)"
# ==============================================================================
```

#### Step 2: Deployment の修正

**修正箇所**: `k8s/orchestrator-worker-deployment.yaml`

**Before（128-138行目付近）**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: nexuscore-config
data:
  celery_broker_url: "redis://redis-service:6379/0"
  celery_result_backend: "redis://redis-service:6379/1"
  database_uri: "postgresql://user:password@postgres-service:5432/nexuscore"  # ❌ 平文パスワード
  redis_url: "redis://redis-service:6379/0"
```

**After（期待される修正）**

**ConfigMap（機密情報以外）を残す**:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: nexuscore-config
data:
  # 機密情報ではない設定のみ ConfigMap に残す
  log_level: "INFO"
  worker_concurrency: "4"
  max_tasks_per_child: "100"
```

**Deployment の env セクションを修正**:
```yaml
# Before
env:
- name: CELERY_BROKER_URL
  valueFrom:
    configMapKeyRef:  # ❌ ConfigMap から取得
      name: nexuscore-config
      key: celery_broker_url

# After
env:
- name: CELERY_BROKER_URL
  valueFrom:
    secretKeyRef:  # ✅ Secret から取得
      name: nexuscore-secrets
      key: celery_broker_url
- name: CELERY_RESULT_BACKEND
  valueFrom:
    secretKeyRef:
      name: nexuscore-secrets
      key: celery_result_backend
- name: DATABASE_URI
  valueFrom:
    secretKeyRef:
      name: nexuscore-secrets
      key: database_uri
- name: REDIS_URL
  valueFrom:
    secretKeyRef:
      name: nexuscore-secrets
      key: redis_url
- name: JWT_SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: nexuscore-secrets
      key: jwt_secret_key
```

#### Step 3: .gitignore の更新

**追加箇所**: `.gitignore`
```
# Kubernetes Secrets（機密情報を含むため除外）
k8s/nexuscore-secrets.yaml
k8s/*-secrets.yaml
k8s/*.secret.yaml
```

### ✅ 検証基準
- [ ] `k8s/nexuscore-secrets.yaml` が作成されている
- [ ] Deployment が Secret を参照している
- [ ] ConfigMap に機密情報が残っていない
- [ ] `kubectl apply -f k8s/nexuscore-secrets.yaml` が成功する
- [ ] `kubectl apply -f k8s/orchestrator-worker-deployment.yaml` が成功する
- [ ] Pod が正常に起動する

### 🧪 テスト方法
```bash
# Secret の作成
kubectl apply -f k8s/nexuscore-secrets.yaml

# Secret の確認
kubectl get secret nexuscore-secrets
kubectl describe secret nexuscore-secrets

# Deployment の適用
kubectl apply -f k8s/orchestrator-worker-deployment.yaml

# Pod の起動確認
kubectl get pods -l app=orchestrator-worker

# Pod 内の環境変数確認（機密情報が正しく設定されているか）
kubectl exec -it <pod-name> -- env | grep DATABASE_URI
```

### 📝 制約条件
- Secret は base64 エンコードされるが、暗号化はされない（etcd レベルでの暗号化が必要）
- Secret へのアクセス権限は RBAC で制御する
- 本番環境では外部シークレット管理サービスの使用を推奨

### 🔗 参考資料
- [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Secret の暗号化](https://kubernetes.io/docs/tasks/administer-cluster/encrypt-data/)

---

## タスク4: 依存関係のバージョン固定

### 📋 タスク概要
**タスクID**: SEC-FIX-004
**重要度**: 🔴 HIGH
**難易度**: ⭐☆☆☆☆（簡単）
**推定時間**: 15分

### 🎯 目的
`requirements.txt` の主要パッケージにバージョン制約を追加し、上流の破壊的変更によるシステム停止を防ぐ。

### 📁 対象ファイル
- **修正**: `requirements.txt`

### 🔧 具体的な変更内容

#### Before（現在の requirements.txt）
```txt
# --- Core AI and Machine Learning ---
openai          # ❌ バージョン指定なし
tensorflow      # ❌ バージョン指定なし
google-generativeai  # ❌ バージョン指定なし
torch==2.2.2+cpu     # ✅ 唯一のピン留め
scipy

# --- Web UI and Server ---
gradio          # ❌ バージョン指定なし
fastapi         # ❌ バージョン指定なし
uvicorn
streamlit

# --- Testing Framework ---
pytest
pytest-cov

# ... 以下省略
```

#### After（期待される修正）
```txt
# ===================================================
# Python Package Requirements for NexusCore
# バージョン制約の方針:
#   - メジャーバージョン: 破壊的変更を防ぐため上限を設定
#   - マイナーバージョン: セキュリティ修正を受けられるよう下限のみ
# ===================================================

# --- Core AI and Machine Learning ---
openai>=1.30.0,<2.0.0  # v1 API互換、v2は破壊的変更あり
--extra-index-url https://download.pytorch.org/whl/cpu
torch==2.2.2+cpu  # 既存のまま
tensorflow>=2.14.0,<3.0.0  # TF 3.0は破壊的変更の可能性
google-generativeai>=0.4.0,<1.0.0  # Gemini API
scipy>=1.11.0,<2.0.0

# --- Web UI and Server ---
gradio>=4.16.0,<5.0.0  # v4系で安定
fastapi>=0.104.0,<1.0.0
uvicorn>=0.24.0,<1.0.0
websockets>=12.0,<13.0
streamlit>=1.29.0,<2.0.0
Flask>=3.0.0,<4.0.0
Flask-SQLAlchemy>=3.1.0,<4.0.0
Flask-Migrate>=4.0.0,<5.0.0
Flask-CORS>=4.0.0,<5.0.0
authlib>=1.3.0,<2.0.0
celery>=5.3.0,<6.0.0
redis>=5.0.0,<6.0.0
matplotlib>=3.8.0,<4.0.0

# --- Audio Processing ---
SpeechRecognition>=3.10.0,<4.0.0
pydub>=0.25.0,<1.0.0
sounddevice>=0.4.6,<1.0.0
standard-aifc; python_version < '3.13'
patch>=1.16,<2.0  # patch_applier で使用

# --- Translation ---
google-cloud-translate>=3.15.0,<4.0.0

# --- Utilities ---
httpx>=0.25.0,<1.0.0
httpcore>=1.0.0,<2.0.0
requests>=2.31.0,<3.0.0  # Slack notifications
python-dotenv>=1.0.0,<2.0.0
termcolor>=2.4.0,<3.0.0
pyyaml>=6.0.0,<7.0.0  # test strategy config

# --- Testing Framework ---
pytest>=7.4.0,<8.0.0
pytest-cov>=4.1.0,<5.0.0
pytest-anyio>=0.0.0,<1.0.0
pytest-mock>=3.12.0,<4.0.0

# --- Authentication (新規追加) ---
pyjwt>=2.8.0,<3.0.0  # JWT認証用
```

### ✅ 検証基準
- [ ] すべての主要パッケージにバージョン制約がある
- [ ] `pip install -r requirements.txt` が成功する
- [ ] 既存のテストがすべて通る
- [ ] LLM統合（OpenAI、Gemini等）が正常に動作する
- [ ] Gradio UI が正常に起動する

### 🧪 テスト方法
```bash
# 仮想環境を作成（クリーンな状態でテスト）
python -m venv .venv-test
source .venv-test/bin/activate  # Windows: .venv-test\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt

# バージョン確認
pip list | grep -E "(openai|tensorflow|google-generativeai|gradio)"

# 期待される出力例:
# openai        1.30.1
# tensorflow    2.15.0
# google-generativeai  0.4.1
# gradio        4.16.2

# テスト実行
PYTHONPATH=src pytest tests/ -v

# LLM統合テスト（環境変数が設定されている場合）
PYTHONPATH=src pytest tests/llm/ -v

# クリーンアップ
deactivate
rm -rf .venv-test
```

### 📝 制約条件
- 現在動作しているバージョンと互換性を保つ
- セキュリティ修正を受けられるよう、マイナーバージョンには幅を持たせる
- 破壊的変更を防ぐため、メジャーバージョンの上限を設定

### 🔗 参考資料
- [Semantic Versioning](https://semver.org/)
- [pip requirements file format](https://pip.pypa.io/en/stable/reference/requirements-file-format/)

---

## 📊 全体の実行順序

### 推奨実行順序
1. **タスク4** → 依存関係固定（最も安全、影響範囲小）
2. **タスク1** → コマンドインジェクション修正（単純、リスク低）
3. **タスク3** → K8s Secret化（独立、他に影響なし）
4. **タスク2** → API認証追加（最も複雑、最後に実施）

### 各タスク完了後のチェックリスト
- [ ] 変更をコミット
- [ ] テストを実行
- [ ] セキュリティスキャン実施（可能であれば）
- [ ] 変更内容をレビュー
- [ ] 次のタスクに進む

---

## 🚀 実行開始コマンド

### タスク4から開始（推奨）
```bash
# 1. ブランチ作成
git checkout -b security/fix-dependencies

# 2. requirements.txt を編集（上記のAfterの内容に置き換え）

# 3. テスト
python -m venv .venv-test
source .venv-test/bin/activate
pip install -r requirements.txt
PYTHONPATH=src pytest tests/ -v
deactivate

# 4. コミット
git add requirements.txt
git commit -m "security: Pin dependency versions to prevent breaking changes"
git push -u origin security/fix-dependencies
```

---

## ✅ 完了条件

### フェーズ1全体の完了条件
- [ ] タスク1-4がすべて完了
- [ ] すべてのテストが通る
- [ ] セキュリティスキャンで新しい脆弱性が検出されない
- [ ] 変更がリモートブランチにプッシュされている
- [ ] プルリクエストが作成されている

### 期待される成果
- 🔒 コマンドインジェクション脆弱性の完全な除去
- 🔒 認証なしAPI実行の防止
- 🔒 機密情報の暗号化（K8s Secret化）
- 🔒 依存関係の破壊的変更からの保護

---

**最終確認日**: 2025-12-02
**作成者**: Claude Code Review Team
**次回レビュー**: フェーズ1完了後
