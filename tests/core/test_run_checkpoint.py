"""run_checkpoint（C3 Plan2・Orchestrator内部冪等性）のテスト。fakeredis 使用。"""
import logging

import fakeredis
import pytest

from nexuscore.core.orchestrator_models import OrchestratorContext
from nexuscore.core.run_checkpoint import (
    LOCK_TTL,
    PHASE_INDEX,
    PHASE_SEQUENCE,
    checkpoint_key,
    clear_checkpoints,
    get_client,
    llm_cache_get,
    llm_cache_key,
    llm_cache_set,
    load_checkpoint,
    mark_phase_done,
    run_phases_with_checkpoint,
)


@pytest.fixture(autouse=True)
def _isolate_logging():
    """フルスイート実行時の caplog 取りこぼし防止。

    他テストがエージェントを生成すると nexuscore ロガーの propagate が
    False に設定され、caplog（root ハンドラ）まで ERROR が伝播しなくなる
    （test_plan_contract.py と同一対処）。
    """
    logging.disable(logging.NOTSET)
    names = ["nexuscore", "nexuscore.core", "nexuscore.core.run_checkpoint"]
    saved = {n: logging.getLogger(n).propagate for n in names}
    for n in names:
        logging.getLogger(n).propagate = True
    yield
    for n, value in saved.items():
        logging.getLogger(n).propagate = value


@pytest.fixture
def fake_client():
    return fakeredis.FakeStrictRedis()


def test_phase_sequence_order():
    """PHASE_SEQUENCE は run_full_project の呼び出し順と一致する"""
    names = [name for name, _ in PHASE_SEQUENCE]
    assert names == [
        "context", "requirements", "planning", "architecture",
        "implementation", "testing", "review",
    ]
    assert PHASE_INDEX["review"] == 6


def test_checkpoint_key_format():
    """A1: 単一キー"""
    assert checkpoint_key(7) == "checkpoint:7"


def test_get_client_env(monkeypatch):
    """REDIS_URL 優先・A2: socket timeout 付き"""
    monkeypatch.setenv("REDIS_URL", "redis://example:6380/2")
    c = get_client()
    kw = c.connection_pool.connection_kwargs
    assert "example" in str(kw.get("host", ""))
    assert kw.get("socket_timeout") == 1.0


def test_get_client_none_when_disabled(monkeypatch):
    """NEXUSCORE_CHECKPOINT=0 で None（kill-switch）"""
    monkeypatch.setenv("NEXUSCORE_CHECKPOINT", "0")
    assert get_client() is None


def test_lock_ttl_below_visibility_timeout():
    """A3: 不変条件 lock TTL < visibility_timeout（docker-compose実値7200）"""
    import re
    from pathlib import Path

    compose = Path("docker-compose.saas.yml").read_text()
    m = re.search(r"CELERY_BROKER_VISIBILITY_TIMEOUT=(\d+)", compose)
    assert m, "docker-compose.saas.yml に visibility_timeout 設定が無い"
    assert LOCK_TTL < int(m.group(1))


def _ctx(**overrides):
    base = dict(task_id="t1", user_requirement="req", run_db_id=7)
    base.update(overrides)
    return OrchestratorContext(**base)


def test_mark_and_load_roundtrip(fake_client):
    """mark後、loadが last_done と復元 context を返す"""
    ctx = _ctx()
    ctx.plan = {"functions_to_implement": ["f1"]}
    mark_phase_done(fake_client, 7, "planning", ctx)

    last_done, restored = load_checkpoint(fake_client, 7)
    assert last_done == "planning"
    assert restored is not None
    assert restored.plan == {"functions_to_implement": ["f1"]}
    assert restored.user_requirement == "req"


def test_load_no_checkpoint(fake_client):
    assert load_checkpoint(fake_client, 999) == (None, None)


def test_load_corrupted_payload_is_ignored(fake_client):
    """A1: 破損ペイロードは『無し』扱い（フル再実行に退化）"""
    fake_client.set(checkpoint_key(7), b"Rnot-json")
    assert load_checkpoint(fake_client, 7) == (None, None)


def test_load_schema_mismatch_is_ignored(fake_client):
    """A1: schema_version 不一致は破棄"""
    fake_client.set(checkpoint_key(7), b'R{"schema_version": 99, "last_done": "planning", "context": {}}')
    assert load_checkpoint(fake_client, 7) == (None, None)


def test_load_takes_latest_phase(fake_client):
    """単一キー上書き=常に最新phase"""
    mark_phase_done(fake_client, 7, "context", _ctx())
    ctx2 = _ctx()
    ctx2.plan = {"p": 2}
    mark_phase_done(fake_client, 7, "requirements", ctx2)
    last_done, restored = load_checkpoint(fake_client, 7)
    assert last_done == "requirements"
    assert restored.plan == {"p": 2}


def test_snapshot_compression_roundtrip(fake_client):
    """A5: 512KB超ペイロードはzlib圧縮されて往復する"""
    ctx = _ctx()
    ctx.review_report = {"blob": "あ" * 400_000}  # >512KB相当
    mark_phase_done(fake_client, 7, "review", ctx)
    raw = fake_client.get(checkpoint_key(7))
    assert raw[:1] == b"C"  # 圧縮フラグ
    last_done, restored = load_checkpoint(fake_client, 7)
    assert restored.review_report == ctx.review_report


def test_serialize_failure_logs_error_and_continues(fake_client, monkeypatch, caplog):
    """A6: dumps失敗(TypeError)はERRORログで可視化し例外を吐かない"""
    def boom(obj, **kw):
        raise TypeError("not serializable")
    monkeypatch.setattr("nexuscore.core.run_checkpoint.json.dumps", boom)
    with caplog.at_level(logging.ERROR):
        mark_phase_done(fake_client, 7, "planning", _ctx())  # 例外なし
    assert any("serialize failed" in r.message for r in caplog.records)


def test_clear_checkpoints(fake_client):
    mark_phase_done(fake_client, 7, "context", _ctx())
    clear_checkpoints(fake_client, 7)
    assert load_checkpoint(fake_client, 7) == (None, None)


def test_context_roundtrip_ci_guard():
    """A8: OrchestratorContext 全フィールドの asdict→JSON→復元が壊れていないかCI固定化"""
    ctx = _ctx()
    ctx.debug_history = [{"attempt": 1}]
    ctx.review_report = {"score": 3}
    fc = fakeredis.FakeStrictRedis()
    mark_phase_done(fc, 1, "planning", ctx)
    _, restored = load_checkpoint(fc, 1)
    assert restored.debug_history == ctx.debug_history
    assert restored.review_report == ctx.review_report


class FakeRunner:
    """run_*_phase を持つ duck-typed ランナー"""

    def __init__(self, fail_at: str | None = None):
        self.executed: list[str] = []
        self.fail_at = fail_at

    def _run(self, name):
        def method(context):
            if name == self.fail_at:
                raise RuntimeError(f"simulated crash at {name}")
            self.executed.append(name)
            context.phase_log.append(name)
            return context
        return method

    def __getattr__(self, item):
        if item.startswith("run_") and item.endswith("_phase"):
            return self._run(item[len("run_"):-len("_phase")])
        raise AttributeError(item)


def test_runs_all_phases_without_client():
    ctx = _ctx()
    result = run_phases_with_checkpoint(FakeRunner(), ctx, client=None, run_db_id=7)
    assert result.phase_log == [n for n, _ in PHASE_SEQUENCE]


def test_resumes_from_checkpoint(fake_client):
    """testing 完了済みなら review だけ実行・snapshot復元"""
    ctx = _ctx()
    ctx.plan = {"done": True}
    mark_phase_done(fake_client, 7, "testing", ctx)

    runner = FakeRunner()
    result = run_phases_with_checkpoint(runner, ctx, client=fake_client, run_db_id=7)
    assert runner.executed == ["review"]
    assert result.plan == {"done": True}


def test_marks_each_phase(fake_client):
    run_phases_with_checkpoint(FakeRunner(), _ctx(), client=fake_client, run_db_id=8)
    last_done, _ = load_checkpoint(fake_client, 8)
    assert last_done == "review"  # 単一キー=最後のphase


def test_crash_keeps_earlier_checkpoint(fake_client):
    """crash例外は伝播させる（実運用ではworker死亡に相当）・直前phaseのcheckpointは保持"""
    with pytest.raises(RuntimeError, match="simulated crash at implementation"):
        run_phases_with_checkpoint(FakeRunner(fail_at="implementation"), _ctx(), client=fake_client, run_db_id=9)
    last_done, _ = load_checkpoint(fake_client, 9)
    assert last_done == "architecture"  # crash(implementation)直前に完了したphase

    runner2 = FakeRunner()
    run_phases_with_checkpoint(runner2, _ctx(), client=fake_client, run_db_id=9)
    assert runner2.executed == ["implementation", "testing", "review"]


def test_heartbeat_fn_called_per_phase(fake_client):
    """A3: 各phase完了後に heartbeat_fn が呼ばれる"""
    calls: list[str] = []
    run_phases_with_checkpoint(
        FakeRunner(), _ctx(), client=fake_client, run_db_id=10,
        heartbeat_fn=lambda: calls.append("beat"),
    )
    assert len(calls) == len(PHASE_SEQUENCE)


def test_heartbeat_fn_failure_does_not_break_run(fake_client):
    """heartbeat_fn が例外を吐いても phase 実行は継続"""
    def boom():
        raise ConnectionError("redis down")
    result = run_phases_with_checkpoint(
        FakeRunner(), _ctx(), client=fake_client, run_db_id=11, heartbeat_fn=boom,
    )
    assert len(result.phase_log) == len(PHASE_SEQUENCE)


def test_run_db_id_none_disables_checkpoint(fake_client):
    runner = FakeRunner()
    run_phases_with_checkpoint(runner, _ctx(), client=fake_client, run_db_id=None, heartbeat_fn=None)
    assert len(runner.executed) == len(PHASE_SEQUENCE)
    assert not fake_client.keys("checkpoint:*")


def test_run_full_project_delegates_to_checkpoint(monkeypatch, tmp_path):
    """run_full_project が run_phases_with_checkpoint へ phase 実行と heartbeat_fn を委譲する"""
    from nexuscore.core import orchestrator as orch_mod
    from nexuscore.core.orchestrator import Orchestrator

    calls: dict = {}

    def fake_run_phases(runner, context, client, run_db_id, heartbeat_fn=None):
        calls["run_db_id"] = run_db_id
        calls["heartbeat_fn"] = heartbeat_fn
        return context

    monkeypatch.setattr(orch_mod, "run_phases_with_checkpoint", fake_run_phases)

    def beat():
        return None

    orch = Orchestrator.__new__(Orchestrator)
    orch.project_path = str(tmp_path)
    orch.constitution = {"automation_policy": {}}
    orch.logger = logging.getLogger("test-orch")
    orch._maybe_stop = lambda phase, extra=None: None
    orch._log_orch_event = lambda *a, **k: None

    orch.run_full_project(user_requirement="req", run_db_id=42, heartbeat_fn=beat)
    assert calls["run_db_id"] == 42
    assert calls["heartbeat_fn"] is beat


def test_llm_cache_key_format():
    """A4: フルハッシュ64hex×2"""
    k = llm_cache_key(model="m1", task="code", system_prompt="sp", user_prompt="up")
    parts = k.split(":")
    assert len(parts) == 3 and len(parts[1]) == 64 and len(parts[2]) == 64


def test_llm_cache_key_distinguishes_inputs():
    assert llm_cache_key("m", "t", "sp", "a") != llm_cache_key("m", "t", "sp", "b")


def test_llm_cache_set_get_roundtrip(fake_client):
    k = llm_cache_key("m", "t", "sp", "up")
    assert llm_cache_get(fake_client, k) is None
    llm_cache_set(fake_client, k, "cached result", ttl=60)
    assert llm_cache_get(fake_client, k) == "cached result"


def test_llm_cache_failure_is_passthrough(fake_client, monkeypatch):
    def boom(*a, **kw):
        raise ConnectionError("redis down")

    k = llm_cache_key("m", "t", "sp", "up")
    monkeypatch.setattr(fake_client, "get", boom)
    assert llm_cache_get(fake_client, k) is None
    monkeypatch.setattr(fake_client, "set", boom)
    llm_cache_set(fake_client, k, "v", ttl=60)  # 例外なし
