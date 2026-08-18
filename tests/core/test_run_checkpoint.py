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
    load_checkpoint,
    mark_phase_done,
)


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
