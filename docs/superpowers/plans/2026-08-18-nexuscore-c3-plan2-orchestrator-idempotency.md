# NexusCore C3 Plan2: Orchestrator 内部冪等性（phase チェックポイント＋LLM 結果キャッシュ）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Celery worker が Orchestrator 実行中に死亡してタスクが再配送された際、完了済み phase をスキップし、LLM 呼び出しをキャッシュして再実行コストをゼロに近づける（改訂案 2026-08-06 採用7項目 #4 の実装）。

**Architecture:** phase 完了ごとに Redis へ「コンテキストスナップショット（JSON）+ phase マーカー」を書き、再実行時はスナップショットを復元して未完了 phase から再開する。phase ループは `Orchestrator` クラスからスタンドアロン関数 `run_phases_with_checkpoint()`（`core/run_checkpoint.py`）へ分離し、duck-typing でテスト可能にする。LLM 呼び出しは唯一の choke point である `_execute_task_via_npe` に `llm_cache:{...}` GET/SETEX を挟む。Redis 障害時はすべて pass-through（チェックポイント無しフル再実行）に退化し、既存動作を壊さない。

**Tech Stack:** Python 3.12 / Redis（`redis` py client・Celery broker と同じ URL）/ fakeredis（テスト）/ pytest

**前提（Plan1 実装済み・本 planでは触らない）:** `webapp/task_lock.py`（分散ロック）・`webapp/celery_app.py` のタスク先頭冪等ガード（SUCCESS skip＋SETNX ロック）・producer 側ガード・NotificationLog。

**設計上の重要決定:**
1. **core→webpm import の層序違反を避ける**: チェックポイント module は `core/run_checkpoint.py` に新設し、Redis クライアント取得は同 module 内に独自定義（`webapp.task_lock.get_redis` と同一 env 変数・4行の重複は層序維持より優先）。
2. **マーカーとスナップショットの書込順**: スナップショット先・マーカー後。間で死んでも「マーカー無し＝phase 再実行」になり安全（副作用が再実行されるだけ）。
3. **`clear_checkpoints` は SUCCESS 時のみ**: FAILED 時はチェックポイントを保持し、autoretry の再実行が途中から再開するのが目的。TTL 24h で自動消滅。
4. **run_db_id=None（CLI 直接実行）はチェックポイント無効**: webapp 経由（Run レコード存在）のみ対象。
5. **LLM キャッシュは成功結果のみキャッシュ**し、env `NEXUSCORE_LLM_CACHE=0` で kill-switch。

---

## File Structure

- Create: `src/nexuscore/core/run_checkpoint.py` — phase マーカー・スナップショット・`run_phases_with_checkpoint()`・LLM キャッシュ helper の一式（責務: 「実行再開基盤」）
- Create: `tests/core/test_run_checkpoint.py` — 上記の fakeredis テスト
- Modify: `src/nexuscore/core/orchestrator.py:162-170` — 7 phase 直列呼び出しを `run_phases_with_checkpoint()` へ置換
- Modify: `src/nexuscore/core/phase_runner_mixin.py:79-111` — `_execute_task_via_npe` に LLM キャッシュ GET/SETEX を挿入
- Modify: `src/nexuscore/webapp/celery_app.py` — SUCCESS 確定時に `clear_checkpoints` を呼ぶ
- Test: `tests/core/` （新規）・`tests/webapp/test_celery_job_state_machine.py`（既存・回帰）

---

### Task 1: run_checkpoint.py 基盤（PHASE_SEQUENCE・キー・get_client）

**Files:**
- Create: `src/nexuscore/core/run_checkpoint.py`
- Create: `tests/core/test_run_checkpoint.py`

- [ ] **Step 1: failing test を書く**

```python
"""run_checkpoint（C3 Plan2・Orchestrator内部冪等性）のテスト。fakeredis 使用。"""
import fakeredis
import pytest

from nexuscore.core.run_checkpoint import (
    PHASE_SEQUENCE,
    PHASE_INDEX,
    get_client,
    phase_marker_key,
    snapshot_key,
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


def test_keys(fake_client):
    """キー名の形式"""
    assert phase_marker_key(7, "planning") == "phase_done:7:planning"
    assert snapshot_key(7) == "ctx_snapshot:7"


def test_get_client_env(monkeypatch):
    """REDIS_URL を優先し、無ければ CELERY_BROKER_URL・デフォルト localhost"""
    monkeypatch.setenv("REDIS_URL", "redis://example:6380/2")
    c = get_client()
    assert "example" in str(c.connection_pool.connection_kwargs.get("host", ""))


def test_get_client_none_when_disabled(monkeypatch):
    """NEXUSCORE_CHECKPOINT=0 で None（kill-switch・Redis 無し環境向け）"""
    monkeypatch.setenv("NEXUSCORE_CHECKPOINT", "0")
    assert get_client() is None
```

- [ ] **Step 2: test fail を確認**

Run: `PYTHONPATH=src python -m pytest tests/core/test_run_checkpoint.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'nexuscore.core.run_checkpoint'`）

- [ ] **Step 3: run_checkpoint.py を実装**

```python
"""Orchestrator 内部冪等性（C3 Plan2）: phase チェックポイント＋LLM 結果キャッシュ。

Celery worker 死亡→再配送時に完了済み phase をスキップし、
コンテキストスナップショットから再開するための基盤。
Redis 障害時はすべて no-op（フル再実行に退化）。

層序注記: webapp.task_lock.get_redis と同じ env 変数を参照する独自実装
（core → webapp import は層序違反のため避ける・4行の重複は意図的）。
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict
from typing import Any

logger = logging.getLogger(__name__)

# run_full_project の phase 呼び出し順と 1:1（orchestrator.py:164-170 と同期維持）
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

_CHECKPOINT_TTL = 86400  # 24h（改訂案指定）


def get_client() -> Any | None:
    """Redis クライアント。NEXUSCORE_CHECKPOINT=0 で None（kill-switch）。"""
    if os.getenv("NEXUSCORE_CHECKPOINT", "1") == "0":
        return None
    try:
        import redis

        url = os.getenv("REDIS_URL") or os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
        return redis.from_url(url)
    except Exception:  # noqa: BLE001 — Redis 不在でも Orchestrator は動く
        return None


def phase_marker_key(run_db_id: int, phase: str) -> str:
    return f"phase_done:{run_db_id}:{phase}"


def snapshot_key(run_db_id: int) -> str:
    return f"ctx_snapshot:{run_db_id}"
```

（`__init__.py` は `tests/core/` に既存なら不要。無ければ空ファイル作成。）

- [ ] **Step 4: test pass を確認**

Run: `PYTHONPATH=src python -m pytest tests/core/test_run_checkpoint.py -v`
Expected: 4 PASSED

- [ ] **Step 5: commit**

```bash
git add src/nexuscore/core/run_checkpoint.py tests/core/test_run_checkpoint.py
git commit -m "feat(c3p2): run_checkpoint基盤（PHASE_SEQUENCE・キー・get_client kill-switch込み）"
```

---

### Task 2: mark_phase_done / load_checkpoint（スナップショット保存・復元）

**Files:**
- Modify: `src/nexuscore/core/run_checkpoint.py`
- Modify: `tests/core/test_run_checkpoint.py`

- [ ] **Step 1: failing test を書く（追記）**

```python
from nexuscore.core.orchestrator_models import OrchestratorContext
from nexuscore.core.run_checkpoint import (
    load_checkpoint,
    mark_phase_done,
    clear_checkpoints,
)


def _ctx(**overrides):
    base = dict(task_id="t1", user_requirement="req", run_db_id=7)
    base.update(overrides)
    return OrchestratorContext(**base)


def test_mark_and_load_roundtrip(fake_client):
    """mark_phase_done 後、load_checkpoint が完了 phase と復元 context を返す"""
    ctx = _ctx()
    ctx.plan = {"functions_to_implement": ["f1"]}
    ctx.phase_log = ["context"]
    mark_phase_done(fake_client, 7, "planning", ctx)

    last_done, restored = load_checkpoint(fake_client, 7)
    assert last_done == "planning"
    assert restored is not None
    assert restored.plan == {"functions_to_implement": ["f1"]}
    assert restored.user_requirement == "req"


def test_load_no_checkpoint(fake_client):
    """マーカー無しは (None, None)→フル再実行"""
    assert load_checkpoint(fake_client, 999) == (None, None)


def test_load_marker_without_snapshot_is_ignored(fake_client):
    """マーカーだけあってスナップショットが無い=不完全書込→フル再実行に退化"""
    fake_client.set(phase_marker_key(7, "testing"), "1")
    assert load_checkpoint(fake_client, 7) == (None, None)


def test_load_takes_latest_phase(fake_client):
    """複数マーカーがある場合は最後の phase を返す"""
    mark_phase_done(fake_client, 7, "context", _ctx())
    mark_phase_done(fake_client, 7, "requirements", _ctx())
    last_done, _ = load_checkpoint(fake_client, 7)
    assert last_done == "requirements"


def test_clear_checkpoints(fake_client):
    """clear 後はフル再実行に戻る"""
    mark_phase_done(fake_client, 7, "context", _ctx())
    clear_checkpoints(fake_client, 7)
    assert load_checkpoint(fake_client, 7) == (None, None)


def test_snapshot_written_before_marker(fake_client, monkeypatch):
    """書込順: snapshot 先・marker 後（順序を担保するため set の呼び出し順を検証）"""
    calls: list[str] = []
    orig_set = fake_client.set

    def spy_set(key, value, **kw):
        calls.append(key)
        return orig_set(key, value, **kw)

    monkeypatch.setattr(fake_client, "set", spy_set)
    mark_phase_done(fake_client, 7, "context", _ctx())
    assert calls == [snapshot_key(7), phase_marker_key(7, "context")]
```

- [ ] **Step 2: test fail を確認**

Run: `PYTHONPATH=src python -m pytest tests/core/test_run_checkpoint.py -v`
Expected: 新規6件 FAIL（`ImportError: cannot import name 'load_checkpoint'`）

- [ ] **Step 3: run_checkpoint.py に関数を追記**

```python
def mark_phase_done(client: Any, run_db_id: int, phase: str, context: Any) -> None:
    """phase 完了を記録: snapshot 先・marker 後（間で死んでも marker 無し=再実行で安全）。"""
    try:
        client.set(snapshot_key(run_db_id), json.dumps(asdict(context), ensure_ascii=False), ex=_CHECKPOINT_TTL)
        client.set(phase_marker_key(run_db_id, phase), "1", ex=_CHECKPOINT_TTL)
    except Exception:  # noqa: BLE001 — Redis 障害はチェックポイント放棄で継続
        logger.warning("checkpoint write failed (run_db_id=%s phase=%s)", run_db_id, phase, exc_info=True)


def load_checkpoint(client: Any | None, run_db_id: int) -> tuple[str | None, Any | None]:
    """最後に完了した phase 名と復元済み context。無し/不完全は (None, None)。"""
    if client is None:
        return None, None
    try:
        last_done: str | None = None
        for name, _ in PHASE_SEQUENCE:
            if client.exists(phase_marker_key(run_db_id, name)):
                last_done = name
        if last_done is None:
            return None, None
        raw = client.get(snapshot_key(run_db_id))
        if raw is None:
            return None, None
        from nexuscore.core.orchestrator_models import OrchestratorContext

        restored = OrchestratorContext(**json.loads(raw))
        return last_done, restored
    except Exception:  # noqa: BLE001
        logger.warning("checkpoint load failed (run_db_id=%s)", run_db_id, exc_info=True)
        return None, None


def clear_checkpoints(client: Any | None, run_db_id: int) -> None:
    """SUCCESS 確定時のみ呼ぶ。FAILED 時は保持して retry の再開に使う。"""
    if client is None:
        return
    try:
        keys = [snapshot_key(run_db_id)] + [phase_marker_key(run_db_id, n) for n, _ in PHASE_SEQUENCE]
        client.delete(*keys)
    except Exception:  # noqa: BLE001
        logger.warning("checkpoint clear failed (run_db_id=%s)", run_db_id, exc_info=True)
```

- [ ] **Step 4: test pass を確認**

Run: `PYTHONPATH=src python -m pytest tests/core/test_run_checkpoint.py -v`
Expected: 10 PASSED

- [ ] **Step 5: commit**

```bash
git add src/nexuscore/core/run_checkpoint.py tests/core/test_run_checkpoint.py
git commit -m "feat(c3p2): mark_phase_done/load_checkpoint/clear_checkpoints（snapshot先marker後・不完全書込は退化）"
```

---

### Task 3: run_phases_with_checkpoint（phase ループ分離・スキップ再開）

**Files:**
- Modify: `src/nexuscore/core/run_checkpoint.py`
- Modify: `tests/core/test_run_checkpoint.py`

- [ ] **Step 1: failing test を書く（追記）**

```python
from nexuscore.core.run_checkpoint import run_phases_with_checkpoint


class FakeRunner:
    """run_*_phase を持つ duck-typed ランナー（実 Orchestrator の代用）"""

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
    """client=None は従来どおり全 phase 実行（チェックポイント無効）"""
    ctx = _ctx()
    result = run_phases_with_checkpoint(FakeRunner(), ctx, client=None, run_db_id=7)
    assert result.phase_log == [n for n, _ in PHASE_SEQUENCE]


def test_resumes_from_checkpoint(fake_client):
    """testing 完了済みなら review だけ実行"""
    ctx = _ctx()
    ctx.plan = {"done": True}
    mark_phase_done(fake_client, 7, "testing", ctx)

    runner = FakeRunner()
    result = run_phases_with_checkpoint(runner, ctx, client=fake_client, run_db_id=7)
    assert runner.executed == ["review"]
    assert result.plan == {"done": True}  # snapshot から復元
    assert "review" in result.phase_log


def test_marks_each_phase(fake_client):
    """各 phase 完了で marker が増える"""
    run_phases_with_checkpoint(FakeRunner(), _ctx(), client=fake_client, run_db_id=8)
    for name, _ in PHASE_SEQUENCE:
        assert fake_client.exists(phase_marker_key(8, name))


def test_crash_keeps_earlier_checkpoints(fake_client):
    """implementation で死んだ場合、planning までの marker が残る→再配送で再開可能"""
    run_phases_with_checkpoint(FakeRunner(fail_at="implementation"), _ctx(), client=fake_client, run_db_id=9)
    assert fake_client.exists(phase_marker_key(9, "planning"))
    assert not fake_client.exists(phase_marker_key(9, "implementation"))

    # 再実行（同一 run_db_id）は implementation から再開
    runner2 = FakeRunner()
    run_phases_with_checkpoint(runner2, _ctx(), client=fake_client, run_db_id=9)
    assert runner2.executed == ["implementation", "testing", "review"]


def test_run_db_id_none_disables_checkpoint(fake_client):
    """run_db_id=None（CLI 直接実行）は client があってもチェックポイントしない"""
    runner = FakeRunner()
    run_phases_with_checkpoint(runner, _ctx(), client=fake_client, run_db_id=None)
    assert len(runner.executed) == len(PHASE_SEQUENCE)
    # snapshot_key(None) に相当するキーは一切書かれない
    for key in fake_client.keys("ctx_snapshot:*") + fake_client.keys("phase_done:*"):
        assert False, f"unexpected checkpoint write: {key}"
```

- [ ] **Step 2: test fail を確認**

Run: `PYTHONPATH=src python -m pytest tests/core/test_run_checkpoint.py -v`
Expected: 新規5件 FAIL（`ImportError: cannot import name 'run_phases_with_checkpoint'`）

- [ ] **Step 3: run_checkpoint.py に関数を追記**

```python
def run_phases_with_checkpoint(
    runner: Any,
    context: Any,
    client: Any | None,
    run_db_id: int | None,
) -> Any:
    """phase 直列実行＋チェックポイント。

    runner: run_<name>_phase(context) を持つオブジェクト（Orchestrator 本体）。
    完了済み phase は snapshot 復元でスキップし、未完了から再開する。
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
    return context
```

- [ ] **Step 4: test pass を確認**

Run: `PYTHONPATH=src python -m pytest tests/core/test_run_checkpoint.py -v`
Expected: 15 PASSED

- [ ] **Step 5: commit**

```bash
git add src/nexuscore/core/run_checkpoint.py tests/core/test_run_checkpoint.py
git commit -m "feat(c3p2): run_phases_with_checkpoint（完了phase skip・クラッシュ→再配送再開のduck-typingテスト）"
```

---

### Task 4: orchestrator.py 本体統合（run_full_project の phase ループ置換）

**Files:**
- Modify: `src/nexuscore/core/orchestrator.py:162-170`
- Modify: `tests/core/test_run_checkpoint.py`

- [ ] **Step 1: failing test を書く（追記）**

```python
def test_run_full_project_delegates_to_checkpoint(monkeypatch, fake_client, tmp_path):
    """run_full_project が run_phases_with_checkpoint へ phase 実行を委譲する"""
    from nexuscore.core import run_checkpoint as rc
    from nexuscore.core.orchestrator import Orchestrator

    calls: dict[str, Any] = {}

    def fake_run_phases(runner, context, client, run_db_id):
        calls["run_db_id"] = run_db_id
        calls["client"] = client
        return context

    monkeypatch.setattr(rc, "run_phases_with_checkpoint", fake_run_phases)
    monkeypatch.setattr("nexuscore.core.orchestrator.run_phases_with_checkpoint", fake_run_phases)

    orch = Orchestrator.__new__(Orchestrator)  # agents 未設定で __init__ を回避
    orch.project_path = str(tmp_path)
    orch.constitution = {"automation_policy": {}}
    orch.logger = logging.getLogger("test-orch")
    orch._maybe_stop = lambda phase, extra=None: None
    orch._log_orch_event = lambda *a, **k: None

    result = orch.run_full_project(user_requirement="req", run_db_id=42)
    assert result is not None
    assert calls["run_db_id"] == 42
    assert calls["client"] is fake_client

    monkeypatch.setattr(rc, "get_client", lambda: fake_client)
    orch2 = Orchestrator.__new__(Orchestrator)
    orch2.project_path = str(tmp_path)
    orch2.constitution = {"automation_policy": {}}
    orch2.logger = logging.getLogger("test-orch")
    orch2._maybe_stop = lambda phase, extra=None: None
    orch2._log_orch_event = lambda *a, **k: None
    orch2.run_full_project(user_requirement="req", run_db_id=43)
    assert calls["run_db_id"] == 43
```

（`import logging` をテストファイル先頭に追加。）

- [ ] **Step 2: test fail を確認**

Run: `PYTHONPATH=src python -m pytest tests/core/test_run_checkpoint.py::test_run_full_project_delegates_to_checkpoint -v`
Expected: FAIL（`orch.run_full_project` が phase メソッドを直接呼ぼうとして AttributeError、または `calls` が空で assert 失敗）

- [ ] **Step 3: orchestrator.py を修正**

`orchestrator.py` の import 部（PhaseRunnerMixin import の近く）に追加:

```python
from nexuscore.core.run_checkpoint import (
    clear_checkpoints,
    get_client as _checkpoint_client,
    run_phases_with_checkpoint,
)
```

`run_full_project` 内 162-170 行（`self._maybe_stop(...)` の後の7行）を置換:

```python
            self._maybe_stop("start", {"task_id": task_id, "requirement": user_requirement})
            checkpoint_client = _checkpoint_client() if run_db_id is not None else None
            context = run_phases_with_checkpoint(
                self, context, client=checkpoint_client, run_db_id=run_db_id,
            )
```

（`run_context_phase` 〜 `run_review_phase` の7行は削除。fast_lane 以下の処理はそのまま。）

- [ ] **Step 4: test pass を確認**

Run: `PYTHONPATH=src python -m pytest tests/core/test_run_checkpoint.py -v`
Expected: 16 PASSED

- [ ] **Step 5: 既存 orchestrator テストの回帰**

Run: `PYTHONPATH=src python -m pytest tests/core/ -q`
Expected: 全 PASSED（run_full_project を直接叩く既存テストがある場合、phase メソッド呼び出しは委譲後も同一順序で走るため壊れないはず。壊れた場合はテスト内容を確認して個別対応）

- [ ] **Step 6: commit**

```bash
git add src/nexuscore/core/orchestrator.py tests/core/test_run_checkpoint.py
git commit -m "feat(c3p2): run_full_projectのphaseループをrun_phases_with_checkpointへ置換（CLI=run_db_id Noneは無効）"
```

---

### Task 5: LLM 結果キャッシュ helper（llm_cache_get / llm_cache_set）

**Files:**
- Modify: `src/nexuscore/core/run_checkpoint.py`
- Modify: `tests/core/test_run_checkpoint.py`

- [ ] **Step 1: failing test を書く（追記）**

```python
from nexuscore.core.run_checkpoint import llm_cache_key, llm_cache_get, llm_cache_set


def test_llm_cache_key_format():
    """key = llm_cache:{prompt_hash}:{input_hash}（各16hex）"""
    k = llm_cache_key(model="m1", task="code", system_prompt="sp", user_prompt="up")
    assert k.startswith("llm_cache:")
    parts = k.split(":")
    assert len(parts) == 3 and len(parts[1]) == 16 and len(parts[2]) == 16


def test_llm_cache_key_distinguishes_inputs():
    """user_prompt が違えば key が違う"""
    a = llm_cache_key("m", "t", "sp", "input-a")
    b = llm_cache_key("m", "t", "sp", "input-b")
    assert a != b


def test_llm_cache_set_get_roundtrip(fake_client):
    k = llm_cache_key("m", "t", "sp", "up")
    assert llm_cache_get(fake_client, k) is None
    llm_cache_set(fake_client, k, "cached result", ttl=60)
    assert llm_cache_get(fake_client, k) == "cached result"


def test_llm_cache_failure_is_passthrough(fake_client, monkeypatch):
    """Redis エラーは None を返して呼び出し側を通す（例外を吐かない）"""
    def boom(*a, **kw):
        raise ConnectionError("redis down")

    monkeypatch.setattr(fake_client, "get", boom)
    k = llm_cache_key("m", "t", "sp", "up")
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
    """llm_cache:{prompt_hash}:{input_hash}（改訂案 #4 の key 形式）。"""
    prompt_hash = hashlib.sha256(f"{model}|{task}|{system_prompt}".encode("utf-8")).hexdigest()[:16]
    input_hash = hashlib.sha256(user_prompt.encode("utf-8")).hexdigest()[:16]
    return f"llm_cache:{prompt_hash}:{input_hash}"


def llm_cache_get(client: Any | None, key: str) -> str | None:
    if client is None:
        return None
    try:
        raw = client.get(key)
        return raw.decode("utf-8") if raw is not None else None
    except Exception:  # noqa: BLE001
        return None


def llm_cache_set(client: Any | None, key: str, value: str, ttl: int = 86400) -> None:
    if client is None:
        return
    try:
        client.set(key, value, ex=ttl)
    except Exception:  # noqa: BLE001
        logger.warning("llm_cache set failed (key=%s)", key, exc_info=True)
```

- [ ] **Step 4: test pass を確認**

Run: `PYTHONPATH=src python -m pytest tests/core/test_run_checkpoint.py -v`
Expected: 20 PASSED

- [ ] **Step 5: commit**

```bash
git add src/nexuscore/core/run_checkpoint.py tests/core/test_run_checkpoint.py
git commit -m "feat(c3p2): LLM結果キャッシュ helper（llm_cache:{prompt_hash}:{input_hash}・TTL24h・障害時passthrough）"
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
    from nexuscore.core.run_checkpoint import get_client as rc_get_client

    call_count = {"n": 0}

    def fake_guarded_llm_call(**kwargs):
        call_count["n"] += 1
        return {"content": "LLM said: hello"}

    class FakeRouter:
        task_model_map = {"code": "m-code"}
        default_model = "m-default"
        def complete(self, *a, **kw):
            return "unused"

    class DummyMixin(prm.PhaseRunnerMixin):
        logger = logging.getLogger("test-mixin")

    monkeypatch.setattr(prm, "guarded_llm_call", fake_guarded_llm_call)
    monkeypatch.setattr(prm, "_llm_cache_client", lambda: fake_client)
    mixin = DummyMixin()

    args = ("build a function", {"task_type": "code"})
    first = mixin._execute_task_via_npe(*args)
    second = mixin._execute_task_via_npe(*args)
    assert first == second
    assert call_count["n"] == 1  # 2回目はキャッシュ


def test_execute_task_via_npe_cache_disabled(monkeypatch):
    """kill-switch（client=None）では毎回 LLM を呼ぶ"""
    from nexuscore.core import phase_runner_mixin as prm

    call_count = {"n": 0}

    def fake_guarded_llm_call(**kwargs):
        call_count["n"] += 1
        return {"content": "fresh"}

    class FakeRouter:
        task_model_map = {}
        default_model = "m"

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
Expected: FAIL（`AttributeError: module ... has no attribute '_llm_cache_client'`）

- [ ] **Step 3: phase_runner_mixin.py を修正**

module import 部に追加:

```python
from nexuscore.core.run_checkpoint import (
    get_client as _rc_get_client,
    llm_cache_get,
    llm_cache_key,
    llm_cache_set,
)
import os as _os


def _llm_cache_client():
    """LLM キャッシュ用 Redis client（NEXUSCORE_LLM_CACHE=0 で None）。"""
    if _os.getenv("NEXUSCORE_LLM_CACHE", "1") == "0":
        return None
    return _rc_get_client()
```

`_execute_task_via_npe` 内、`guarded_llm_call` 呼び出しの前後に挿入（93行目 `result = guarded_llm_call(` を以下へ置換）:

```python
        cache_client = _llm_cache_client()
        cache_key = llm_cache_key(
            model=model, task=task_type, system_prompt=system_prompt, user_prompt=prompt,
        )
        cached = llm_cache_get(cache_client, cache_key)
        if cached is not None:
            self.logger.info(f"[NPE] LLM cache hit (task='{task_type}')")
            return cached

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
Expected: 22 PASSED

- [ ] **Step 5: commit**

```bash
git add src/nexuscore/core/phase_runner_mixin.py tests/core/test_run_checkpoint.py
git commit -m "feat(c3p2): _execute_task_via_npeにLLMキャッシュ統合（hit時guarded_llm_call skip・NEXUSCORE_LLM_CACHE=0で無効）"
```

---

### Task 7: celery_app SUCCESS 時 clear_checkpoints ＋変更履歴＋全回帰

**Files:**
- Modify: `src/nexuscore/webapp/celery_app.py:291-293` 付近
- Modify: `docs/変更履歴.md`

- [ ] **Step 1: failing test を書く**

`tests/webapp/test_celery_job_state_machine.py` に追記（既存の fakeredis fixture に合わせる）:

```python
def test_clear_checkpoints_on_success(monkeypatch, fake_client):
    """SUCCESS 確定時に checkpoint がクリアされる（FAILED は残る）"""
    from nexuscore.core import run_checkpoint as rc

    monkeypatch.setattr(rc, "get_client", lambda: fake_client)
    rc.mark_phase_done(fake_client, 101, "planning", _mk_ctx(run_db_id=101))

    # SUCCESS パス: state_machine は成功扱い・run_orchestrator_sync は正常終了とする
    # （既存 test_celery_task_state_transition_success と同じモック構成を再利用）
    ...  # 既存の成功テストをコピーし、最後に以下を assert
    assert rc.load_checkpoint(fake_client, 101) == (None, None)
```

※ このテストは既存 `test_celery_task_state_transition_success` のモック構成（Run/Project/state_machine の patch）を写経し、run_db_id=101 で実行して最後に checkpoint 消失を assert する形に組み立てる。写経元が長い場合、`_mk_ctx` は `OrchestratorContext(task_id="t", user_requirement="r", run_db_id=run_db_id)` のヘルパとして tests/core/test_run_checkpoint.py から import して共通化する。

- [ ] **Step 2: test fail を確認**

Run: `PYTHONPATH=src python -m pytest tests/webapp/test_celery_job_state_machine.py -k clear_checkpoint -v`
Expected: FAIL（SUCCESS 後も checkpoint が残っているため）

- [ ] **Step 3: celery_app.py を修正**

`_run_orchestrator_task_internal` 内、成功確定部（291-293行 `state_machine.complete(...)` / `run.status = "SUCCESS"` の直後）に追加:

```python
                # C3 Plan2: SUCCESS 確定時のみチェックポイント掃除
                # （FAILED は保持→autoretry の再実行が途中再開する・TTL 24h で自動消滅）
                from nexuscore.core import run_checkpoint as _rc

                _rc.clear_checkpoints(_rc.get_client(), run.id)
```

- [ ] **Step 4: test pass を確認**

Run: `PYTHONPATH=src python -m pytest tests/webapp/test_celery_job_state_machine.py tests/core/test_run_checkpoint.py -v`
Expected: 全 PASSED

- [ ] **Step 5: 変更履歴に追記**

`docs/変更履歴.md` の先頭エントリ（2026-08-18）に統合:

```markdown
### Added（C3 Plan2・Orchestrator内部冪等性・改訂案2026-08-06採用7項目#4）
- `core/run_checkpoint.py`: phase完了マーカー＋コンテキストスナップショット（JSON・snapshot先marker後の書込順・TTL 24h）＋`run_phases_with_checkpoint()`（完了phase skip・再配送再開）＋LLM結果キャッシュ（`llm_cache:{prompt_hash}:{input_hash}`・TTL 24h）
- `orchestrator.py`: 7 phase直列ループを`run_phases_with_checkpoint`へ委譲（CLI実行=run_db_id Noneはチェックポイント無効）
- `_execute_task_via_npe`: LLMキャッシュhit時はguarded_llm_callをskip（`NEXUSCORE_LLM_CACHE=0`で無効化・`NEXUSCORE_CHECKPOINT=0`でチェックポイント全体を無効化）
- `celery_app.py`: SUCCESS確定時のみチェックポイントクリア（FAILED保持=retry再開用）
```

- [ ] **Step 6: フル回帰**

Run: `PYTHONPATH=src python -m pytest tests/ -q`
Expected: 既存緑数（約4,993）＋新規22件 が PASSED / 0 failed

- [ ] **Step 7: commit & push**

```bash
git add src/nexuscore/webapp/celery_app.py tests/webapp/test_celery_job_state_machine.py docs/変更履歴.md
git commit -m "feat(c3p2): SUCCESS時checkpointクリア＋変更履歴（Orchestrator内部冪等性完結）"
git push
```

- [ ] **Step 8: CI確認（効果-証跡対応ゲート）**

Run: `gh run watch <新規run id> --exit-status`
Expected: NexusCore CI/CD・Safe Tests とも conclusion: success

---

## Self-Review 結果（作成時実施済み）

1. **Spec カバレッジ**: 改訂案 #4 の「step完了マーカー」「LLM結果キャッシュ TTL 24h」→ Task 1-3/5-6 で網羅。Redis実証（docker）は本 plan外（実装後の別検証・経緯は backlog 構想の「docker導入後にRedis検証」参照）。
2. **プレースホルダー**: Task 7 Step 1 のテストは「既存テスト写経」としているが構成と assert を明示済み（写経元を特定させるため）。それ以外に TBD 無し。
3. **型整合**: `mark_phase_done(client, run_db_id, phase, context)` / `load_checkpoint(client, run_db_id) -> (str|None, Any|None)` / `run_phases_with_checkpoint(runner, context, client, run_db_id)` / `llm_cache_key(model, task, system_prompt, user_prompt)` の署名は全 Task で同一。
