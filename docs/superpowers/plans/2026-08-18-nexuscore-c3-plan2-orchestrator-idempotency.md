# NexusCore C3 Plan2: Orchestrator 内部冪等性（phase チェックポイント＋LLM 結果キャッシュ）Implementation Plan — v2

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **v2**: マルチLLMレビュー（MiniMax18+Gemini3・採用10）+ sentaku L3弁証論（A3合成案）を反映。改訂の正典: `obsidian-ssot/00_SYSTEM/マルチLLMレビュー/2026-08-18_C3Plan2設計レビュー/revised_proposal.md`（Amendment 2まで）

**Goal:** Celery worker が Orchestrator 実行中に死亡してタスクが再配送された際、完了済み phase をスキップし、LLM 呼び出しをキャッシュして再実行コストをゼロに近づける（改訂案 2026-08-06 採用7項目 #4 の実装）。

**Architecture:** phase 完了ごとに **単一キー `checkpoint:{run_db_id}`** へ「last_done + コンテキストスナップショット(JSON)」を **1回の SET（アトミック）** で書き、再実行時はスナップショットを復元して未完了 phase から再開する。phase ループは `Orchestrator` クラスからスタンドアロン関数 `run_phases_with_checkpoint()`（`core/run_checkpoint.py`）へ分離し、duck-typing でテスト可能にする。LLM 呼び出しは唯一の choke point である `_execute_task_via_npe` に `llm_cache:{...}` GET/SETEX を挟む（**第二防御線**: snapshot復元不能時の再実行コスト削減が役割）。実行ロックは **TTL 600s + phase完了時heartbeat + ロック失敗時は遅延retry**（タスク消失防止）。Redis 障害時はすべて pass-through（timeout 1s + 60sサーキットブレーカ付き）に退化し、既存動作を壊さない。

**Tech Stack:** Python 3.12 / Redis（`redis` py client・Celery broker と同じ URL）/ fakeredis（テスト）/ pytest

**前提と失敗モード（A9）**: Plan1はRedis必須（重複実行防止）・Plan2はRedis任意（不要な再実行防止）で**失敗モードが異なる**。実測: `visibility_timeout=7200s`（docker-compose.saas.yml）/ 3600s（デフォルト）・acks_late=1。**choke point注記**: phase内で `_execute_task_via_npe` 以外のLLM直接呼出を追加しないこと（追加するとキャッシュを抜ける）。

**前提（Plan1 実装済み・本 planでは触らない）:** `webapp/task_lock.py`（分散ロック・heartbeat関数あり）・producer 側ガード・NotificationLog。※`_acquire_execution_lock` のTTLとskip挙動は**本plan Task 7で修正する**。

**設計上の重要決定（v2）:**
1. **層序**: `core/run_checkpoint.py` に新設・Redis取得は同module内独自定義（timeout付き・A2）。heartbeatは**`heartbeat_fn` として依存注入**（core→webapp import回避）。
2. **単一キー1回SET（A1・両LLM一致critical）**: 2キー分離の非アトミック性を構造解消。`schema_version:1` 入り・破損/version不一致は「無し」と扱いフル再実行。
3. **clear_checkpoints は SUCCESS 時のみ**: FAILED 時は保持し autoretry 再実行が途中から再開。TTL 24h で自動消滅。
4. **run_db_id=None（CLI 直接実行）はチェックポイント無効**。
5. **LLM キャッシュは成功結果のみ・フルハッシュ64hex（A4）・env `NEXUSCORE_LLM_CACHE=0` で kill-switch**。
6. **512KB超スナップショットはzlib圧縮（A5）**・`json.dumps`失敗はERRORログで可視化（A6）。
7. **ロック3リスク対策（A3合成案・L3弁証論）**: ①並走=TTL600s+phase完了heartbeat ②タスク消失=ロック失敗時`self.retry(countdown=660)` ③再開不能=不変条件`TTL<visibility_timeout`のCIテスト。

---

## File Structure

- Create: `src/nexuscore/core/run_checkpoint.py` — チェックポイント（単一キー）・`run_phases_with_checkpoint()`・LLM キャッシュ helper・サーキットブレーカ
- Create: `tests/core/test_run_checkpoint.py` — fakeredis テスト（新規約24件）
- Modify: `src/nexuscore/core/orchestrator.py:162-170` — 7 phase 直列呼び出しを `run_phases_with_checkpoint()` へ置換（`heartbeat_fn` 受渡し追加）
- Modify: `src/nexuscore/webapp/orchestrator_helper.py:78` — `run_orchestrator_sync` に `heartbeat_fn` 引数追加
- Modify: `src/nexuscore/core/phase_runner_mixin.py:79-111` — `_execute_task_via_npe` に LLM キャッシュ挿入
- Modify: `src/nexuscore/webapp/celery_app.py` — TTL600s化・ロック失敗時retry・heartbeat_fn注入・SUCCESS時clear
- Modify: `docs/変更履歴.md`

---

### Task 1: run_checkpoint.py 基盤（PHASE_SEQUENCE・単一キー・get_client+ブレーカ）

**Files:**
- Create: `src/nexuscore/core/run_checkpoint.py`
- Create: `tests/core/test_run_checkpoint.py`

- [ ] **Step 1: failing test を書く**

```python
"""run_checkpoint（C3 Plan2・Orchestrator内部冪等性）のテスト。fakeredis 使用。"""
import logging

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
```

- [ ] **Step 2: test fail を確認**

Run: `PYTHONPATH=src python -m pytest tests/core/test_run_checkpoint.py -v`
Expected: FAIL（`ModuleNotFoundError`）

- [ ] **Step 3: run_checkpoint.py を実装**

```python
"""Orchestrator 内部冪等性（C3 Plan2）: phase チェックポイント＋LLM 結果キャッシュ。

Celery worker 死亡→再配送時に完了済み phase をスキップし、
コンテキストスナップショットから再開するための基盤。
Redis 障害時はすべて no-op（timeout 1s + 60sサーキットブレーカ付きのフル再実行に退化）。

層序注記: webapp.task_lock と同じ env 変数を参照する独自実装
（core → webapp import は層序違反のため避ける）。heartbeat は heartbeat_fn で依存注入。
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict
from typing import Any, Callable

logger = logging.getLogger(__name__)

PHASE_SEQUENCE: list[tuple[str, str]] = [
    ("context", "run_context_phase"),
    ("requirements", "run_requirements_phase"),
    ("planning", "run_planning_phase"),
    ("architecture", "run_architecture_phase"),
    ("implementation", "run_implementation_phase"),
    ("testing", "run_testing_phase"),
    ("review", "run_review_phase"),
]
PHASE_INDEX: dict[str, int] = {name: i for i, (name, _) in enumerate(PHASE_SEQUENCE)}

_CHECKPOINT_TTL = 86400        # 24h（改訂案指定）
_SNAPSHOT_MAX_BYTES = 512 * 1024  # A5: 超過時はzlib圧縮
LOCK_TTL = 600                 # A3: 1phase（LLM数回×数十秒）をカバーし visibility_timeout(7200) < に収める

# A2: 簡易サーキットブレーカ（Redis失敗後60s間はget_client即None）
_BREAKER_COOLDOWN = 60.0
_breaker_until = 0.0


def _note_failure() -> None:
    global _breaker_until
    _breaker_until = time.monotonic() + _BREAKER_COOLDOWN


def get_client() -> Any | None:
    """Redis クライアント。NEXUSCHECKPOINT=0 で None。ブレーカ作動中も None。"""
    if os.getenv("NEXUSCORE_CHECKPOINT", "1") == "0":
        return None
    if time.monotonic() < _breaker_until:
        return None
    try:
        import redis

        url = os.getenv("REDIS_URL") or os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
        return redis.from_url(url, socket_connect_timeout=1.0, socket_timeout=1.0)
    except Exception:  # noqa: BLE001
        _note_failure()
        return None


def checkpoint_key(run_db_id: int) -> str:
    """A1: チェックポイント単一キー（last_done+contextを1エントリで保持）"""
    return f"checkpoint:{run_db_id}"
```

（`tests/core/__init__.py` が無ければ空ファイル作成。）

- [ ] **Step 4: test pass を確認**

Run: `PYTHONPATH=src python -m pytest tests/core/test_run_checkpoint.py -v`
Expected: 5 PASSED

- [ ] **Step 5: commit**

```bash
git add src/nexuscore/core/run_checkpoint.py tests/core/test_run_checkpoint.py tests/core/__init__.py
git commit -m "feat(c3p2): run_checkpoint基盤（単一キー・timeout+ブレーカ付きget_client・不変条件テスト）"
```

---

### Task 2: mark_phase_done / load_checkpoint / clear_checkpoints（単一キー・圧縮・schema_version）

**Files:**
- Modify: `src/nexuscore/core/run_checkpoint.py`
- Modify: `tests/core/test_run_checkpoint.py`

- [ ] **Step 1: failing test を書く（追記）**

```python
from nexuscore.core.orchestrator_models import OrchestratorContext
from nexuscore.core.run_checkpoint import (
    clear_checkpoints,
    load_checkpoint,
    mark_phase_done,
)


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
    ctx2 = _ctx(); ctx2.plan = {"p": 2}
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
    mark_phase_done(fake_client=None or fakeredis.FakeStrictRedis(), 1, "planning", ctx)
    _, restored = load_checkpoint(fakeredis.FakeStrictRedis(), 1) if False else (None, None)
    # ↑ client を都度作ると別インスタンスになるため、単一インスタンスで:
    fc = fakeredis.FakeStrictRedis()
    mark_phase_done(fc, 1, "planning", ctx)
    _, restored = load_checkpoint(fc, 1)
    assert restored.debug_history == ctx.debug_history
    assert restored.review_report == ctx.review_report
```

（`test_context_roundtrip_ci_guard` の上2行の冗長な行は実装時に削除して `fc = fakeredis.FakeStrictRedis()` から始めること。）

- [ ] **Step 2: test fail を確認**

Run: `PYTHONPATH=src python -m pytest tests/core/test_run_checkpoint.py -v`
Expected: 新規8件 FAIL（`ImportError`）

- [ ] **Step 3: run_checkpoint.py に関数を追記**

```python
def mark_phase_done(client: Any, run_db_id: int, phase: str, context: Any) -> None:
    """A1: 単一キー1回SET（アトミック）。A5: 512KB超はzlib+base64。"""
    try:
        payload = json.dumps(
            {"schema_version": 1, "last_done": phase, "context": asdict(context)},
            ensure_ascii=False,
        ).encode("utf-8")
        if len(payload) > _SNAPSHOT_MAX_BYTES:
            import base64
            import zlib

            payload = b"C" + base64.b64encode(zlib.compress(payload))
        else:
            payload = b"R" + payload
        client.set(checkpoint_key(run_db_id), payload, ex=_CHECKPOINT_TTL)
        logger.info("checkpoint saved (run_db_id=%s phase=%s bytes=%d)", run_db_id, phase, len(payload))  # A7
    except TypeError:
        # A6: シリアライズ不能型の混入＝実装バグ。サイレント退化を防ぐためERRORで可視化
        logger.error(
            "checkpoint serialize failed (run_db_id=%s phase=%s): contextにJSON不能型が混入の疑い",
            run_db_id, phase, exc_info=True,
        )
    except Exception:  # noqa: BLE001 — Redis 障害はチェックポイント放棄で継続
        _note_failure()
        logger.warning("checkpoint write failed (run_db_id=%s phase=%s)", run_db_id, phase, exc_info=True)


def load_checkpoint(client: Any | None, run_db_id: int) -> tuple[str | None, Any | None]:
    """last_done と復元済み context。無し/破損/スキーマ不一致は (None, None)。"""
    if client is None:
        return None, None
    try:
        raw = client.get(checkpoint_key(run_db_id))
        if raw is None:
            return None, None
        if raw[:1] == b"C":
            import base64
            import zlib

            payload = zlib.decompress(base64.b64decode(raw[1:])).decode("utf-8")
        else:
            payload = raw[1:].decode("utf-8")
        data = json.loads(payload)
        if data.get("schema_version") != 1:
            logger.warning("checkpoint schema mismatch (run_db_id=%s) -> discard", run_db_id)
            return None, None
        from nexuscore.core.orchestrator_models import OrchestratorContext

        restored = OrchestratorContext(**data["context"])
        logger.info("checkpoint restore (run_db_id=%s last_done=%s)", run_db_id, data.get("last_done"))  # A7
        return data.get("last_done"), restored
    except Exception:  # noqa: BLE001
        _note_failure()
        logger.warning("checkpoint load failed (run_db_id=%s)", run_db_id, exc_info=True)
        return None, None


def clear_checkpoints(client: Any | None, run_db_id: int) -> None:
    """SUCCESS 確定時のみ呼ぶ。FAILED 時は保持して retry の再開に使う。"""
    if client is None:
        return
    try:
        client.delete(checkpoint_key(run_db_id))
    except Exception:  # noqa: BLE001
        _note_failure()
        logger.warning("checkpoint clear failed (run_db_id=%s)", run_db_id, exc_info=True)
```

- [ ] **Step 4: test pass を確認**

Run: `PYTHONPATH=src python -m pytest tests/core/test_run_checkpoint.py -v`
Expected: 13 PASSED

- [ ] **Step 5: commit**

```bash
git add src/nexuscore/core/run_checkpoint.py tests/core/test_run_checkpoint.py
git commit -m "feat(c3p2): mark/load/clear（単一キー・zlib圧縮・schema_version・dumps失敗ERROR可視化）"
```

---

### Task 3: run_phases_with_checkpoint（phase ループ分離・heartbeat_fn注入）

**Files:**
- Modify: `src/nexuscore/core/run_checkpoint.py`
- Modify: `tests/core/test_run_checkpoint.py`

- [ ] **Step 1: failing test を書く（追記）**

```python
from nexuscore.core.run_checkpoint import run_phases_with_checkpoint


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
    run_phases_with_checkpoint(FakeRunner(fail_at="implementation"), _ctx(), client=fake_client, run_db_id=9)
    last_done, _ = load_checkpoint(fake_client, 9)
    assert last_done == "planning"

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
```

- [ ] **Step 2: test fail を確認**

Run: `PYTHONPATH=src python -m pytest tests/core/test_run_checkpoint.py -v`
Expected: 新規7件 FAIL（`ImportError`）

- [ ] **Step 3: run_checkpoint.py に関数を追記**

```python
def run_phases_with_checkpoint(
    runner: Any,
    context: Any,
    client: Any | None,
    run_db_id: int | None,
    heartbeat_fn: Callable[[], None] | None = None,
) -> Any:
    """phase 直列実行＋チェックポイント。

    runner: run_<name>_phase(context) を持つオブジェクト（Orchestrator 本体）。
    heartbeat_fn: 各phase完了時に呼ぶ実行ロックTTL延長（A3・依存注入で層序維持）。
    """
    last_done, restored = load_checkpoint(client, run_db_id) if run_db_id is not None else (None, None)
    if restored is not None:
        context = restored
        logger.info("resuming run_db_id=%s after phase '%s' (checkpoint restore)", run_db_id, last_done)

    start = 0 if last_done is None else PHASE_INDEX[last_done] + 1
    for name, method_name in PHASE_SEQUENCE[start:]:
        context = getattr(runner, method_name)(context)
        if client is not None and run_db_id is not None:
            mark_phase_done(client, run_db_id, name, context)
        if heartbeat_fn is not None:
            try:
                heartbeat_fn()
            except Exception:  # noqa: BLE001 — heartbeat失敗でrunは止めない
                logger.warning("lock heartbeat failed (run_db_id=%s)", run_db_id, exc_info=True)
    return context
```

- [ ] **Step 4: test pass を確認**

Run: `PYTHONPATH=src python -m pytest tests/core/test_run_checkpoint.py -v`
Expected: 20 PASSED

- [ ] **Step 5: commit**

```bash
git add src/nexuscore/core/run_checkpoint.py tests/core/test_run_checkpoint.py
git commit -m "feat(c3p2): run_phases_with_checkpoint（完了phase skip・heartbeat_fn依存注入・例外でもrun継続）"
```

---

### Task 4: orchestrator / orchestrator_helper 統合（heartbeat_fn 受渡し）

**Files:**
- Modify: `src/nexuscore/core/orchestrator.py:140-170`
- Modify: `src/nexuscore/webapp/orchestrator_helper.py:78-107`
- Modify: `tests/core/test_run_checkpoint.py`

- [ ] **Step 1: failing test を書く（追記）**

```python
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

    beat = lambda: None  # noqa: E731
    orch = Orchestrator.__new__(Orchestrator)
    orch.project_path = str(tmp_path)
    orch.constitution = {"automation_policy": {}}
    orch.logger = logging.getLogger("test-orch")
    orch._maybe_stop = lambda phase, extra=None: None
    orch._log_orch_event = lambda *a, **k: None

    orch.run_full_project(user_requirement="req", run_db_id=42, heartbeat_fn=beat)
    assert calls["run_db_id"] == 42
    assert calls["heartbeat_fn"] is beat
```

- [ ] **Step 2: test fail を確認**

Run: `PYTHONPATH=src python -m pytest tests/core/test_run_checkpoint.py::test_run_full_project_delegates_to_checkpoint -v`
Expected: FAIL（`run_full_project` が `heartbeat_fn` を受け取らない TypeError）

- [ ] **Step 3: 両ファイルを修正**

`orchestrator.py` import部に追加:

```python
from nexuscore.core.run_checkpoint import (
    get_client as _checkpoint_client,
    run_phases_with_checkpoint,
)
from typing import Callable  # （既存 typing import に統合可）
```

`run_full_project` シグネチャとphaseループ部を修正:

```python
    def run_full_project(
        self,
        user_requirement: str,
        language: str = "ja",
        fast_lane: bool = False,
        run_db_id: int | None = None,
        heartbeat_fn: Callable[[], None] | None = None,
    ) -> OrchestratorContext | None:
```

（162-170行の7 phase呼び出しを置換）

```python
            self._maybe_stop("start", {"task_id": task_id, "requirement": user_requirement})
            checkpoint_client = _checkpoint_client() if run_db_id is not None else None
            context = run_phases_with_checkpoint(
                self, context, client=checkpoint_client, run_db_id=run_db_id,
                heartbeat_fn=heartbeat_fn,
            )
```

`orchestrator_helper.py` の `run_orchestrator_sync` に `heartbeat_fn: Callable[[], None] | None = None` 引数を追加し、`orchestrator.run_full_project(...)` 呼び出しに `heartbeat_fn=heartbeat_fn` を渡す。

- [ ] **Step 4: test pass を確認＋回帰**

Run: `PYTHONPATH=src python -m pytest tests/core/ -q`
Expected: 全 PASSED

- [ ] **Step 5: commit**

```bash
git add src/nexuscore/core/orchestrator.py src/nexuscore/webapp/orchestrator_helper.py tests/core/test_run_checkpoint.py
git commit -m "feat(c3p2): phaseループをrun_phases_with_checkpointへ委譲+heartbeat_fn経路貫通（CLI=無効）"
```

---

### Task 5: LLM 結果キャッシュ helper（フルハッシュ）

**Files:**
- Modify: `src/nexuscore/core/run_checkpoint.py`
- Modify: `tests/core/test_run_checkpoint.py`

- [ ] **Step 1: failing test を書く（追記）**

```python
from nexuscore.core.run_checkpoint import llm_cache_get, llm_cache_key, llm_cache_set


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
```

- [ ] **Step 2: test fail を確認**

Run: `PYTHONPATH=src python -m pytest tests/core/test_run_checkpoint.py -v`
Expected: 新規4件 FAIL（`ImportError`）

- [ ] **Step 3: run_checkpoint.py に追記**

```python
import hashlib


def llm_cache_key(model: str, task: str, system_prompt: str, user_prompt: str) -> str:
    """llm_cache:{prompt_hash}:{input_hash}（A4: フル64hex・衝突回避）。"""
    prompt_hash = hashlib.sha256(f"{model}|{task}|{system_prompt}".encode("utf-8")).hexdigest()
    input_hash = hashlib.sha256(user_prompt.encode("utf-8")).hexdigest()
    return f"llm_cache:{prompt_hash}:{input_hash}"


def llm_cache_get(client: Any | None, key: str) -> str | None:
    if client is None:
        return None
    try:
        raw = client.get(key)
        return raw.decode("utf-8") if raw is not None else None
    except Exception:  # noqa: BLE001
        _note_failure()
        return None


def llm_cache_set(client: Any | None, key: str, value: str, ttl: int = 86400) -> None:
    if client is None:
        return
    try:
        client.set(key, value, ex=ttl)
    except Exception:  # noqa: BLE001
        _note_failure()
        logger.warning("llm_cache set failed (key=%s...)", key[:32], exc_info=True)
```

- [ ] **Step 4: test pass を確認**

Run: `PYTHONPATH=src python -m pytest tests/core/test_run_checkpoint.py -v`
Expected: 25 PASSED（+1 delegation test = 26）

- [ ] **Step 5: commit**

```bash
git add src/nexuscore/core/run_checkpoint.py tests/core/test_run_checkpoint.py
git commit -m "feat(c3p2): LLM結果キャッシュ helper（フルハッシュ・TTL24h・障害時passthrough）"
```

---

### Task 6: _execute_task_via_npe へキャッシュ統合

**Files:**
- Modify: `src/nexuscore/core/phase_runner_mixin.py:79-111`
- Test: `tests/core/test_run_checkpoint.py`

- [ ] **Step 1: failing test を書く（追記）**

```python
def test_execute_task_via_npe_uses_llm_cache(fake_client, monkeypatch):
    """同一 prompt の2回目は LLM を呼ばずキャッシュを返す"""
    from nexuscore.core import phase_runner_mixin as prm

    call_count = {"n": 0}

    def fake_guarded_llm_call(**kwargs):
        call_count["n"] += 1
        return {"content": "LLM said: hello"}

    class DummyMixin(prm.PhaseRunnerMixin):
        logger = logging.getLogger("test-mixin")

    monkeypatch.setattr(prm, "guarded_llm_call", fake_guarded_llm_call)
    monkeypatch.setattr(prm, "_llm_cache_client", lambda: fake_client)
    mixin = DummyMixin()

    first = mixin._execute_task_via_npe("build a function", {"task_type": "code"})
    second = mixin._execute_task_via_npe("build a function", {"task_type": "code"})
    assert first == second
    assert call_count["n"] == 1


def test_execute_task_via_npe_cache_disabled(monkeypatch):
    """kill-switch（client=None）では毎回 LLM を呼ぶ"""
    from nexuscore.core import phase_runner_mixin as prm

    call_count = {"n": 0}

    def fake_guarded_llm_call(**kwargs):
        call_count["n"] += 1
        return {"content": "fresh"}

    class DummyMixin(prm.PhaseRunnerMixin):
        logger = logging.getLogger("test-mixin")

    monkeypatch.setattr(prm, "guarded_llm_call", fake_guarded_llm_call)
    monkeypatch.setattr(prm, "_llm_cache_client", lambda: None)
    mixin = DummyMixin()
    mixin._execute_task_via_npe("p", {"task_type": "code"})
    mixin._execute_task_via_npe("p", {"task_type": "code"})
    assert call_count["n"] == 2
```

- [ ] **Step 2: test fail を確認**

Run: `PYTHONPATH=src python -m pytest tests/core/test_run_checkpoint.py -k npe -v`
Expected: FAIL（`_llm_cache_client` 無し）

- [ ] **Step 3: phase_runner_mixin.py を修正**

module import 部に追加:

```python
import os as _os

from nexuscore.core.run_checkpoint import (
    get_client as _rc_get_client,
    llm_cache_get,
    llm_cache_key,
    llm_cache_set,
)


def _llm_cache_client():
    """LLM キャッシュ用 Redis client（NEXUSCORE_LLM_CACHE=0 で None）。"""
    if _os.getenv("NEXUSCORE_LLM_CACHE", "1") == "0":
        return None
    return _rc_get_client()
```

`_execute_task_via_npe` 内の `result = guarded_llm_call(...)` 以降を置換:

```python
        cache_client = _llm_cache_client()
        cache_key = llm_cache_key(
            model=model, task=task_type, system_prompt=system_prompt, user_prompt=prompt,
        )
        cached = llm_cache_get(cache_client, cache_key)
        if cached is not None:
            self.logger.info(f"[NPE] LLM cache hit (task='{task_type}')")  # A7
            return cached
        self.logger.info(f"[NPE] LLM cache miss (task='{task_type}')")  # A7

        result = guarded_llm_call(
            model=model,
            task=task_type,
            system_prompt=system_prompt,
            user_prompt=prompt,
            llm_complete_fn=self.llm_router.complete,
        )

        if isinstance(result, dict):
            content = result.get("content", "")
        else:
            content = str(result)

        try:
            from nexuscore.utils.clean_output import clean_output

            cleaned = clean_output(content)
        except Exception:  # noqa: BLE001
            cleaned = content

        llm_cache_set(cache_client, cache_key, cleaned)
        return cleaned
```

- [ ] **Step 4: test pass を確認**

Run: `PYTHONPATH=src python -m pytest tests/core/test_run_checkpoint.py -v`
Expected: 28 PASSED

- [ ] **Step 5: commit**

```bash
git add src/nexuscore/core/phase_runner_mixin.py tests/core/test_run_checkpoint.py
git commit -m "feat(c3p2): _execute_task_via_npeにLLMキャッシュ統合（hit/missログ・kill-switch）"
```

---

### Task 7: celery_app 統合（TTL600s・ロック失敗retry・heartbeat_fn・SUCCESS時clear）

**Files:**
- Modify: `src/nexuscore/webapp/celery_app.py:196-220, 246-250, 291-293`
- Modify: `tests/webapp/test_celery_job_state_machine.py`
- Modify: `docs/変更履歴.md`

- [ ] **Step 1: failing test を書く（追記）**

```python
def test_lock_ttl_and_retry_on_lock_failure(...):
    """A3: (1) ロックTTL=600s (2) ロック失敗時はskipでなく遅延retry（タスク消失防止）"""
    # 既存 test_celery_task_state_transition_* のモック構成を流用し:
    # 1) _acquire_execution_lock 経由の TTL が run_checkpoint.LOCK_TTL(600) であること
    # 2) task_lock.acquire_lock が False を返すよう差し替えた場合、
    #    タスク呼出が celery.exceptions.Retry を raise すること（skip-return でないこと）
```

（具体的assertは既存テストのfixture構成に合わせて実装時補完・`pytest.raises(Retry)` を使う。）

```python
def test_heartbeat_fn_passed_to_run(monkeypatch, fake_client):
    """A3: celeryタスクがheartbeat_fnをorchestratorへ注入する"""
    from nexuscore.webapp import celery_app as ca
    captured = {}
    monkeypatch.setattr(ca, "run_orchestrator_sync", lambda **kw: captured.update(kw) or None)
    # 既存成功テストのRun/Projectモック構成を流用してタスク実行
    assert callable(captured.get("heartbeat_fn"))
```

```python
def test_clear_checkpoints_on_success(...):
    """SUCCESS確定時に checkpoint がクリアされる（FAILED は残る）"""
    from nexuscore.core import run_checkpoint as rc
    # 成功テスト構成を流用し run_db_id=101 で実行:
    #   rc.mark_phase_done(fake_client, 101, "planning", ctx) を事前に打ち
    #   実行後 assert rc.load_checkpoint(fake_client, 101) == (None, None)
```

- [ ] **Step 2: test fail を確認**

Run: `PYTHONPATH=src python -m pytest tests/webapp/test_celery_job_state_machine.py -k "lock_ttl or heartbeat_fn or clear_checkpoint" -v`
Expected: FAIL

- [ ] **Step 3: celery_app.py を修正**

`_acquire_execution_lock`（196-220行）:

```python
    if not task_lock.acquire_lock(client, lock_key, worker_id, ttl=run_checkpoint.LOCK_TTL):
        return (False, client, lock_key)
```

（`from nexuscore.core import run_checkpoint` をimport・TTL 30s→LOCK_TTL 600s・task_lock.py側のデフォルトTTLは触らない）

タスク本体（246-250行）:

```python
        worker_id = self.request.id or f"direct-{uuid.uuid4().hex}"
        can_run, redis_client, lock_key = _acquire_execution_lock(run, worker_id)
        if run.status == "SUCCESS":
            logger.info(f"Run {run_db_id} skipped by idempotency guard (already SUCCESS)")
            return
        if not can_run:
            # A3: skip-return-ACK だと再配送workerが消えてタスク消失する。
            # ロック残り<TTL(600s)後に遅延再試行させる（retryはautoretry_forと別系統・
            # max_retries到達で失敗終了するため有界）
            logger.info(f"Run {run_db_id} locked by another worker -> retry in 660s")
            raise self.retry(countdown=run_checkpoint.LOCK_TTL + 60)
```

heartbeat_fn 作成とorchestrator呼出（`run_orchestrator_sync` 呼び出し部）:

```python
                heartbeat_fn = (
                    lambda: task_lock.heartbeat(redis_client, lock_key, worker_id, ttl=run_checkpoint.LOCK_TTL)
                    if redis_client is not None else None
                )
                run_orchestrator_sync(
                    project_path=project.local_path,
                    user_requirement=run.requirement,
                    run_db_id=run.id,
                    autonomy_level=run.autonomy_level or 1,
                    language="ja",
                    fast_lane=False,
                    heartbeat_fn=heartbeat_fn,
                )
```

（`from nexuscore.webapp import task_lock` は関数内既存importを利用）

SUCCESS確定部（291-293行 `run.status = "SUCCESS"` の直後）:

```python
                # C3 Plan2: SUCCESS 確定時のみチェックポイント掃除
                # （FAILED は保持→autoretry の再実行が途中再開する・TTL 24h で自動消滅）
                from nexuscore.core import run_checkpoint as _rc

                _rc.clear_checkpoints(_rc.get_client(), run.id)
```

- [ ] **Step 4: test pass を確認**

Run: `PYTHONPATH=src python -m pytest tests/webapp/test_celery_job_state_machine.py tests/core/test_run_checkpoint.py -q`
Expected: 全 PASSED

- [ ] **Step 5: 変更履歴に追記**

`docs/変更履歴.md` の 2026-08-18 エントリに統合:

```markdown
### Added（C3 Plan2・Orchestrator内部冪等性・マルチLLMレビュー+L3弁証論反映）
- `core/run_checkpoint.py`: チェックポイント単一キー`checkpoint:{run_db_id}`（1回SET=アトミック・schema_version・512KB超zlib圧縮）＋`run_phases_with_checkpoint()`（完了phase skip・heartbeat_fn依存注入）＋LLM結果キャッシュ（フルハッシュ・TTL24h）＋timeout1s+60sサーキットブレーカ
- `orchestrator.py`/`orchestrator_helper.py`: phaseループ委譲＋heartbeat_fn経路貫通（CLI実行=run_db_id Noneは無効）
- `_execute_task_via_npe`: LLMキャッシュhit時guarded_llm_call skip（hit/missログ・`NEXUSCORE_LLM_CACHE=0`/`NEXUSCORE_CHECKPOINT=0`で無効化）
- `celery_app.py`: 実行ロックTTL 30s→600s+phase完了heartbeat（並走防止）・ロック失敗時は660s後retry（タスク消失防止）・不変条件`LOCK_TTL<visibility_timeout`をCIテスト固定・SUCCESS時checkpointクリア
```

- [ ] **Step 6: フル回帰**

Run: `PYTHONPATH=src python -m pytest tests/ -q`
Expected: 既存緑数（約4,993）＋新規約28件 PASSED / 0 failed

- [ ] **Step 7: commit & push**

```bash
git add src/nexuscore/webapp/celery_app.py tests/webapp/test_celery_job_state_machine.py docs/変更履歴.md
git commit -m "feat(c3p2): celery統合（TTL600s+heartbeat+ロック失敗retry+SUCCESS時clear）でOrchestrator内部冪等性完結"
git push
```

- [ ] **Step 8: CI確認（効果-証跡対応ゲート）**

Run: `gh run watch <新規run id> --exit-status`
Expected: NexusCore CI/CD・Safe Tests とも conclusion: success

---

## Self-Review 結果（v2作成時実施済み）

1. **Spec カバレッジ**: 改訂案 #4（step完了マーカー+LLM結果キャッシュTTL24h）→ Task 1-3/5-6。レビュー採用A1-A10+A3合成案→ 全Task反映。Redis実証（docker・実worker SIGKILL再開E2E）は**本plan外**→ backlog「docker導入後にRedis検証」と統合して実施（A10）。
2. **プレースホルダー**: Task 7 Step 1 の3テストは「既存モック構成流用」と構成+assertを明示（写経元指定）。Task 2 の `test_context_roundtrip_ci_guard` 冗長行は削除指示付き。他にTBD無し。
3. **型整合**: `mark_phase_done(client, run_db_id, phase, context)` / `load_checkpoint(client, run_db_id) -> (str|None, Any|None)` / `run_phases_with_checkpoint(runner, context, client, run_db_id, heartbeat_fn=None)` / `llm_cache_key(model, task, system_prompt, user_prompt)` / `checkpoint_key(run_db_id)` — 全Task同一。
