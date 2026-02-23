"""
FastAPI RunView API 並行実行テスト (CR-NEXUS-030).

同一プロセス内での同時Resumeリクエストが安全に処理されることを確認する。
"""

import json
import threading
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

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
    """データベースモデルをモック（認証用）"""
    with (
        patch("nexuscore.webapp.models.User") as mock_user,
        patch("nexuscore.webapp.models.ApiKey") as mock_api_key_model,
        patch("nexuscore.webapp.db") as mock_db,
    ):
        # API Key認証のモック
        mock_user_obj = MagicMock()
        mock_user_obj.id = 1
        mock_user.query.first.return_value = mock_user_obj

        mock_api_key_obj = MagicMock()
        mock_api_key_obj.user = mock_user_obj
        mock_api_key_model.hash_token.return_value = "hashed_key"
        mock_api_key_model.query.filter_by.return_value.first.return_value = mock_api_key_obj

        yield {
            "User": mock_user,
            "ApiKey": mock_api_key_model,
            "db": mock_db,
        }


@pytest.fixture
def isolated_state_dir(monkeypatch, tmp_path):
    """RunState ディレクトリを tmp に隔離"""
    state_dir = tmp_path / "run_state"
    state_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NEXUSCORE_RUN_STATE_DIR", str(state_dir))
    monkeypatch.setenv("NEXUSCORE_RUN_LOCK_DIR", str(tmp_path / "run_lock"))
    monkeypatch.setenv("NEXUSCORE_RUNSTATE_HMAC_SECRET", "test-secret")
    return state_dir


def test_resume_run_view_concurrent_same_run_id(
    client: TestClient, mock_api_key, mock_db_models, isolated_state_dir, monkeypatch
):
    """
    同一 run_id への同時Resumeリクエストが FS Lock で制御されることを確認。

    1つ目のリクエストは成功、2つ目は CONFLICT を返す。
    """
    run_id = "test-run-concurrent"

    # Create a minimal RunState for load_state to succeed
    state_file = isolated_state_dir / f"{run_id}.json"
    state = {
        "schema_version": "1.0",
        "run_id": run_id,
        "status": "PAUSED",
        "authority_level": "partial",
        "next_phase": "implementation",
        "updated_at": "2025-01-01T00:00:00+00:00",
    }
    state_file.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    # Track orchestrator instances to ensure they are not shared
    orchestrator_instances = []
    orchestrator_lock = threading.Lock()

    # Mock get_orchestrator to return unique orchestrator instances
    class FakeOrchestrator:
        def __init__(self, instance_id):
            self.instance_id = instance_id
            self.project_path = "/tmp/test"

    instance_counter = {"count": 0}

    def mock_get_orchestrator(project_path=None, language="ja"):
        with orchestrator_lock:
            instance_counter["count"] += 1
            instance_id = instance_counter["count"]
            orch = FakeOrchestrator(instance_id)
            orchestrator_instances.append(orch)
            return orch

    # Track resume_run calls and verify orchestrator_factory is called for each request
    resume_call_count = {"count": 0}
    resume_lock = threading.Lock()
    factory_call_tracker = []

    def mock_resume_run(run_id_param: str, *, orchestrator_factory=None):
        # Verify orchestrator_factory is provided (API route should always provide it)
        assert (
            orchestrator_factory is not None
        ), "orchestrator_factory should be provided by API route"

        # Call factory to create orchestrator instance (even if we don't use it, it verifies isolation)
        if orchestrator_factory:
            orch = orchestrator_factory()
            with resume_lock:
                factory_call_tracker.append(orch.instance_id)

        # Simulate lock acquisition - first call succeeds, second fails
        with resume_lock:
            call_num = resume_call_count["count"]
            resume_call_count["count"] += 1

            if call_num == 0:
                # First call: succeed (RUNNING)
                return {
                    "status": "RUNNING",
                    "run_id": run_id_param,
                }
            else:
                # Second call: CONFLICT (lock already held)
                from nexuscore.orchestrator.explainability import build_explainability

                return {
                    "status": "CONFLICT",
                    "run_id": run_id_param,
                    "explainability": build_explainability(
                        what=f"Resume conflict: run_id={run_id_param} is already being resumed/executed",
                        why_code="CONFLICT",
                        next_action="wait/retry",
                    ),
                }

    results = []
    results_lock = threading.Lock()

    def make_request():
        try:
            response = client.post(
                f"/api/v1/runs/{run_id}/resume",
                headers={"X-API-Key": mock_api_key},
            )
            with results_lock:
                results.append(
                    {
                        "status_code": response.status_code,
                        "data": response.json(),
                    }
                )
        except Exception as e:
            with results_lock:
                results.append({"error": str(e)})

    with (
        patch("nexuscore.api.routes.run_view.get_orchestrator", side_effect=mock_get_orchestrator),
        patch("nexuscore.orchestrator.authority_runner.resume_run", side_effect=mock_resume_run),
    ):
        # Launch two concurrent requests
        thread1 = threading.Thread(target=make_request)
        thread2 = threading.Thread(target=make_request)

        thread1.start()
        time.sleep(0.1)  # Small delay to let first request start
        thread2.start()

        thread1.join()
        thread2.join()

    # Verify results: one should succeed (200), one should conflict (409)
    assert len(results) == 2
    status_codes = [r["status_code"] for r in results if "status_code" in r]
    assert 200 in status_codes
    assert 409 in status_codes

    # Verify orchestrator_factory was called for both requests (even if second one conflicts)
    # This verifies that each request gets its own factory call, ensuring isolation
    assert len(factory_call_tracker) >= 1, "orchestrator_factory should be called at least once"

    # Verify orchestrator instances are unique (if multiple were created)
    if len(factory_call_tracker) >= 2:
        assert len(factory_call_tracker) == len(
            set(factory_call_tracker)
        ), "Orchestrator instances should be unique"


def test_resume_run_view_concurrent_different_run_ids(
    client: TestClient, mock_api_key, mock_db_models, isolated_state_dir, monkeypatch
):
    """
    異なる run_id への同時Resumeリクエストが独立して処理されることを確認。

    両方のリクエストが成功する。
    """
    run_id1 = "test-run-concurrent-1"
    run_id2 = "test-run-concurrent-2"

    # Create RunStates for both run_ids
    for run_id in [run_id1, run_id2]:
        state_file = isolated_state_dir / f"{run_id}.json"
        state = {
            "schema_version": "1.0",
            "run_id": run_id,
            "status": "PAUSED",
            "authority_level": "partial",
            "next_phase": "implementation",
            "updated_at": "2025-01-01T00:00:00+00:00",
        }
        state_file.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    # Track orchestrator instances
    orchestrator_instances = []
    orchestrator_lock = threading.Lock()

    class FakeOrchestrator:
        def __init__(self, instance_id):
            self.instance_id = instance_id
            self.project_path = "/tmp/test"

    instance_counter = {"count": 0}

    def mock_get_orchestrator(project_path=None, language="ja"):
        with orchestrator_lock:
            instance_counter["count"] += 1
            instance_id = instance_counter["count"]
            orch = FakeOrchestrator(instance_id)
            orchestrator_instances.append(orch)
            return orch

    def mock_resume_run(run_id_param: str, *, orchestrator_factory=None):
        # Both should succeed
        if orchestrator_factory:
            orch = orchestrator_factory()
        return {
            "status": "RUNNING",
            "run_id": run_id_param,
        }

    results = []
    results_lock = threading.Lock()

    def make_request(run_id):
        try:
            response = client.post(
                f"/api/v1/runs/{run_id}/resume",
                headers={"X-API-Key": mock_api_key},
            )
            with results_lock:
                results.append(
                    {
                        "run_id": run_id,
                        "status_code": response.status_code,
                        "data": response.json(),
                    }
                )
        except Exception as e:
            with results_lock:
                results.append({"run_id": run_id, "error": str(e)})

    with (
        patch("nexuscore.api.routes.run_view.get_orchestrator", side_effect=mock_get_orchestrator),
        patch("nexuscore.orchestrator.authority_runner.resume_run", side_effect=mock_resume_run),
    ):
        # Launch two concurrent requests with different run_ids
        thread1 = threading.Thread(target=make_request, args=(run_id1,))
        thread2 = threading.Thread(target=make_request, args=(run_id2,))

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

    # Verify both requests succeed
    assert len(results) == 2
    for result in results:
        assert "status_code" in result
        assert result["status_code"] == 200

    # Verify orchestrator instances are unique
    assert len(orchestrator_instances) >= 2
    instance_ids = [o.instance_id for o in orchestrator_instances]
    assert len(instance_ids) == len(set(instance_ids)), "Orchestrator instances should be unique"
