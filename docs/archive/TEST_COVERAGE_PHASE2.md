# NexusCore フェーズ2: テストカバレッジ向上タスク仕様書

**作成日**: 2025-12-27
**対象**: Claude Code / Cursor AI
**推定工数**: 2週間（AI実行では 2-3時間）
**前提条件**: フェーズ1（セキュリティ修正）が完了していること

---

## 📋 概要

フェーズ1で修正したセキュリティ脆弱性に続き、フェーズ2では **テストカバレッジの向上** に焦点を当てます。

### 現状の問題

コードレビューで以下のモジュールが **カバレッジ 0%** であることが判明しました：

1. `src/nexuscore/npe/policies.py` - 機密情報検出・マスキング（セキュリティ重要）
2. `src/nexuscore/core/errors.py` - エラー分類システム（リトライ戦略の基盤）
3. `src/nexuscore/core/retry_utils.py` - 指数バックオフリトライ（LLM API呼び出しの信頼性）
4. `src/nexuscore/webapp/auth.py` - GitHub OAuth認証（SaaS基盤のセキュリティ）

これらは **ミッションクリティカル** なモジュールであり、テストなしでの運用はリスクが高いです。

### 目標

- 上記4モジュールのテストカバレッジを **80%以上** に引き上げる
- エッジケース・異常系を網羅した堅牢なテストスイートを構築
- CI/CD パイプラインでのカバレッジ計測を有効化

---

## 🎯 タスク一覧

| タスクID | 内容 | 優先度 | 推定時間 |
|---------|------|--------|---------|
| **Task 1** | NPE Policies テスト追加 | 🔴 CRITICAL | 30分 |
| **Task 2** | Error Classification テスト追加 | 🔴 CRITICAL | 30分 |
| **Task 3** | Retry Utils テスト追加 | 🟡 HIGH | 45分 |
| **Task 4** | OAuth Authentication テスト追加 | 🟡 HIGH | 45分 |
| **Task 5** | カバレッジレポート生成とCI連携 | 🟢 MEDIUM | 30分 |

---

## 📝 タスク詳細

---

### **Task 1: NPE Policies テスト追加**

**目的**: 機密情報検出・マスキング機能の正確性を保証する

**対象ファイル**: `src/nexuscore/npe/policies.py`

**テスト作成先**: `tests/npe/test_policies.py`

#### 実装すべきテスト

##### 1. `test_context_scanner_detects_aws_keys`
AWS アクセスキー（AKIA...、ASIA...）を正しく検出することを確認。

```python
def test_context_scanner_detects_aws_keys():
    """AWS アクセスキーを検出するテスト"""
    code_with_key = """
    AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"
    AWS_SECRET_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    """
    result = context_scanner(code_with_key)
    assert result == "sensitive"

    code_with_asia_key = "token = 'ASIATESTACCESSKEY123'"
    result = context_scanner(code_with_asia_key)
    assert result == "sensitive"
```

##### 2. `test_context_scanner_detects_pem_keys`
PEM形式の秘密鍵を検出する。

```python
def test_context_scanner_detects_pem_keys():
    """PEM秘密鍵を検出するテスト"""
    pem_key = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA0Z5V...
-----END RSA PRIVATE KEY-----"""
    result = context_scanner(pem_key)
    assert result == "sensitive"
```

##### 3. `test_context_scanner_safe_code`
安全なコードは 'safe' を返すことを確認。

```python
def test_context_scanner_safe_code():
    """安全なコードは 'safe' を返すテスト"""
    safe_code = """
def hello_world():
    print("Hello, NexusCore!")
    return 42
"""
    result = context_scanner(safe_code)
    assert result == "safe"
```

##### 4. `test_secure_context_builder_masks_aws_keys`
AWS キーが正しくマスキングされることを確認。

```python
def test_secure_context_builder_masks_aws_keys():
    """AWS キーをマスキングするテスト"""
    code = "AWS_KEY = 'AKIAIOSFODNN7EXAMPLE'"
    masked = secure_context_builder(code)
    assert "AKIAIOSFODNN7EXAMPLE" not in masked
    assert "[REDACTED_AWS_KEY_BY_NPE]" in masked
```

##### 5. `test_secure_context_builder_masks_env_vars`
環境変数形式の機密情報をマスキング。

```python
def test_secure_context_builder_masks_env_vars():
    """環境変数の機密情報をマスキングするテスト"""
    code = """
    API_KEY = "super-secret-key-123"
    PASSWORD = 'my-password'
    """
    masked = secure_context_builder(code)
    assert "super-secret-key-123" not in masked
    assert "my-password" not in masked
    assert "[REDACTED_BY_NPE]" in masked
```

##### 6. `test_secure_context_builder_masks_emails`
メールアドレスのマスキング。

```python
def test_secure_context_builder_masks_emails():
    """メールアドレスをマスキングするテスト"""
    code = "user_email = 'test@example.com'"
    masked = secure_context_builder(code)
    assert "example.com" not in masked
    assert "[REDACTED_DOMAIN]" in masked
```

#### 検証方法

```bash
# テスト実行
pytest tests/npe/test_policies.py -v

# カバレッジ確認
pytest tests/npe/test_policies.py --cov=src/nexuscore/npe/policies --cov-report=term-missing
```

**期待結果**: カバレッジ 85% 以上

---

### **Task 2: Error Classification テスト追加**

**目的**: エラー分類ロジックの正確性を保証する（リトライ戦略の基盤）

**対象ファイル**: `src/nexuscore/core/errors.py`

**テスト作成先**: `tests/core/test_errors.py`

#### 実装すべきテスト

##### 1. `test_classify_rate_limit_error`
レートリミットエラーの分類。

```python
from nexuscore.core.errors import classify_error, ModelRateLimitError

def test_classify_rate_limit_error():
    """レートリミットエラーの分類テスト"""
    # カスタム例外
    exc = ModelRateLimitError("Rate limit exceeded")
    assert classify_error(exc) == "rate_limit"

    # 一般的な例外（エラーメッセージから判定）
    exc = Exception("HTTP 429: rate limit exceeded")
    assert classify_error(exc) == "rate_limit"
```

##### 2. `test_classify_timeout_error`
タイムアウトエラーの分類。

```python
from nexuscore.core.errors import ModelTimeoutError

def test_classify_timeout_error():
    """タイムアウトエラーの分類テスト"""
    exc = ModelTimeoutError("Request timed out after 30s")
    assert classify_error(exc) == "timeout"

    exc = Exception("Connection timeout")
    assert classify_error(exc) == "timeout"
```

##### 3. `test_classify_connection_error`
接続エラーの分類。

```python
from nexuscore.core.errors import ModelConnectionError

def test_classify_connection_error():
    """接続エラーの分類テスト"""
    exc = ModelConnectionError("DNS resolution failed")
    assert classify_error(exc) == "connection"

    exc = Exception("Network unreachable")
    assert classify_error(exc) == "connection"
```

##### 4. `test_classify_invalid_output_error`
LLM出力形式エラーの分類。

```python
from nexuscore.core.errors import InvalidModelOutputError

def test_classify_invalid_output_error():
    """LLM出力エラーの分類テスト"""
    exc = InvalidModelOutputError("JSON parse failed")
    assert classify_error(exc) == "invalid_output"

    exc = Exception("Invalid JSON format: unexpected token")
    assert classify_error(exc) == "invalid_output"
```

##### 5. `test_classify_sandbox_error`
サンドボックス実行エラーの分類。

```python
from nexuscore.core.errors import SandboxExecutionError

def test_classify_sandbox_error():
    """サンドボックスエラーの分類テスト"""
    exc = SandboxExecutionError("Test execution failed")
    assert classify_error(exc) == "sandbox"

    exc = Exception("subprocess execution failed")
    assert classify_error(exc) == "sandbox"
```

##### 6. `test_classify_patch_apply_error`
パッチ適用エラーの分類。

```python
from nexuscore.core.errors import PatchApplyError

def test_classify_patch_apply_error():
    """パッチ適用エラーの分類テスト"""
    exc = PatchApplyError("Patch application failed")
    assert classify_error(exc) == "patch_apply"
```

##### 7. `test_classify_unexpected_error`
想定外エラーの分類。

```python
def test_classify_unexpected_error():
    """想定外エラーの分類テスト"""
    exc = ValueError("Some random error")
    assert classify_error(exc) == "unexpected"
```

##### 8. `test_convert_http_error_to_nexus_error`
HTTP エラーを NexusCore 例外に変換。

```python
from nexuscore.core.errors import convert_http_error_to_nexus_error, ModelRateLimitError

def test_convert_http_error_to_nexus_error():
    """HTTP エラーを NexusCore 例外に変換するテスト"""
    http_error = Exception("HTTP 429: Too Many Requests")
    nexus_error = convert_http_error_to_nexus_error(http_error)

    assert isinstance(nexus_error, ModelRateLimitError)
    assert "Rate limit error" in str(nexus_error)
```

#### 検証方法

```bash
pytest tests/core/test_errors.py -v
pytest tests/core/test_errors.py --cov=src/nexuscore/core/errors --cov-report=term-missing
```

**期待結果**: カバレッジ 90% 以上

---

### **Task 3: Retry Utils テスト追加**

**目的**: 指数バックオフリトライロジックの信頼性を保証する

**対象ファイル**: `src/nexuscore/core/retry_utils.py`

**テスト作成先**: `tests/core/test_retry_utils.py`

#### 実装すべきテスト

##### 1. `test_retry_success_on_first_attempt`
初回試行で成功する場合のテスト。

```python
from nexuscore.core.retry_utils import retry

def test_retry_success_on_first_attempt():
    """初回試行で成功する場合のテスト"""
    call_count = 0

    @retry(max_retries=2)
    def successful_function():
        nonlocal call_count
        call_count += 1
        return "success"

    result = successful_function()
    assert result == "success"
    assert call_count == 1  # 1回だけ呼ばれる
```

##### 2. `test_retry_success_after_failures`
失敗後に成功する場合のテスト。

```python
from nexuscore.core.errors import ModelTimeoutError

def test_retry_success_after_failures():
    """2回失敗後に成功するテスト"""
    call_count = 0

    @retry(max_retries=3, base_delay=0.1)
    def flaky_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ModelTimeoutError("Timeout on API call")
        return "success"

    result = flaky_function()
    assert result == "success"
    assert call_count == 3  # 3回目で成功
```

##### 3. `test_retry_exhausted`
最大リトライ回数を超えた場合のテスト。

```python
import pytest
from nexuscore.core.errors import ModelRateLimitError

def test_retry_exhausted():
    """最大リトライ回数を超えた場合のテスト"""
    call_count = 0

    @retry(max_retries=2, base_delay=0.1)
    def always_failing_function():
        nonlocal call_count
        call_count += 1
        raise ModelRateLimitError("Rate limit exceeded")

    with pytest.raises(ModelRateLimitError):
        always_failing_function()

    assert call_count == 3  # max_retries=2 なので計3回試行
```

##### 4. `test_retry_exponential_backoff`
指数バックオフの遅延が正しいことを確認。

```python
import time

def test_retry_exponential_backoff():
    """指数バックオフの遅延が正しいことを確認"""
    call_times = []

    @retry(max_retries=2, base_delay=0.5)
    def timed_function():
        call_times.append(time.time())
        raise ModelTimeoutError("Timeout")

    with pytest.raises(ModelTimeoutError):
        timed_function()

    # 遅延の確認（0.5s、1.0s の指数バックオフ）
    assert len(call_times) == 3
    delay_1 = call_times[1] - call_times[0]
    delay_2 = call_times[2] - call_times[1]

    assert 0.4 < delay_1 < 0.7  # 約0.5秒
    assert 0.9 < delay_2 < 1.3  # 約1.0秒
```

##### 5. `test_retry_context_tracks_attempts`
RetryContext が試行回数を正しく記録するテスト。

```python
from nexuscore.core.retry_utils import RetryContext, retry_with_context

def test_retry_context_tracks_attempts():
    """RetryContext が試行回数を追跡するテスト"""
    context = RetryContext()

    call_count = 0
    def flaky_func():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ModelTimeoutError("Timeout")
        return "success"

    wrapped = retry_with_context(flaky_func, max_retries=2, base_delay=0.1, context=context)
    result = wrapped()

    assert result == "success"
    assert context.retry_count == 1  # 1回リトライ（計2回試行）
    assert context.last_error_class == "timeout"
```

##### 6. `test_retry_does_not_retry_on_non_retryable_error`
リトライ対象外のエラーでは即座に失敗するテスト。

```python
def test_retry_does_not_retry_on_non_retryable_error():
    """リトライ対象外のエラーでは即座に失敗するテスト"""
    call_count = 0

    @retry(max_retries=3, base_delay=0.1)
    def non_retryable_error():
        nonlocal call_count
        call_count += 1
        raise ValueError("This is not a retryable error")

    with pytest.raises(ValueError):
        non_retryable_error()

    assert call_count == 1  # リトライせず即座に失敗
```

#### 検証方法

```bash
pytest tests/core/test_retry_utils.py -v
pytest tests/core/test_retry_utils.py --cov=src/nexuscore/core/retry_utils --cov-report=term-missing
```

**期待結果**: カバレッジ 80% 以上

---

### **Task 4: OAuth Authentication テスト追加**

**目的**: GitHub OAuth フローとセッション管理の正確性を保証する

**対象ファイル**: `src/nexuscore/webapp/auth.py`

**テスト作成先**: `tests/webapp/test_auth.py`

#### 実装すべきテスト

##### 1. `test_login_github_redirects_to_oauth`
GitHub OAuth へのリダイレクトを確認。

```python
import pytest
from nexuscore.webapp import create_app

@pytest.fixture
def client():
    """Flask テストクライアント"""
    app = create_app(testing=True)
    with app.test_client() as client:
        yield client

def test_login_github_redirects_to_oauth(client, monkeypatch):
    """GitHub OAuth へのリダイレクトを確認"""
    # GitHub OAuth 設定を環境変数でモック
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "test-client-secret")

    response = client.get("/auth/login/github")

    assert response.status_code in (302, 200)  # リダイレクトまたは成功
```

##### 2. `test_login_github_without_config`
OAuth 未設定時のエラーハンドリング。

```python
def test_login_github_without_config(client, monkeypatch):
    """OAuth 未設定時のエラーハンドリング"""
    # 環境変数をクリア
    monkeypatch.delenv("GITHUB_CLIENT_ID", raising=False)
    monkeypatch.delenv("GITHUB_CLIENT_SECRET", raising=False)

    response = client.get("/auth/login/github")

    assert response.status_code == 500
    data = response.get_json()
    assert "not configured" in data["error"]
```

##### 3. `test_github_callback_creates_new_user`
新規ユーザー作成のテスト（モック使用）。

```python
from unittest.mock import Mock, patch

def test_github_callback_creates_new_user(client, monkeypatch):
    """新規ユーザー作成のテスト"""
    # OAuth トークン取得をモック
    mock_token = {"access_token": "test-token"}

    # GitHub API レスポンスをモック
    mock_user_response = Mock()
    mock_user_response.status_code = 200
    mock_user_response.json.return_value = {
        "id": 12345,
        "login": "test-user",
        "name": "Test User",
        "avatar_url": "https://example.com/avatar.png"
    }

    mock_email_response = Mock()
    mock_email_response.status_code = 200
    mock_email_response.json.return_value = [
        {"email": "test@example.com", "primary": True, "verified": True}
    ]

    with patch("nexuscore.webapp.auth.oauth.github.authorize_access_token", return_value=mock_token):
        with patch("requests.get") as mock_requests:
            mock_requests.side_effect = [mock_user_response, mock_email_response]

            response = client.get("/auth/github/callback")

            # リダイレクトまたはセッション設定を確認
            assert response.status_code in (302, 200)
```

##### 4. `test_github_callback_updates_existing_user`
既存ユーザー更新のテスト。

```python
def test_github_callback_updates_existing_user(client):
    """既存ユーザー更新のテスト"""
    # 既存ユーザーをDBに作成
    from nexuscore.webapp.models import User
    from nexuscore.webapp import db

    existing_user = User(
        github_id="12345",
        github_login="old-login",
        name="Old Name"
    )
    db.session.add(existing_user)
    db.session.commit()

    # OAuth コールバックで情報が更新されることを確認
    # (モックを使用して実装)
```

##### 5. `test_logout_clears_session`
ログアウトがセッションをクリアすることを確認。

```python
def test_logout_clears_session(client):
    """ログアウトがセッションをクリアするテスト"""
    # セッションを設定
    with client.session_transaction() as sess:
        sess["user_id"] = 123
        sess["github_login"] = "test-user"

    response = client.get("/auth/logout")

    # セッションがクリアされることを確認
    with client.session_transaction() as sess:
        assert "user_id" not in sess
        assert "github_login" not in sess
```

##### 6. `test_get_current_user`
セッションからユーザー取得のテスト。

```python
def test_get_current_user(client):
    """セッションからユーザー取得のテスト"""
    from nexuscore.webapp.auth import get_current_user
    from nexuscore.webapp.models import User
    from nexuscore.webapp import db

    # テストユーザーを作成
    user = User(github_id="123", github_login="test-user")
    db.session.add(user)
    db.session.commit()

    # セッションに user_id を設定
    with client.session_transaction() as sess:
        sess["user_id"] = user.id

    # get_current_user() が正しくユーザーを返すことを確認
    with client.application.app_context():
        current_user = get_current_user()
        assert current_user is not None
        assert current_user.github_login == "test-user"
```

##### 7. `test_require_auth_decorator`
認証デコレータのテスト。

```python
def test_require_auth_decorator(client):
    """認証デコレータのテスト"""
    from nexuscore.webapp.auth import require_auth
    from flask import Flask

    # 保護されたエンドポイントを作成
    @require_auth
    def protected_view():
        return "Protected content"

    # 未認証でアクセス → リダイレクト
    response = client.get("/protected")
    assert response.status_code in (302, 401)
```

#### 検証方法

```bash
pytest tests/webapp/test_auth.py -v
pytest tests/webapp/test_auth.py --cov=src/nexuscore/webapp/auth --cov-report=term-missing
```

**期待結果**: カバレッジ 75% 以上（モックの制約により完全カバレッジは困難）

---

### **Task 5: カバレッジレポート生成とCI連携**

**目的**: フェーズ2の成果を可視化し、CI/CD パイプラインに統合する

#### 5.1 カバレッジレポート生成

```bash
# 全テスト実行 + カバレッジ計測
pytest tests/ \
  --cov=src/nexuscore/npe/policies \
  --cov=src/nexuscore/core/errors \
  --cov=src/nexuscore/core/retry_utils \
  --cov=src/nexuscore/webapp/auth \
  --cov-report=html \
  --cov-report=term-missing \
  --cov-report=xml

# HTML レポートを確認
open htmlcov/index.html
```

#### 5.2 `.coveragerc` 設定ファイル作成

```ini
# .coveragerc
[run]
source = src/nexuscore
omit =
    */tests/*
    */venv/*
    */__pycache__/*
    */migrations/*

[report]
precision = 2
show_missing = True
skip_covered = False

[html]
directory = htmlcov
```

#### 5.3 GitHub Actions ワークフロー更新

`.github/workflows/test.yml` に以下を追加：

```yaml
- name: Run tests with coverage
  run: |
    pytest tests/ \
      --cov=src/nexuscore \
      --cov-report=xml \
      --cov-report=term-missing

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
    flags: unittests
    fail_ci_if_error: true
```

#### 検証方法

```bash
# カバレッジレポートが生成されることを確認
ls -la htmlcov/
cat coverage.xml
```

**期待結果**:
- `htmlcov/index.html` が生成される
- `coverage.xml` が生成される
- 全体カバレッジが 70% 以上

---

## ✅ 完了条件

### 各タスクの完了条件

1. **Task 1**: `tests/npe/test_policies.py` が 6個以上のテストを含み、カバレッジ 85% 以上
2. **Task 2**: `tests/core/test_errors.py` が 8個以上のテストを含み、カバレッジ 90% 以上
3. **Task 3**: `tests/core/test_retry_utils.py` が 6個以上のテストを含み、カバレッジ 80% 以上
4. **Task 4**: `tests/webapp/test_auth.py` が 7個以上のテストを含み、カバレッジ 75% 以上
5. **Task 5**: カバレッジレポートが HTML/XML 形式で生成される

### 全体の完了条件

- [ ] すべてのテストが PASSED（失敗ゼロ）
- [ ] 対象4モジュールのカバレッジが平均 80% 以上
- [ ] カバレッジレポートが生成される
- [ ] コミット＆プッシュが完了

---

## 🚀 実行手順（Claude Code / Cursor）

### ステップ1: 環境確認

```bash
# 必要なパッケージがインストールされているか確認
pip list | grep -E "pytest|pytest-cov"

# なければインストール
pip install pytest pytest-cov pytest-mock
```

### ステップ2: タスク1〜4を順次実行

各タスクごとに：

1. テストファイルを作成
2. テストを実装
3. 実行して確認
4. カバレッジを確認

```bash
# 例: Task 1
pytest tests/npe/test_policies.py -v
pytest tests/npe/test_policies.py --cov=src/nexuscore/npe/policies --cov-report=term-missing
```

### ステップ3: 全体カバレッジ確認

```bash
pytest tests/ \
  --cov=src/nexuscore/npe/policies \
  --cov=src/nexuscore/core/errors \
  --cov=src/nexuscore/core/retry_utils \
  --cov=src/nexuscore/webapp/auth \
  --cov-report=html \
  --cov-report=term-missing
```

### ステップ4: コミット＆プッシュ

```bash
git add tests/ .coveragerc
git commit -m "test: Add comprehensive test coverage for critical modules (Phase 2)

- Add tests for NPE policies (sensitive data detection)
- Add tests for error classification system
- Add tests for retry utilities with exponential backoff
- Add tests for OAuth authentication flows
- Configure coverage reporting and CI integration

Coverage improvements:
- npe/policies.py: 0% → 85%
- core/errors.py: 0% → 90%
- core/retry_utils.py: 0% → 80%
- webapp/auth.py: 0% → 75%
"

git push origin claude/code-review-assessment-01PQXiLvM9oaUfBZaJfABDm6
```

---

## 📊 成功メトリクス

| メトリクス | 現状 | 目標 | 達成後 |
|----------|------|------|--------|
| `npe/policies.py` カバレッジ | 0% | 85% | ✅ |
| `core/errors.py` カバレッジ | 0% | 90% | ✅ |
| `core/retry_utils.py` カバレッジ | 0% | 80% | ✅ |
| `webapp/auth.py` カバレッジ | 0% | 75% | ✅ |
| テスト総数 | N個 | N+30個 | ✅ |
| 全体カバレッジ | 40-50% | 70%+ | ✅ |

---

## 🔍 注意事項

### モックの使用

OAuth テスト（Task 4）では外部 API 呼び出しをモックする必要があります：

- `oauth.github.authorize_access_token()` をモック
- `requests.get()` をモック（GitHub API）
- `db.session.commit()` が正しく呼ばれることを確認

### テスト実行時の環境変数

一部のテストは環境変数に依存します：

```bash
export GITHUB_CLIENT_ID="test-client-id"
export GITHUB_CLIENT_SECRET="test-secret"
export FLASK_ENV="testing"
```

### Fixture の共有

`tests/conftest.py` に共通の fixture を定義すると便利です：

```python
import pytest
from nexuscore.webapp import create_app, db

@pytest.fixture
def app():
    """Flask アプリケーション fixture"""
    app = create_app(testing=True)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """Flask テストクライアント"""
    return app.test_client()
```

---

## 📚 参考リンク

- [pytest 公式ドキュメント](https://docs.pytest.org/)
- [pytest-cov ガイド](https://pytest-cov.readthedocs.io/)
- [Flask Testing](https://flask.palletsprojects.com/en/2.3.x/testing/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)

---

**この仕様書に従って、フェーズ2のテストカバレッジ向上を完了させてください。**
