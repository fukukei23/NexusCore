"""
api_keys.py 未カバー行のテスト (Issue #90)

対象:
- L51-53: _get_user_id_from_auth invalid user_id
- L151-154: issue_api_key SQLAlchemyError → rollback
- L160-161: issue_api_key unexpected non-HTTPException
- L218-227: list_api_keys SQLAlchemyError + unexpected Exception
- L291-294: revoke_api_key SQLAlchemyError → rollback
- L296-301: revoke_api_key unexpected non-HTTPException
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from nexuscore.api.fastapi_app import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_api_key(monkeypatch):
    api_key = "test-api-key-123"
    monkeypatch.setenv("NEXUSCORE_API_KEY", api_key)
    yield api_key
    monkeypatch.delenv("NEXUSCORE_API_KEY", raising=False)


def _make_auth_key_obj(user_id=1):
    """認証用モック ApiKey オブジェクト"""
    mock_auth_user = MagicMock()
    mock_auth_user.id = user_id
    mock_auth_user.github_login = "testuser"
    mock_key = MagicMock()
    mock_key.user = mock_auth_user
    mock_key.user_id = user_id
    return mock_key


def _make_query_with_auth(auth_key_obj, **overrides):
    """認証 + カスタムチェーン対応のモッククエリ"""
    mock_query = MagicMock()
    mock_query.filter_by.return_value.first.return_value = auth_key_obj
    for attr, val in overrides.items():
        obj = mock_query.filter_by.return_value
        for part in attr.split("."):
            obj = getattr(obj, part)
        # simplified: set return_value on chain
    return mock_query


# === L51-53: _get_user_id_from_auth with invalid user_id ===


def test_issue_api_key_invalid_user_id(client, mock_api_key):
    """user_id が非数値 → 500"""
    auth_key = _make_auth_key_obj()
    auth_key.user.id = "not_a_number"

    with (
        patch("nexuscore.webapp.models.ApiKey") as ApiKey,
        patch("nexuscore.webapp.models.User"),
        patch("nexuscore.webapp.db"),
    ):
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = auth_key
        ApiKey.query = mock_query
        ApiKey.hash_token.return_value = "hashed"

        resp = client.post(
            "/api/v1/api-keys",
            json={"name": "Bad"},
            headers={"X-API-Key": mock_api_key},
        )
    assert resp.status_code == 500


def test_list_api_keys_invalid_user_id(client, mock_api_key):
    """user_id が非数値 → 500 (list)"""
    auth_key = _make_auth_key_obj()
    auth_key.user.id = "not_a_number"

    with (
        patch("nexuscore.webapp.models.ApiKey") as ApiKey,
        patch("nexuscore.webapp.models.User"),
        patch("nexuscore.webapp.db"),
    ):
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = auth_key
        ApiKey.query = mock_query
        ApiKey.hash_token.return_value = "hashed"

        resp = client.get(
            "/api/v1/api-keys",
            headers={"X-API-Key": mock_api_key},
        )
    assert resp.status_code == 500


def test_revoke_api_key_invalid_user_id(client, mock_api_key):
    """user_id が非数値 → 500 (revoke)"""
    auth_key = _make_auth_key_obj()
    auth_key.user.id = "not_a_number"

    with (
        patch("nexuscore.webapp.models.ApiKey") as ApiKey,
        patch("nexuscore.webapp.models.User"),
        patch("nexuscore.webapp.db"),
    ):
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = auth_key
        ApiKey.query = mock_query
        ApiKey.hash_token.return_value = "hashed"

        resp = client.delete(
            "/api/v1/api-keys/1",
            headers={"X-API-Key": mock_api_key},
        )
    assert resp.status_code == 500


# === L151-154: issue_api_key SQLAlchemyError ===


def test_issue_api_key_sqlalchemy_error(client, mock_api_key):
    """SQLAlchemyError → rollback + 500"""
    auth_key = _make_auth_key_obj()

    with (
        patch("nexuscore.webapp.models.ApiKey") as ApiKey,
        patch("nexuscore.webapp.models.User"),
        patch("nexuscore.webapp.db") as mock_db,
    ):
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = auth_key
        mock_query.filter_by.return_value.count.return_value = 0
        ApiKey.query = mock_query
        ApiKey.generate_token.return_value = "tok"
        ApiKey.hash_token.return_value = "hash"

        # db.session.commit で SQLAlchemyError を発生させる
        mock_db.session.commit.side_effect = SQLAlchemyError("connection lost")

        resp = client.post(
            "/api/v1/api-keys",
            json={"name": "DB Error Key"},
            headers={"X-API-Key": mock_api_key},
        )
    assert resp.status_code == 500


# === L160-161: issue_api_key unexpected non-HTTPException ===


def test_issue_api_key_unexpected_exception(client, mock_api_key):
    """予期しない例外 → 500"""
    with (
        patch("nexuscore.webapp.models.ApiKey") as ApiKey,
        patch("nexuscore.webapp.models.User"),
        patch("nexuscore.webapp.db"),
    ):
        # import 時点で例外を発生させる
        ApiKey.generate_token.side_effect = RuntimeError("boom")

        auth_key = _make_auth_key_obj()
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = auth_key
        mock_query.filter_by.return_value.count.return_value = 0
        ApiKey.query = mock_query
        ApiKey.hash_token.return_value = "hash"

        resp = client.post(
            "/api/v1/api-keys",
            json={"name": "Runtime Key"},
            headers={"X-API-Key": mock_api_key},
        )
    assert resp.status_code == 500


# === L218-220: list_api_keys SQLAlchemyError ===


def test_list_api_keys_sqlalchemy_error(client, mock_api_key):
    """一覧取得時 SQLAlchemyError → 500"""
    auth_key = _make_auth_key_obj()

    with (
        patch("nexuscore.webapp.models.ApiKey") as ApiKey,
        patch("nexuscore.webapp.models.User"),
        patch("nexuscore.webapp.db"),
    ):
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = auth_key
        mock_query.filter_by.return_value.order_by.return_value.all.side_effect = SQLAlchemyError("read fail")
        ApiKey.query = mock_query
        ApiKey.hash_token.return_value = "hashed"

        resp = client.get(
            "/api/v1/api-keys",
            headers={"X-API-Key": mock_api_key},
        )
    assert resp.status_code == 500


# === L222-227: list_api_keys unexpected Exception ===


def test_list_api_keys_unexpected_exception(client, mock_api_key):
    """一覧取得時 予期しない例外 → 500"""
    auth_key = _make_auth_key_obj()

    with (
        patch("nexuscore.webapp.models.ApiKey") as ApiKey,
        patch("nexuscore.webapp.models.User"),
        patch("nexuscore.webapp.db"),
    ):
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = auth_key
        # created_at アクセスで AttributeError → Exception catch
        bad_key = MagicMock()
        bad_key.id = 1
        bad_key.name = "Broken"
        del bad_key.created_at
        mock_query.filter_by.return_value.order_by.return_value.all.return_value = [bad_key]
        ApiKey.query = mock_query
        ApiKey.hash_token.return_value = "hashed"

        resp = client.get(
            "/api/v1/api-keys",
            headers={"X-API-Key": mock_api_key},
        )
    assert resp.status_code == 500


# === L291-294: revoke_api_key SQLAlchemyError ===


def test_revoke_api_key_sqlalchemy_error(client, mock_api_key):
    """削除時 SQLAlchemyError → rollback + 500"""
    auth_key = _make_auth_key_obj()
    target_key = MagicMock()
    target_key.id = 99
    target_key.user_id = 1

    with (
        patch("nexuscore.webapp.models.ApiKey") as ApiKey,
        patch("nexuscore.webapp.models.User"),
        patch("nexuscore.webapp.db") as mock_db,
    ):
        mock_query = MagicMock()

        def filter_by_side_effect(**kwargs):
            if "token_hash" in kwargs:
                return MagicMock(first=lambda: auth_key)
            elif "id" in kwargs:
                return MagicMock(first=lambda: target_key)
            return MagicMock(first=lambda: None)

        mock_query.filter_by.side_effect = filter_by_side_effect
        ApiKey.query = mock_query
        ApiKey.hash_token.return_value = "hashed"

        mock_db.session.commit.side_effect = SQLAlchemyError("fk error")

        resp = client.delete(
            "/api/v1/api-keys/99",
            headers={"X-API-Key": mock_api_key},
        )
    assert resp.status_code == 500


# === L296-301: revoke_api_key unexpected non-HTTPException ===


def test_revoke_api_key_unexpected_exception(client, mock_api_key):
    """削除時 予期しない例外 → 500"""
    auth_key = _make_auth_key_obj()
    target_key = MagicMock()
    target_key.id = 99
    target_key.user_id = 1

    with (
        patch("nexuscore.webapp.models.ApiKey") as ApiKey,
        patch("nexuscore.webapp.models.User"),
        patch("nexuscore.webapp.db") as mock_db,
    ):
        mock_query = MagicMock()

        def filter_by_side_effect(**kwargs):
            if "token_hash" in kwargs:
                return MagicMock(first=lambda: auth_key)
            elif "id" in kwargs:
                return MagicMock(first=lambda: target_key)
            return MagicMock(first=lambda: None)

        mock_query.filter_by.side_effect = filter_by_side_effect
        ApiKey.query = mock_query
        ApiKey.hash_token.return_value = "hashed"

        mock_db.session.commit.side_effect = RuntimeError("unexpected")

        resp = client.delete(
            "/api/v1/api-keys/99",
            headers={"X-API-Key": mock_api_key},
        )
    assert resp.status_code == 500
