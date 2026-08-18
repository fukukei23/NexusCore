"""run_checkpoint（C3 Plan2・Orchestrator内部冪等性）のテスト。fakeredis 使用。"""
import fakeredis
import pytest
from nexuscore.core.run_checkpoint import (
    LOCK_TTL,
    PHASE_INDEX,
    PHASE_SEQUENCE,
    checkpoint_key,
    get_client,
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
