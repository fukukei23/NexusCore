"""
api/dependencies/auth.py テスト (Issue #96)

load_api_key, get_api_key, get_current_user, get_current_user_optional をカバー
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

import nexuscore.api.dependencies.auth as auth_module
from nexuscore.api.dependencies.auth import (
    AuthenticatedUser,
    get_api_key,
    get_current_user,
    get_current_user_optional,
    load_api_key,
)


@pytest.fixture(autouse=True)
def reset_cache():
    auth_module._cached_api_key = None
    yield
    auth_module._cached_api_key = None


@pytest.fixture
def env_key(monkeypatch):
    monkeypatch.setenv("NEXUSCORE_API_KEY", "test-key")


@pytest.fixture
def no_env_key(monkeypatch):
    monkeypatch.delenv("NEXUSCORE_API_KEY", raising=False)


# === load_api_key: secrets.json パス (L64-71) ===


def test_load_from_secrets_json(no_env_key, tmp_path):
    """secrets.json から API Key を読み込む (L64-69)"""
    (tmp_path / "secrets.json").write_text(
        json.dumps({"NEXUSCORE_API_KEY": "json-key"}), encoding="utf-8"
    )
    mock_file = MagicMock()
    mock_file.resolve.return_value.parent.parent.parent.parent = tmp_path
    with patch.object(auth_module, "Path", return_value=mock_file):
        assert load_api_key() == "json-key"


def test_secrets_json_missing_key_returns_none(no_env_key, tmp_path):
    """secrets.json に該当キーなし → None"""
    (tmp_path / "secrets.json").write_text(
        json.dumps({"OTHER": "val"}), encoding="utf-8"
    )
    mock_file = MagicMock()
    mock_file.resolve.return_value.parent.parent.parent.parent = tmp_path
    with patch.object(auth_module, "Path", return_value=mock_file):
        assert load_api_key() is None


def test_secrets_json_invalid_json_returns_none(no_env_key, tmp_path):
    """secrets.json の JSON が壊れている → None (L70-71)"""
    (tmp_path / "secrets.json").write_text("{bad json", encoding="utf-8")
    mock_file = MagicMock()
    mock_file.resolve.return_value.parent.parent.parent.parent = tmp_path
    with patch.object(auth_module, "Path", return_value=mock_file):
        assert load_api_key() is None


def test_secrets_json_empty_value_returns_none(no_env_key, tmp_path):
    """secrets.json の値が空文字 → None"""
    (tmp_path / "secrets.json").write_text(
        json.dumps({"NEXUSCORE_API_KEY": ""}), encoding="utf-8"
    )
    mock_file = MagicMock()
    mock_file.resolve.return_value.parent.parent.parent.parent = tmp_path
    with patch.object(auth_module, "Path", return_value=mock_file):
        assert load_api_key() is None


def test_no_secrets_file_returns_none(no_env_key, tmp_path):
    """secrets.json が存在しない → None"""
    mock_file = MagicMock()
    mock_root = MagicMock()
    mock_root.__truediv__ = lambda s, o: MagicMock(**{"exists.return_value": False})
    mock_file.resolve.return_value.parent.parent.parent.parent = mock_root
    with patch.object(auth_module, "Path", return_value=mock_file):
        assert load_api_key() is None


def test_secrets_json_read_exception(no_env_key, tmp_path):
    """secrets.json 読み込み例外 → None (L70-71)"""
    secrets = tmp_path / "secrets.json"
    secrets.write_text(json.dumps({"NEXUSCORE_API_KEY": "key"}), encoding="utf-8")
    mock_file = MagicMock()
    mock_file.resolve.return_value.parent.parent.parent.parent = tmp_path
    with patch.object(auth_module, "Path", return_value=mock_file):
        with patch("builtins.open", side_effect=PermissionError("denied")):
            assert load_api_key() is None


def test_load_from_env(env_key):
    """環境変数から取得"""
    assert load_api_key() == "test-key"


def test_load_from_env_strips(env_key, monkeypatch):
    """前後空白をstrip"""
    monkeypatch.setenv("NEXUSCORE_API_KEY", "  spaced  ")
    assert load_api_key() == "spaced"


# === get_api_key: キャッシュ空文字 (L95-96) ===


def test_get_api_key_empty_string_raises_500(env_key, monkeypatch):
    """_cached_api_key が空文字 → 500 (L95-96)"""
    monkeypatch.setenv("NEXUSCORE_API_KEY", " ")
    auth_module._cached_api_key = None
    with pytest.raises(HTTPException) as exc:
        get_api_key()
    assert exc.value.status_code == 500


def test_get_api_key_none_raises_500(no_env_key):
    """キーがどこにもない → 500"""
    with pytest.raises(HTTPException) as exc:
        get_api_key()
    assert exc.value.status_code == 500


def test_get_api_key_caching(env_key):
    """2回目はキャッシュから"""
    first = get_api_key()
    second = get_api_key()
    assert first is second


# === get_current_user: DB 正常系 ===


def _make_db_mocks(user_id=123, has_user_attr=True):
    mock_user = MagicMock()
    mock_user.id = user_id

    mock_api_key_obj = MagicMock()
    mock_api_key_obj.user_id = user_id
    if has_user_attr:
        mock_api_key_obj.user = mock_user
    else:
        del mock_api_key_obj.user

    mock_query = MagicMock()
    mock_query.filter_by.return_value.first.return_value = mock_api_key_obj
    mock_query.get.return_value = mock_user

    mock_api_key_cls = MagicMock()
    mock_api_key_cls.hash_token.return_value = "hashed"
    mock_api_key_cls.query = mock_query

    mock_user_cls = MagicMock()
    mock_user_cls.query = mock_query

    return mock_api_key_cls, mock_user_cls


def _patch_db(mock_api_key_cls, mock_user_cls):
    return patch.dict(
        "sys.modules",
        {
            "nexuscore.webapp.models": MagicMock(
                ApiKey=mock_api_key_cls, User=mock_user_cls
            ),
        },
    )


def test_db_auth_with_user_attr(env_key):
    """api_key_obj.user あり → 認証成功"""
    ak, uk = _make_db_mocks(has_user_attr=True)
    with _patch_db(ak, uk):
        user = get_current_user(x_api_key="valid")
    assert user.user_id == "123"
    assert user.roles == ["api_user"]


def test_db_auth_without_user_attr(env_key):
    """api_key_obj.user なし → User.query.get から取得"""
    ak, uk = _make_db_mocks(has_user_attr=False)
    with _patch_db(ak, uk):
        user = get_current_user(x_api_key="valid")
    assert user.user_id == "123"


def test_db_api_key_not_found(env_key):
    """DB に API Key なし → 401"""
    ak, uk = _make_db_mocks()
    ak.query.filter_by.return_value.first.return_value = None
    with _patch_db(ak, uk):
        with pytest.raises(HTTPException) as exc:
            get_current_user(x_api_key="invalid")
    assert exc.value.status_code == 401


def test_db_user_not_found(env_key):
    """User なし → 401"""
    ak, uk = _make_db_mocks(has_user_attr=False)
    uk.query.get.return_value = None
    with _patch_db(ak, uk):
        with pytest.raises(HTTPException) as exc:
            get_current_user(x_api_key="valid")
    assert exc.value.status_code == 401


# === get_current_user: ApiKey.query 不可 (L136-144) ===


def test_apikey_query_none(env_key):
    """ApiKey.query is None → 401 (L136-138)"""
    ak = MagicMock()
    ak.hash_token.return_value = "hashed"
    ak.query = None
    with _patch_db(ak, MagicMock()):
        with pytest.raises(HTTPException) as exc:
            get_current_user(x_api_key="key")
    assert exc.value.status_code == 401


def test_apikey_no_query_attr(env_key):
    """hasattr(ApiKey, 'query') is False → 401"""
    ak = MagicMock()
    ak.hash_token.return_value = "hashed"
    del ak.query
    with _patch_db(ak, MagicMock()):
        with pytest.raises(HTTPException) as exc:
            get_current_user(x_api_key="key")
    assert exc.value.status_code == 401


def test_apikey_filter_attribute_error(env_key):
    """filter_by で AttributeError → 401 (L140-144)"""
    ak = MagicMock()
    ak.query.filter_by.side_effect = AttributeError("no attr")
    with _patch_db(ak, MagicMock()):
        with pytest.raises(HTTPException) as exc:
            get_current_user(x_api_key="key")
    assert exc.value.status_code == 401


def test_apikey_filter_runtime_error(env_key):
    """filter_by で RuntimeError → 401"""
    ak = MagicMock()
    ak.query.filter_by.side_effect = RuntimeError("no session")
    with _patch_db(ak, MagicMock()):
        with pytest.raises(HTTPException) as exc:
            get_current_user(x_api_key="key")
    assert exc.value.status_code == 401


def test_apikey_sqlalchemy_error(env_key):
    """SQLAlchemyError → 500 (L145-148)"""
    from sqlalchemy.exc import SQLAlchemyError

    ak = MagicMock()
    ak.query.filter_by.side_effect = SQLAlchemyError("conn error")
    with _patch_db(ak, MagicMock()):
        with pytest.raises(HTTPException) as exc:
            get_current_user(x_api_key="key")
    assert exc.value.status_code == 500


def test_apikey_unexpected_error_with_context(env_key):
    """予期しない例外 + "context" 文字列 → 401 (L155-158)"""
    ak = MagicMock()
    ak.hash_token.side_effect = Exception("no application context")
    with _patch_db(ak, MagicMock()):
        with pytest.raises(HTTPException) as exc:
            get_current_user(x_api_key="key")
    assert exc.value.status_code == 401


def test_apikey_unexpected_error_no_context(env_key):
    """予期しない例外 + context 文字列なし → 500 (L159-160)"""
    ak = MagicMock()
    ak.hash_token.side_effect = Exception("weird error")
    with _patch_db(ak, MagicMock()):
        with pytest.raises(HTTPException) as exc:
            get_current_user(x_api_key="key")
    assert exc.value.status_code == 500


# === get_current_user: User 取得フォールバック (L170-197) ===


def _make_user_fallback_mocks():
    ak, uk = _make_db_mocks(has_user_attr=False)
    return ak, uk


def test_user_query_none(env_key):
    """User.query is None → 401 (L173-175)"""
    ak, uk = _make_user_fallback_mocks()
    uk.query = None
    with _patch_db(ak, uk):
        with pytest.raises(HTTPException) as exc:
            get_current_user(x_api_key="key")
    assert exc.value.status_code == 401


def test_user_no_query_attr(env_key):
    """hasattr(User, 'query') is False → 401"""
    ak, uk = _make_user_fallback_mocks()
    del uk.query
    with _patch_db(ak, uk):
        with pytest.raises(HTTPException) as exc:
            get_current_user(x_api_key="key")
    assert exc.value.status_code == 401


def test_user_attribute_error(env_key):
    """User.query.get で AttributeError → 401 (L177-181)"""
    ak, uk = _make_user_fallback_mocks()
    uk.query.get.side_effect = AttributeError("attr err")
    with _patch_db(ak, uk):
        with pytest.raises(HTTPException) as exc:
            get_current_user(x_api_key="key")
    assert exc.value.status_code == 401


def test_user_runtime_error(env_key):
    """User.query.get で RuntimeError → 401"""
    ak, uk = _make_user_fallback_mocks()
    uk.query.get.side_effect = RuntimeError("runtime")
    with _patch_db(ak, uk):
        with pytest.raises(HTTPException) as exc:
            get_current_user(x_api_key="key")
    assert exc.value.status_code == 401


def test_user_sqlalchemy_error(env_key):
    """User.query.get で SQLAlchemyError → 500 (L182-185)"""
    from sqlalchemy.exc import SQLAlchemyError

    ak, uk = _make_user_fallback_mocks()
    uk.query.get.side_effect = SQLAlchemyError("db err")
    with _patch_db(ak, uk):
        with pytest.raises(HTTPException) as exc:
            get_current_user(x_api_key="key")
    assert exc.value.status_code == 500


def test_user_unexpected_error_with_query_string(env_key):
    """User 取得例外 + "query" 文字列 → 401 (L192-195)"""
    ak, uk = _make_user_fallback_mocks()
    uk.query.get.side_effect = Exception("query object has no attribute")
    with _patch_db(ak, uk):
        with pytest.raises(HTTPException) as exc:
            get_current_user(x_api_key="key")
    assert exc.value.status_code == 401


def test_user_unexpected_error_without_context(env_key):
    """User 取得例外 + context 文字列なし → 500 (L196-197)"""
    ak, uk = _make_user_fallback_mocks()
    uk.query.get.side_effect = Exception("unknown failure")
    with _patch_db(ak, uk):
        with pytest.raises(HTTPException) as exc:
            get_current_user(x_api_key="key")
    assert exc.value.status_code == 500


# === ImportError フォールバック (L208-222) ===


def test_import_error_fallback_success(env_key):
    """webapp.models ImportError → 環境変数比較で成功 (L208-222)"""
    with patch.dict("sys.modules", {"nexuscore.webapp.models": None}):
        user = get_current_user(x_api_key="test-key")
    assert user.user_id == "api_user"
    assert user.roles == ["api_user"]


def test_import_error_fallback_wrong_key(env_key):
    """webapp.models ImportError → キー不一致で 401"""
    with patch.dict("sys.modules", {"nexuscore.webapp.models": None}):
        with pytest.raises(HTTPException) as exc:
            get_current_user(x_api_key="wrong")
    assert exc.value.status_code == 401


def test_import_error_no_api_key(no_env_key):
    """webapp.models ImportError + APIキー未設定 → 500"""
    with patch.dict("sys.modules", {"nexuscore.webapp.models": None}):
        with pytest.raises(HTTPException) as exc:
            get_current_user(x_api_key="key")
    assert exc.value.status_code == 500


# === 外部 try の予期しない例外 (L223-233) ===


def test_outer_unexpected_exception(env_key):
    """外部 try で予期しない例外 → 500 (L223-233)"""
    with patch.object(auth_module, "get_api_key", side_effect=TypeError("boom")):
        with pytest.raises(HTTPException) as exc:
            get_current_user(x_api_key="key")
    assert exc.value.status_code == 500


# === get_current_user_optional ===


def test_optional_no_header(env_key):
    """ヘッダーなし → None"""
    result = get_current_user_optional(x_api_key=None)
    assert result is None


def test_optional_valid_key(env_key):
    """有効キー → AuthenticatedUser"""
    result = get_current_user_optional(x_api_key="test-key")
    assert result.user_id == "api_user"


def test_optional_invalid_key(env_key):
    """無効キー → 401"""
    with pytest.raises(HTTPException) as exc:
        get_current_user_optional(x_api_key="wrong")
    assert exc.value.status_code == 401
