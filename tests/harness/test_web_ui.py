"""Task 23: ハーネスWeb UI薄い実装（plan Phase 4・ADR-002準拠）

plan雛形からの意図的変更（実契約突合・変更記録方式）:
- 配置を plan雛形の ``webapp/harness_routes.py`` から ``api/harness_routes.py`` へ変更
  （FastAPIアプリの実体は ``api/fastapi_app.py``・ADR-002決定Aどおりの統合先）
- LLMRouter経路はCLI（Task 15）と同じく不使用（RoutedLLMはcomplete_with_tools未実装のため
  ``harness_cli.build_llm``/``create_provider`` 直接生成を再利用・DRY）
- ask承認UIはTTY結合のAskSessionでは表現できないため本実装は ``ask=False``
  （registry=読む系のみ・fail-closed。ask承認UIは将来拡張=run_state ask履歴結線§122と同時期）
- 既定providerはmock（オフライン・安全側。実LLMはフォーム明示指定時のみ）
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from nexuscore.api.fastapi_app import create_app
from nexuscore.api.harness_routes import router as harness_router

# 2026-11-17 改訂（Strix診断A案③）: /harness/* にAPI Key認証が付与されたため、
# 既存テストは「認証なしで200」前提だった。本テストは認証ヘッダーを送出する
# 形に更新し、検証対象（フォーム描画・実行結果・state分離・上限結線）は維持する。


@pytest.fixture()
def api_key(monkeypatch: pytest.MonkeyPatch) -> str:
    """API Key を設定し、DB 解決をモック化する（既存APIテストと同方式）"""
    key = "test-api-key-123"
    monkeypatch.setenv("NEXUSCORE_API_KEY", key)

    mock_auth_user = MagicMock()
    mock_auth_user.id = 1
    mock_auth_user.github_login = "testuser"
    mock_key = MagicMock()
    mock_key.user = mock_auth_user
    mock_key.user_id = 1
    valid_hash = "hash-of-valid-key"

    def _filter_by(token_hash=None, **_kwargs):
        chain = MagicMock()
        chain.first.return_value = mock_key if token_hash == valid_hash else None
        return chain

    mock_query = MagicMock()
    mock_query.filter_by.side_effect = _filter_by
    api_key_patcher = patch("nexuscore.models.ApiKey")
    api_key_mock = api_key_patcher.start()
    api_key_mock.query = mock_query
    api_key_mock.hash_token.side_effect = (
        lambda raw: valid_hash if raw == key else "hash-of-other-key"
    )
    patch("nexuscore.models.User").start()
    patch("nexuscore.models.db").start()
    try:
        yield key
    finally:
        api_key_patcher.stop()


def test_index_renders_form(api_key: str) -> None:
    """正常系: GET /harness/ がタスク入力フォームを返す（plan Task 23 Step 2）"""
    app = FastAPI()
    app.include_router(harness_router)
    client = TestClient(app)
    resp = client.get("/harness/", headers={"X-API-Key": api_key})
    assert resp.status_code == 200
    assert "<form" in resp.text
    assert 'action="/harness/run"' in resp.text


def test_run_renders_harness_result(api_key: str) -> None:
    """正常系: POST /harness/run がharness実行結果（JSON）を画面へ返す

    mockダミーは常時tool_call要求するためregistry（読む系のみ）で消費しきり
    abort_reason=limits で終わる＝fail-closed挙動のスモーク確認を兼ねる。
    """
    app = FastAPI()
    app.include_router(harness_router)
    client = TestClient(app)
    resp = client.post(
        "/harness/run",
        data={"task": "hello", "provider": "mock"},
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 200
    assert "abort_reason" in resp.text


def test_run_does_not_touch_cli_default_state(tmp_path, monkeypatch, api_key: str) -> None:
    """異常系（回帰・2026-09-09実害）: Web UI実行がCLI既定stateを汚染しない

    実害: _run_harnessがRunStateStore()（既定=artifacts/harness/run_state.json・
    CWD相対）を使うため、Web UIのmockスモークテストがCLIの中断run stateを
    上書きした（Task 24 run1のdeepseek stateがpytest検証中に破壊された実測）。
    封じ手: Web UI実行はrun_state_webui.jsonへ分離。
    """
    monkeypatch.chdir(tmp_path)
    app = FastAPI()
    app.include_router(harness_router)
    client = TestClient(app)
    resp = client.post(
        "/harness/run",
        data={"task": "hello", "provider": "mock"},
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 200
    assert (tmp_path / "artifacts/harness/run_state_webui.json").exists()
    assert not (tmp_path / "artifacts/harness/run_state.json").exists()


def test_router_included_in_app(api_key: str) -> None:
    """結合: create_app() に /harness ルートが組み込まれている（ADR-002統合先）"""
    client = TestClient(create_app())
    resp = client.get("/harness/", headers={"X-API-Key": api_key})
    assert resp.status_code == 200
    assert "<form" in resp.text


def test_webui_applies_operational_limits_and_context(monkeypatch, api_key: str) -> None:
    """fail条件ケース: Web UI経路もCLIと同じ上限・cwd注入を適用すること

    2026-09-19 self-inspectで発見: 上限結線（--max-tokens）とG-1コンテキスト
    注入はCLI側にしか実装されておらず、Web UI経由はLimits既定500_000の
    90%=450,000まで走り、cwd注入も無かった（経路差＝同じ穴が残る）。
    """
    from nexuscore.api import harness_routes
    from nexuscore.cli.harness_cli import OPERATIONAL_MAX_TOKENS

    captured: dict = {}

    class _SpyHarness:
        def __init__(self, **kwargs):
            captured["limits"] = kwargs.get("limits")

        def run(self, task, messages=None, *, system_prompt=None):
            captured["system_prompt"] = system_prompt
            return {"content": "ok", "abort_reason": None}

    monkeypatch.setattr(harness_routes, "AgentHarness", _SpyHarness)
    app = FastAPI()
    app.include_router(harness_router)
    client = TestClient(app)
    resp = client.post(
        "/harness/run",
        data={"task": "hello", "provider": "mock"},
        headers={"X-API-Key": api_key},
    )

    assert resp.status_code == 200
    assert captured["limits"] is not None
    assert captured["limits"].max_tokens == OPERATIONAL_MAX_TOKENS
    assert captured["system_prompt"] and "作業ディレクトリ" in captured["system_prompt"]
