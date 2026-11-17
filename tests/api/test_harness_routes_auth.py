"""/harness/* の認証付与テスト（2026-11-17・Strix診断A案③）

Strix診断（nexuscore_bfa5）で「`GET /harness/`・`POST /harness/run` が
FastAPI app に認証なしで載っている（認証依存が一切ない）」と指摘（high / 8.2）。

実測（2026-11-17・CC突合）:
- `src/nexuscore/api/harness_routes.py:77,86` に認証依存なし
- `fastapi_app.py:42` で `app.include_router(harness_router)`（prefix なしで公開）
- read_file は policy で default: allow のため .env 等を読める
- ただし `build_registry(ask=False)` は読む系3ツールのみ（exec/write 未登録）で
  RCE 自体は不成立（Strix の RCE 主張は誇張）

本テストは /harness/* が API Key 認証を要求することを保証する。
認証は既存APIルートと同じ `get_current_user`（X-API-Key ヘッダー）方式。
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from nexuscore.api.fastapi_app import create_app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture()
def mock_api_key(monkeypatch: pytest.MonkeyPatch):
    """API Key をモック（既存 tests/api/test_fastapi_projects.py と同方式）"""
    api_key = "test-api-key-123"
    monkeypatch.setenv("NEXUSCORE_API_KEY", api_key)
    return api_key


def _make_auth_key_obj(user_id: int = 1):
    """認証用モック ApiKey オブジェクト（tests/api/test_api_keys_coverage.py と同方式）"""
    mock_auth_user = MagicMock()
    mock_auth_user.id = user_id
    mock_auth_user.github_login = "testuser"
    mock_key = MagicMock()
    mock_key.user = mock_auth_user
    mock_key.user_id = user_id
    return mock_key


def _patch_auth(auth_key_obj, valid_key: str):
    """ApiKey/User の DB 解決をモック化する（patcher を返す）

    `filter_by(token_hash=...)` は渡されたハッシュが `valid_key` のハッシュと
    一致する時だけオブジェクトを返す（=実際の照合と同じ挙動）。
    """
    valid_hash = "hash-of-valid-key"

    def _filter_by(token_hash=None, **_kwargs):
        chain = MagicMock()
        chain.first.return_value = auth_key_obj if token_hash == valid_hash else None
        return chain

    mock_query = MagicMock()
    mock_query.filter_by.side_effect = _filter_by
    api_key_patcher = patch("nexuscore.models.ApiKey")
    user_patcher = patch("nexuscore.models.User")
    db_patcher = patch("nexuscore.models.db")
    api_key_mock = api_key_patcher.start()
    api_key_mock.query = mock_query
    api_key_mock.hash_token.side_effect = lambda raw: (
        valid_hash if raw == valid_key else "hash-of-other-key"
    )
    user_patcher.start()
    db_patcher.start()
    return (api_key_patcher, user_patcher, db_patcher)


def test_harness_index_requires_api_key(client: TestClient) -> None:
    """GET /harness/ は X-API-Key ヘッダー必須（欠落は 422）"""
    response = client.get("/harness/")
    assert response.status_code in (401, 422), response.text
    assert response.status_code != 200


def test_harness_run_requires_api_key(client: TestClient) -> None:
    """POST /harness/run は X-API-Key ヘッダー必須（欠落は 422・タスクを実行されない）"""
    response = client.post("/harness/run", data={"task": "ls", "provider": "mock"})
    assert response.status_code in (401, 422), response.text
    assert response.status_code != 200


def test_harness_index_rejects_invalid_api_key(
    client: TestClient, mock_api_key: str
) -> None:
    """誤った API Key は 401"""
    patchers = _patch_auth(_make_auth_key_obj(), mock_api_key)
    try:
        response = client.get("/harness/", headers={"X-API-Key": "wrong-key-value"})
        assert response.status_code == 401, response.text
    finally:
        for p in patchers:
            p.stop()


def test_harness_run_rejects_invalid_api_key(
    client: TestClient, mock_api_key: str
) -> None:
    """誤った API Key では /harness/run も 401"""
    patchers = _patch_auth(_make_auth_key_obj(), mock_api_key)
    try:
        response = client.post(
            "/harness/run",
            data={"task": "ls", "provider": "mock"},
            headers={"X-API-Key": "wrong-key-value"},
        )
        assert response.status_code == 401, response.text
    finally:
        for p in patchers:
            p.stop()


def test_harness_index_with_valid_api_key_is_allowed(
    client: TestClient, mock_api_key: str
) -> None:
    """正しい API Key では /harness/ が開ける（認証を付けたことで機能が壊れていない）"""
    patchers = _patch_auth(_make_auth_key_obj(), mock_api_key)
    try:
        response = client.get("/harness/", headers={"X-API-Key": mock_api_key})
        assert response.status_code == 200, response.text
    finally:
        for p in patchers:
            p.stop()
