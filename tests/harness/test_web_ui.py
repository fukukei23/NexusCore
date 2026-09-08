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

from fastapi import FastAPI
from fastapi.testclient import TestClient

from nexuscore.api.fastapi_app import create_app
from nexuscore.api.harness_routes import router as harness_router


def test_index_renders_form() -> None:
    """正常系: GET /harness/ がタスク入力フォームを返す（plan Task 23 Step 2）"""
    app = FastAPI()
    app.include_router(harness_router)
    client = TestClient(app)
    resp = client.get("/harness/")
    assert resp.status_code == 200
    assert "<form" in resp.text
    assert 'action="/harness/run"' in resp.text


def test_run_renders_harness_result() -> None:
    """正常系: POST /harness/run がharness実行結果（JSON）を画面へ返す

    mockダミーは常時tool_call要求するためregistry（読む系のみ）で消費しきり
    abort_reason=limits で終わる＝fail-closed挙動のスモーク確認を兼ねる。
    """
    app = FastAPI()
    app.include_router(harness_router)
    client = TestClient(app)
    resp = client.post("/harness/run", data={"task": "hello", "provider": "mock"})
    assert resp.status_code == 200
    assert "abort_reason" in resp.text


def test_run_does_not_touch_cli_default_state(tmp_path, monkeypatch) -> None:
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
    resp = client.post("/harness/run", data={"task": "hello", "provider": "mock"})
    assert resp.status_code == 200
    assert (tmp_path / "artifacts/harness/run_state_webui.json").exists()
    assert not (tmp_path / "artifacts/harness/run_state.json").exists()


def test_router_included_in_app() -> None:
    """結合: create_app() に /harness ルートが組み込まれている（ADR-002統合先）"""
    client = TestClient(create_app())
    resp = client.get("/harness/")
    assert resp.status_code == 200
    assert "<form" in resp.text
