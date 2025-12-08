"""
FastAPI API Keys エンドポイントのテスト

CR-FASTAPI-020 で作成された /api/v1/api-keys エンドポイントのテスト。
"""
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from nexuscore.api.fastapi_app import app


@pytest.fixture
def client():
    """FastAPI TestClient のフィクスチャ"""
    return TestClient(app)


@pytest.fixture
def mock_api_key(monkeypatch):
    """API Key をモック"""
    api_key = "test-api-key-123"
    monkeypatch.setenv("NEXUSCORE_API_KEY", api_key)
    yield api_key
    monkeypatch.delenv("NEXUSCORE_API_KEY", raising=False)


@pytest.fixture
def mock_db_models():
    """データベースモデルをモック"""
    with patch("nexuscore.webapp.models.ApiKey") as mock_api_key_model, \
         patch("nexuscore.webapp.models.User") as mock_user, \
         patch("nexuscore.webapp.db") as mock_db:
        # 認証のモックを設定（get_current_user が動作するように）
        # get_current_user は ApiKey.query.filter_by().first().user.id を使用する
        mock_auth_user = MagicMock()
        mock_auth_user.id = 1  # 整数として設定
        mock_auth_user.github_login = "testuser"

        mock_api_key_obj = MagicMock()
        mock_api_key_obj.user = mock_auth_user
        mock_api_key_obj.user_id = 1

        # get_current_user が使用するパスをモック
        mock_api_key_model.hash_token.return_value = "hashed_test_api_key"
        mock_query_chain = MagicMock()
        mock_query_chain.filter_by.return_value.first.return_value = mock_api_key_obj
        mock_api_key_model.query = mock_query_chain

        yield {
            "ApiKey": mock_api_key_model,
            "User": mock_user,
            "db": mock_db,
        }


@pytest.fixture
def mock_authenticated_user():
    """認証済みユーザーをモック"""
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.github_login = "testuser"
    return mock_user


def test_issue_api_key_success(client: TestClient, mock_api_key, mock_db_models):
    """
    API Key 発行の正常系テスト
    """
    # 認証用のモックを設定（get_current_user 用）
    mock_auth_user = MagicMock()
    mock_auth_user.id = 1
    mock_auth_key_obj = MagicMock()
    mock_auth_key_obj.user = mock_auth_user
    mock_auth_key_obj.user_id = 1

    # ApiKey.query.filter_by().count() をモック
    mock_query = MagicMock()
    # get_current_user 用のクエリチェーン（認証確認用）
    mock_query.filter_by.return_value.first.return_value = mock_auth_key_obj
    # 発行数の確認用
    mock_query.filter_by.return_value.count.return_value = 0  # 既存キー数は0
    mock_query.filter_by.return_value.order_by.return_value.all.return_value = []
    mock_db_models["ApiKey"].query = mock_query
    mock_db_models["ApiKey"].hash_token.return_value = "hashed_test_api_key"

    # generate_token と hash_token をモック
    mock_db_models["ApiKey"].generate_token.return_value = "nexus_test_token_12345"
    mock_db_models["ApiKey"].hash_token.return_value = "hashed_token_12345"

    # 新しい ApiKey インスタンスを作成
    def create_api_key(**kwargs):
        api_key = MagicMock()
        api_key.id = 123
        api_key.name = kwargs.get("name", "Test Key")
        api_key.created_at = datetime(2025, 12, 8, 12, 34, 56)
        api_key.user_id = kwargs.get("user_id", 1)
        return api_key

    mock_db_models["ApiKey"].side_effect = create_api_key

    # db.session をモック
    mock_session = MagicMock()
    mock_db_models["db"].session = mock_session

    # リクエスト
    response = client.post(
        "/api/v1/api-keys",
        json={"name": "Test Key"},
        headers={"X-API-Key": mock_api_key},
    )

    # 検証
    assert response.status_code == 201
    data = response.json()
    assert "api_key" in data
    assert "token" in data
    assert data["api_key"]["id"] == 123
    assert data["api_key"]["name"] == "Test Key"
    assert data["token"] == "nexus_test_token_12345"


def test_issue_api_key_without_auth(client: TestClient):
    """
    API Key 発行の認証なしテスト（401）
    """
    response = client.post(
        "/api/v1/api-keys",
        json={"name": "Test Key"},
    )

    assert response.status_code == 422  # FastAPI のバリデーションエラー（ヘッダー欠如）


def test_issue_api_key_limit_exceeded(client: TestClient, mock_api_key, mock_db_models):
    """
    API Key 発行の上限超過テスト（403）
    """
    # 認証用のモックを設定（get_current_user 用）
    mock_auth_user = MagicMock()
    mock_auth_user.id = 1
    mock_auth_key_obj = MagicMock()
    mock_auth_key_obj.user = mock_auth_user
    mock_auth_key_obj.user_id = 1

    # モックの設定（既存キー数が上限に達している）
    mock_query = MagicMock()
    # get_current_user 用のクエリチェーン（認証確認用）
    mock_query.filter_by.return_value.first.return_value = mock_auth_key_obj
    # 発行数の確認用
    mock_query.filter_by.return_value.count.return_value = 5  # 上限に達している
    mock_db_models["ApiKey"].query = mock_query
    mock_db_models["ApiKey"].hash_token.return_value = "hashed_test_api_key"

    # リクエスト
    response = client.post(
        "/api/v1/api-keys",
        json={"name": "Test Key"},
        headers={"X-API-Key": mock_api_key},
    )

    # 検証
    assert response.status_code == 403
    data = response.json()
    # FastAPI の HTTPException は detail キーにエラー情報を入れる
    if "detail" in data and isinstance(data["detail"], dict) and "error" in data["detail"]:
        assert data["detail"]["error"]["code"] == "FORBIDDEN"
        assert "limit exceeded" in data["detail"]["error"]["message"].lower()
    else:
        # フォールバック: エラーメッセージに "limit" が含まれることを確認
        error_str = str(data).lower()
        assert "limit" in error_str or "forbidden" in error_str


def test_list_api_keys_success(client: TestClient, mock_api_key, mock_db_models):
    """
    API Key 一覧取得の正常系テスト
    """
    # 認証用のモックを設定（get_current_user 用）
    mock_auth_user = MagicMock()
    mock_auth_user.id = 1
    mock_auth_key_obj = MagicMock()
    mock_auth_key_obj.user = mock_auth_user
    mock_auth_key_obj.user_id = 1

    # モックの設定
    mock_api_key1 = MagicMock()
    mock_api_key1.id = 123
    mock_api_key1.name = "Key 1"
    mock_api_key1.created_at = datetime(2025, 12, 8, 12, 34, 56)

    mock_api_key2 = MagicMock()
    mock_api_key2.id = 124
    mock_api_key2.name = "Key 2"
    mock_api_key2.created_at = datetime(2025, 12, 9, 10, 20, 30)

    # ApiKey.query.filter_by().order_by().all() をモック
    mock_query = MagicMock()
    # get_current_user 用のクエリチェーン（認証確認用）
    mock_query.filter_by.return_value.first.return_value = mock_auth_key_obj
    # 一覧取得用
    mock_query.filter_by.return_value.order_by.return_value.all.return_value = [
        mock_api_key1,
        mock_api_key2,
    ]
    mock_db_models["ApiKey"].query = mock_query
    mock_db_models["ApiKey"].hash_token.return_value = "hashed_test_api_key"

    # リクエスト
    response = client.get(
        "/api/v1/api-keys",
        headers={"X-API-Key": mock_api_key},
    )

    # 検証
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) == 2
    assert data["items"][0]["id"] == 123
    assert data["items"][0]["name"] == "Key 1"
    assert data["items"][1]["id"] == 124
    assert data["items"][1]["name"] == "Key 2"
    # token が含まれていないことを確認
    assert "token" not in data["items"][0]
    assert "token" not in data["items"][1]


def test_list_api_keys_empty(client: TestClient, mock_api_key, mock_db_models):
    """
    API Key 一覧取得の空リストテスト
    """
    # 認証用のモックを設定（get_current_user 用）
    mock_auth_user = MagicMock()
    mock_auth_user.id = 1
    mock_auth_key_obj = MagicMock()
    mock_auth_key_obj.user = mock_auth_user
    mock_auth_key_obj.user_id = 1

    # モックの設定（空リスト）
    mock_query = MagicMock()
    # get_current_user 用のクエリチェーン（認証確認用）
    mock_query.filter_by.return_value.first.return_value = mock_auth_key_obj
    # 一覧取得用（空リスト）
    mock_query.filter_by.return_value.order_by.return_value.all.return_value = []
    mock_db_models["ApiKey"].query = mock_query
    mock_db_models["ApiKey"].hash_token.return_value = "hashed_test_api_key"

    # リクエスト
    response = client.get(
        "/api/v1/api-keys",
        headers={"X-API-Key": mock_api_key},
    )

    # 検証
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) == 0


def test_revoke_api_key_success(client: TestClient, mock_api_key, mock_db_models):
    """
    API Key 無効化の正常系テスト（204）
    """
    # 認証用のモックを設定（get_current_user 用）
    mock_auth_user = MagicMock()
    mock_auth_user.id = 1
    mock_auth_key_obj = MagicMock()
    mock_auth_key_obj.user = mock_auth_user
    mock_auth_key_obj.user_id = 1

    # モックの設定
    mock_api_key_obj = MagicMock()
    mock_api_key_obj.id = 123
    mock_api_key_obj.user_id = 1  # 現在のユーザーと同じ

    mock_query = MagicMock()
    # get_current_user 用のクエリチェーン（認証確認用）
    mock_query.filter_by.return_value.first.return_value = mock_auth_key_obj
    # 削除対象のキー取得用（同じクエリチェーンを使用）
    # 注意: filter_by(id=123) と filter_by(token_hash=...) は別の呼び出しなので、
    # 両方のパターンに対応する必要がある
    def filter_by_side_effect(**kwargs):
        if "token_hash" in kwargs:
            # 認証用
            return MagicMock(first=lambda: mock_auth_key_obj)
        elif "id" in kwargs:
            # 削除対象キー取得用
            return MagicMock(first=lambda: mock_api_key_obj)
        return MagicMock(first=lambda: None)

    mock_query.filter_by.side_effect = filter_by_side_effect
    mock_db_models["ApiKey"].query = mock_query
    mock_db_models["ApiKey"].hash_token.return_value = "hashed_test_api_key"

    # db.session をモック
    mock_session = MagicMock()
    mock_db_models["db"].session = mock_session

    # リクエスト
    response = client.delete(
        "/api/v1/api-keys/123",
        headers={"X-API-Key": mock_api_key},
    )

    # 検証
    assert response.status_code == 204
    # 204 No Content はボディがない
    assert response.content == b""


def test_revoke_api_key_not_found(client: TestClient, mock_api_key, mock_db_models):
    """
    API Key 無効化の存在しないキーテスト（404）
    """
    # 認証用のモックを設定（get_current_user 用）
    mock_auth_user = MagicMock()
    mock_auth_user.id = 1
    mock_auth_key_obj = MagicMock()
    mock_auth_key_obj.user = mock_auth_user
    mock_auth_key_obj.user_id = 1

    # モックの設定（キーが見つからない）
    mock_query = MagicMock()
    # get_current_user 用のクエリチェーン（認証確認用）
    # 削除対象のキー取得用（存在しない）
    def filter_by_side_effect(**kwargs):
        if "token_hash" in kwargs:
            # 認証用
            return MagicMock(first=lambda: mock_auth_key_obj)
        elif "id" in kwargs:
            # 削除対象キー取得用（存在しない）
            return MagicMock(first=lambda: None)
        return MagicMock(first=lambda: None)

    mock_query.filter_by.side_effect = filter_by_side_effect
    mock_db_models["ApiKey"].query = mock_query
    mock_db_models["ApiKey"].hash_token.return_value = "hashed_test_api_key"

    # リクエスト
    response = client.delete(
        "/api/v1/api-keys/999",
        headers={"X-API-Key": mock_api_key},
    )

    # 検証
    assert response.status_code == 404
    data = response.json()
    # FastAPI の HTTPException は detail キーにエラー情報を入れる
    if "detail" in data and isinstance(data["detail"], dict) and "error" in data["detail"]:
        assert data["detail"]["error"]["code"] == "NOT_FOUND"
    else:
        # フォールバック: エラーメッセージに "not found" が含まれることを確認
        error_str = str(data).lower()
        assert "not found" in error_str


def test_revoke_api_key_forbidden(client: TestClient, mock_api_key, mock_db_models):
    """
    API Key 無効化の他ユーザーのキーテスト（403）
    """
    # 認証用のモックを設定（get_current_user 用）
    mock_auth_user = MagicMock()
    mock_auth_user.id = 1
    mock_auth_key_obj = MagicMock()
    mock_auth_key_obj.user = mock_auth_user
    mock_auth_key_obj.user_id = 1

    # モックの設定（他ユーザーのキー）
    mock_api_key_obj = MagicMock()
    mock_api_key_obj.id = 123
    mock_api_key_obj.user_id = 999  # 現在のユーザー（1）とは異なる

    mock_query = MagicMock()
    # get_current_user 用のクエリチェーン（認証確認用）
    # 削除対象のキー取得用（他ユーザーのキー）
    def filter_by_side_effect(**kwargs):
        if "token_hash" in kwargs:
            # 認証用
            return MagicMock(first=lambda: mock_auth_key_obj)
        elif "id" in kwargs:
            # 削除対象キー取得用（他ユーザーのキー）
            return MagicMock(first=lambda: mock_api_key_obj)
        return MagicMock(first=lambda: None)

    mock_query.filter_by.side_effect = filter_by_side_effect
    mock_db_models["ApiKey"].query = mock_query
    mock_db_models["ApiKey"].hash_token.return_value = "hashed_test_api_key"

    # リクエスト
    response = client.delete(
        "/api/v1/api-keys/123",
        headers={"X-API-Key": mock_api_key},
    )

    # 検証
    assert response.status_code == 403
    data = response.json()
    # FastAPI の HTTPException は detail キーにエラー情報を入れる
    if "detail" in data and isinstance(data["detail"], dict) and "error" in data["detail"]:
        assert data["detail"]["error"]["code"] == "FORBIDDEN"
        assert "permission" in data["detail"]["error"]["message"].lower()
    else:
        # フォールバック: エラーメッセージに "permission" または "forbidden" が含まれることを確認
        error_str = str(data).lower()
        assert "permission" in error_str or "forbidden" in error_str


def test_issue_api_key_default_name(client: TestClient, mock_api_key, mock_db_models):
    """
    API Key 発行のデフォルト名テスト（name 未指定）
    """
    # 認証用のモックを設定（get_current_user 用）
    mock_auth_user = MagicMock()
    mock_auth_user.id = 1
    mock_auth_key_obj = MagicMock()
    mock_auth_key_obj.user = mock_auth_user
    mock_auth_key_obj.user_id = 1

    # モックの設定
    mock_query = MagicMock()
    # get_current_user 用のクエリチェーン（認証確認用）
    mock_query.filter_by.return_value.first.return_value = mock_auth_key_obj
    # 発行数の確認用
    mock_query.filter_by.return_value.count.return_value = 2  # 既存キー数は2
    mock_query.filter_by.return_value.order_by.return_value.all.return_value = []
    mock_db_models["ApiKey"].query = mock_query
    mock_db_models["ApiKey"].hash_token.return_value = "hashed_test_api_key"

    mock_db_models["ApiKey"].generate_token.return_value = "nexus_test_token_12345"
    mock_db_models["ApiKey"].hash_token.return_value = "hashed_token_12345"

    def create_api_key(**kwargs):
        api_key = MagicMock()
        api_key.id = 124
        api_key.name = kwargs.get("name", "API Key 3")  # デフォルト名
        api_key.created_at = datetime(2025, 12, 8, 12, 34, 56)
        api_key.user_id = kwargs.get("user_id", 1)
        return api_key

    mock_db_models["ApiKey"].side_effect = create_api_key

    # db.session をモック
    mock_session = MagicMock()
    mock_db_models["db"].session = mock_session

    # リクエスト（name を指定しない）
    response = client.post(
        "/api/v1/api-keys",
        json={},
        headers={"X-API-Key": mock_api_key},
    )

    # 検証
    assert response.status_code == 201
    data = response.json()
    assert data["api_key"]["name"] == "API Key 3"  # デフォルト名が付けられる

