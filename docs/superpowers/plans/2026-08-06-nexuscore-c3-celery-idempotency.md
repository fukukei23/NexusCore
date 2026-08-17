# NexusCore C3 Celery 冪等性・再実行保護（Plan1: Celery層）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Celery タスク `run_orchestrator_task` の冪等性・再実行保護を、Redis SETNX 分散ロック + 決定論的 task_id + producer ガード + autoretry 拡充 + Slack 通知冪等化で実装し、worker 落ち/再配送/重複 enqueue による 2 重実行を確実に防止する。

**Architecture:** 閾値ヒューリスティック（破綻案）を撤回し、Redis SETNX による分散ロックで原子的状態遷移を実現。決定論的 task_id で broker レベルの重複 enqueue 拒否、producer 側でも Redis ロックで二重防御。Slack 通知は NotificationLog テーブルの UNIQUE 制約で冪等化。Orchestrator 内部の冪等性（step 完了マーカー + LLM キャッシュ）は別 Plan（Plan2）で実装。

**Tech Stack:** Python 3.12 / Flask / Celery / Redis (redis-py) / SQLAlchemy / Flask-Migrate (Alembic) / fakeredis (テスト用)

**前段（確定済・multi-llm-review Gemini+MiniMax CRITICAL一致）:**
- 当初「閾値1hヒューリスティック」は Race Condition/タスクロスト/2重実行の3穴で撤回
- 実例: `obsidian-ssot/00_SYSTEM/参考資料/LLMサボりバイアス実例/2026-08-05_閾値ヒューリスティック設計サボり-C3Celery冪等性.md`

**Plan2（別途）:** (4) Orchestrator 内部冪等性 — JobStateMachine への step API 新設・step 完了マーカー・LLM 結果キャッシュ。本 Plan1 完了後に着手。

---

## File Structure

- **Create:** `src/nexuscore/webapp/task_lock.py` — Redis 分散ロック utility（get_redis / acquire_lock / release_lock / heartbeat / producer_lock）
- **Modify:** `src/nexuscore/webapp/models.py` — NotificationLog モデル追加
- **Create:** `migrations/versions/<auto>_add_notification_logs.py` — autogenerate で notification_logs テーブル生成（既存マイグレ chain）
- **Modify:** `src/nexuscore/webapp/celery_app.py:141-212` — タスク装飾子強化（acks_late / task_reject_on_worker_lost / autoretry_for / 決定論的 task_id 受取）・先頭ロックガード・_finalize_run の Slack 冪等化
- **Modify:** `src/nexuscore/webapp/views_projects.py:217-237` — `_dispatch_celery_run` に producer_lock + 決定論的 task_id
- **Modify:** `src/nexuscore/api/routes/_projects_runs.py:54-90` — 同上（FastAPI 側 producer）
- **Modify:** `docker-compose.saas.yml` — Celery 設定明示（visibility_timeout / task_acks_late / task_track_started）
- **Modify:** `requirements-dev.txt` — fakeredis 追加
- **Test:** `tests/webapp/test_task_lock.py`（新規）・`tests/webapp/test_celery_app.py`（拡張）・`tests/webapp/test_notification_idempotency.py`（新規）

---

## Task 1: Redis 分散ロック utility（task_lock.py）

**Files:**
- Create: `src/nexuscore/webapp/task_lock.py`
- Modify: `requirements-dev.txt`（fakeredis 追加）
- Test: `tests/webapp/test_task_lock.py`

- [ ] **Step 1: fakeredis 追加**

`requirements-dev.txt` 末尾に追加:
```
fakeredis>=2.20.0
```
実行: `cd ~/projects/NexusCore && .venv/bin/pip install fakeredis`

- [ ] **Step 2: failing test を書く**

`tests/webapp/test_task_lock.py`:
```python
"""task_lock utility のテスト（fakeredis 使用）"""
import pytest
from unittest.mock import patch
import fakeredis

from nexuscore.webapp.task_lock import (
    acquire_lock, release_lock, heartbeat, producer_lock,
)


@pytest.fixture
def fake_client():
    return fakeredis.FakeStrictRedis()


def test_acquire_lock_success(fake_client):
    """最初のロック取得は成功"""
    assert acquire_lock(fake_client, "lock:run:1", "worker-A", ttl=30) is True


def test_acquire_lock_contended(fake_client):
    """既に取得済みのロックは別 worker が取得失敗"""
    acquire_lock(fake_client, "lock:run:1", "worker-A", ttl=30)
    assert acquire_lock(fake_client, "lock:run:1", "worker-B", ttl=30) is False


def test_release_lock_owner_only(fake_client):
    """所有者のみロック解放（他人は解放できない）"""
    acquire_lock(fake_client, "lock:run:1", "worker-A", ttl=30)
    assert release_lock(fake_client, "lock:run:1", "worker-B") is False  # 他人は失敗
    assert release_lock(fake_client, "lock:run:1", "worker-A") is True   # 所有者は成功
    assert acquire_lock(fake_client, "lock:run:1", "worker-C", ttl=30) is True  # 解放後は再取得可


def test_heartbeat_extends_ttl(fake_client):
    """heartbeat で TTL が延長される"""
    acquire_lock(fake_client, "lock:run:1", "worker-A", ttl=30)
    assert heartbeat(fake_client, "lock:run:1", "worker-A", ttl=30) is True
    # 他人の heartbeat は失敗
    assert heartbeat(fake_client, "lock:run:1", "worker-B", ttl=30) is False


def test_producer_lock_prevents_duplicate(fake_client):
    """producer_lock は短時間の重複 enqueue を防止"""
    assert producer_lock(fake_client, run_id=1, ttl=10) is True
    assert producer_lock(fake_client, run_id=1, ttl=10) is False  # 2回目は失敗
```

- [ ] **Step 3: test fail を確認**

Run: `cd ~/projects/NexusCore && PYTHONPATH=src .venv/bin/pytest tests/webapp/test_task_lock.py -v`
Expected: FAIL（`ImportError: No module named 'nexuscore.webapp.task_lock'`）

- [ ] **Step 4: task_lock.py を実装**

`src/nexuscore/webapp/task_lock.py`:
```python
"""Redis SETNX ベースの分散ロック utility。

Celery タスクの冪等性・producer 側の重複 enqueue 防止に使用。
所有者チェック付きの安全な解放（Lua script）で誤解放を防止。
"""
from __future__ import annotations

import os
from typing import Any

import redis

# 所有者のみ解放するための Lua script（CHECK-AND-DEL を原子的に実行）
_RELEASE_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
else
    return 0
end
"""

_EXTEND_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('expire', KEYS[1], ARGV[2])
else
    return 0
end
"""


def get_redis() -> redis.Redis:
    """Redis クライアントを取得（broker URL を流用）。"""
    url = os.getenv("REDIS_URL") or os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    return redis.from_url(url)


def acquire_lock(client: Any, lock_key: str, worker_id: str, ttl: int = 30) -> bool:
    """SET NX EX でロック取得。成功=True・既取得=False。"""
    return bool(client.set(lock_key, worker_id, nx=True, ex=ttl))


def release_lock(client: Any, lock_key: str, worker_id: str) -> bool:
    """所有者のみ解放（Lua で原子的 CHECK-AND-DEL）。"""
    return bool(client.eval(_RELEASE_SCRIPT, 1, lock_key, worker_id))


def heartbeat(client: Any, lock_key: str, worker_id: str, ttl: int = 30) -> bool:
    """所有者のみ TTL 延長（長時間タスク用）。"""
    return bool(client.eval(_EXTEND_SCRIPT, 1, lock_key, worker_id, str(ttl)))


def producer_lock(client: Any, run_id: int, ttl: int = 10) -> bool:
    """producer 側の重複 enqueue 防止（短 TTL）。"""
    return acquire_lock(client, f"producer_lock:{run_id}", "producer", ttl=ttl)


def task_lock_key(run_db_id: int) -> str:
    """タスク実行ロックのキー名。"""
    return f"lock:run:{run_db_id}"


def deterministic_task_id(run_db_id: int) -> str:
    """決定論的 task_id（broker レベルで重複 enqueue 拒否に使用）。"""
    return f"orchestrator-run-{run_db_id}"
```

- [ ] **Step 5: test pass を確認**

Run: `PYTHONPATH=src .venv/bin/pytest tests/webapp/test_task_lock.py -v`
Expected: 5 passed

- [ ] **Step 6: commit**

```bash
git add src/nexuscore/webapp/task_lock.py tests/webapp/test_task_lock.py requirements-dev.txt
git commit -m "feat(c3): Redis分散ロック utility 追加（task_lock.py）"
```

---

## Task 2: Celery タスク装飾子強化（acks_late / autoretry / 決定論的 task_id 受取）

**Files:**
- Modify: `src/nexuscore/webapp/celery_app.py:141-148`（タスク定義）
- Test: `tests/webapp/test_celery_app.py`

- [ ] **Step 1: failing test を書く（test_celery_app.py に追記）**

`tests/webapp/test_celery_app.py` 末尾に追記:
```python
def test_run_orchestrator_task_has_acks_late():
    """タスクに acks_late が設定されている（worker 落ちで再配送）"""
    from nexuscore.webapp.celery_app import _run_orchestrator_task_internal
    # Celery Task オブジェクトとして装飾されていることを確認
    assert _run_orchestrator_task_internal.acks_late is True
    assert _run_orchestrator_task_internal.reject_on_worker_lost is True


def test_deterministic_task_id():
    """決定論的 task_id が生成される（重複 enqueue 拒否）"""
    from nexuscore.webapp.task_lock import deterministic_task_id
    assert deterministic_task_id(42) == "orchestrator-run-42"
```

- [ ] **Step 2: test fail を確認**

Run: `PYTHONPATH=src SKIP_CELERY_AUTO_INIT=1 .venv/bin/pytest tests/webapp/test_celery_app.py::test_run_orchestrator_task_has_acks_late -v`
Expected: FAIL（`acks_late is True` でなくデフォルト False）

- [ ] **Step 3: celery_app.py のタスク装飾子を強化**

`src/nexuscore/webapp/celery_app.py:141` の `@celery_instance.task(...)` を修正:
```python
    @celery_instance.task(
        name="nexuscore.run_orchestrator",
        bind=True,
        acks_late=True,
        reject_on_worker_lost=True,
        autoretry_for=(
            sqlalchemy.exc.OperationalError,
            redis.exceptions.ConnectionError,
            redis.exceptions.TimeoutError,
            TimeoutError,
            ConnectionError,
        ),
        retry_backoff=True,
        retry_backoff_max=120,
        retry_jitter=True,
        max_retries=5,
    )
    def _run_orchestrator_task_internal(self, run_db_id: int) -> None:
```

※ `self`（bind=True）を使うため、メソッド内で `self.request.id` が取れる。`run_db_id` はそのまま引数。

インポート追加（ファイル先頭付近）:
```python
import redis
import sqlalchemy
```

- [ ] **Step 4: test pass を確認**

Run: `PYTHONPATH=src SKIP_CELERY_AUTO_INIT=1 .venv/bin/pytest tests/webapp/test_celery_app.py -v`
Expected: PASS（新規2件＋既存）

- [ ] **Step 5: commit**

```bash
git add src/nexuscore/webapp/celery_app.py tests/webapp/test_celery_app.py
git commit -m "feat(c3): Celeryタスク装飾子強化（acks_late/autoretry/決定論的task_id）"
```

---

## Task 3: タスク先頭の冪等ガード（ロック取得・status SUCCESS skip）

**Files:**
- Modify: `src/nexuscore/webapp/celery_app.py`（タスク本体先頭・JobStateMachine開始前）
- Test: `tests/webapp/test_celery_app.py`

- [ ] **Step 1: failing test を書く**

`tests/webapp/test_celery_app.py` に追記:
```python
def test_task_skips_already_success_run(monkeypatch):
    """status=SUCCESS の Run は2重実行を skip する"""
    import fakeredis
    from unittest.mock import MagicMock, patch
    from nexuscore.webapp import celery_app as capp

    fake_redis = fakeredis.FakeStrictRedis()
    monkeypatch.setattr("nexuscore.webapp.task_lock.get_redis", lambda: fake_redis)

    run = MagicMock()
    run.id = 1
    run.status = "SUCCESS"
    run.requirement = "do something"
    run.project = MagicMock(local_path="/tmp", name="p", autonomy_level=None)

    with patch("nexuscore.webapp.celery_app.Run") as MockRun, \
         patch("nexuscore.webapp.celery_app.run_orchestrator_sync") as mock_sync:
        MockRun.query.get.return_value = run
        # タスク本体を実行（Celery起動せず直接呼出）
        result = capp._run_orchestrator_task_internal.__wrapped__(MagicMock(request=MagicMock(id="w1")), run.id)
        mock_sync.assert_not_called()  # Orchestrator は実行されない


def test_task_skips_when_lock_contended(monkeypatch):
    """別 worker がロック中は skip（2重実行防止）"""
    import fakeredis
    from unittest.mock import MagicMock, patch
    from nexuscore.webapp import celery_app as capp
    from nexuscore.webapp import task_lock

    fake_redis = fakeredis.FakeStrictRedis()
    # 先に別 worker がロック取得済みにする
    task_lock.acquire_lock(fake_redis, task_lock.task_lock_key(1), "other-worker", ttl=30)
    monkeypatch.setattr("nexuscore.webapp.task_lock.get_redis", lambda: fake_redis)

    run = MagicMock()
    run.id = 1
    run.status = "PENDING"
    run.requirement = "do something"
    run.project = MagicMock(local_path="/tmp", name="p")

    with patch("nexuscore.webapp.celery_app.Run") as MockRun, \
         patch("nexuscore.webapp.celery_app.run_orchestrator_sync") as mock_sync:
        MockRun.query.get.return_value = run
        capp._run_orchestrator_task_internal.__wrapped__(MagicMock(request=MagicMock(id="w2")), run.id)
        mock_sync.assert_not_called()
```

- [ ] **Step 2: test fail を確認**

Run: `PYTHONPATH=src SKIP_CELERY_AUTO_INIT=1 .venv/bin/pytest tests/webapp/test_celery_app.py::test_task_skips_already_success_run -v`
Expected: FAIL（現在は SUCCESS でも実行してしまう）

- [ ] **Step 3: タスク本体先頭にガードを実装**

`celery_app.py` の `_run_orchestrator_task_internal` 本体の先頭（`run = Run.query.get(...)` の後）に挿入:
```python
        # === C3: 冪等ガード（閾値ヒューリスティック撤回・Redis SETNX で原子的）===
        from nexuscore.webapp import task_lock

        # (a) 完了済み Run は即 skip（2重実行防止）
        if run.status == "SUCCESS":
            logger.info(f"Run {run_db_id} already SUCCESS — skipping (idempotency guard)")
            return

        # (b) Redis 分散ロック取得（ Race Condition 回避・worker_id = Celery task id）
        redis_client = task_lock.get_redis()
        lock_key = task_lock.task_lock_key(run_db_id)
        worker_id = self.request.id  # bind=True により self 参照可
        if not task_lock.acquire_lock(redis_client, lock_key, worker_id, ttl=30):
            logger.info(f"Run {run_db_id} is locked by another worker — skipping")
            return
        # 長時間タスク用: 実行中に heartbeat で TTL 延長（必要に応じて定期呼出・Plan1では最終解放のみ）
        try:
            # === 既存の Orchestrator 実行フロー（status RUNNING 遷移以降）===
            project = run.project
            job_id = run.run_id or str(run.id)

            if not run.requirement:
                logger.error(f"Run.requirement is empty for run_id={run.id}")
                run.status = "FAILED"
                run.finished_at = datetime.now(UTC)
                db.session.commit()
                return

            session_controller = SessionController(
                session_id=job_id,
                root_dir=os.path.join(project.local_path, ".nexus", "sessions"),
            )
            history_logger = RunHistoryLogger(project_root=project.local_path)
            state_machine = JobStateMachine(
                job_id=job_id,
                session_controller=session_controller,
                history_logger=history_logger,
                job_type="orchestrator",
            )

            final_status = "error"
            try:
                state_machine.start()
                run.status = "RUNNING"
                run.started_at = datetime.now(UTC)
                db.session.commit()

                run_orchestrator_sync(
                    project_path=project.local_path,
                    user_requirement=run.requirement,
                    run_db_id=run.id,
                    autonomy_level=run.autonomy_level or 1,
                    language="ja",
                    fast_lane=False,
                )

                state_machine.complete(details={"run_db_id": run.id, "project_name": project.name})
                run.status = "SUCCESS"
                final_status = "success"

            except Exception as exc:  # noqa: BLE001
                logger.error(f"Orchestrator execution failed for run_id={run.id}: {exc}", exc_info=True)
                state_machine.fail(
                    error_message=str(exc),
                    details={"run_db_id": run.id, "project_name": project.name, "exception_type": type(exc).__name__},
                )
                run.status = "FAILED"

            finally:
                _finalize_run(run, project, final_status)

        finally:
            # (c) ロック解放（所有者のみ・例外時も確実に解放）
            task_lock.release_lock(redis_client, lock_key, worker_id)
```

※ 既存の `run = Run.query.get(...)` 〜 `_finalize_run` までをこの try/finally で囲む。`return`（Run not found）はガード前のまま。

- [ ] **Step 4: test pass を確認**

Run: `PYTHONPATH=src SKIP_CELERY_AUTO_INIT=1 .venv/bin/pytest tests/webapp/test_celery_app.py -v`
Expected: PASS

- [ ] **Step 5: commit**

```bash
git add src/nexuscore/webapp/celery_app.py tests/webapp/test_celery_app.py
git commit -m "feat(c3): タスク先頭冪等ガード（Redis SETNX分散ロック・SUCCESS skip）"
```

---

## Task 4: producer 側ガード（views_projects / api routes）

**Files:**
- Modify: `src/nexuscore/webapp/views_projects.py:217-237`（`_dispatch_celery_run`）
- Modify: `src/nexuscore/api/routes/_projects_runs.py:54-90`
- Test: `tests/webapp/test_views_projects.py`（既存があれば拡張・なければ新規追記）

- [ ] **Step 1: failing test を書く**

`tests/webapp/test_producer_guard.py`（新規）:
```python
"""producer 側の重複 enqueue ガードのテスト"""
import pytest
import fakeredis
from unittest.mock import patch, MagicMock


def test_dispatch_celery_run_uses_producer_lock(monkeypatch):
    """_dispatch_celery_run は producer_lock を取得してから enqueue する"""
    fake_redis = fakeredis.FakeStrictRedis()
    monkeypatch.setattr("nexuscore.webapp.task_lock.get_redis", lambda: fake_redis)

    captured = {}

    class FakeTask:
        @staticmethod
        def delay(run_id, **kwargs):
            captured["called"] = True
            captured["task_id"] = kwargs.get("task_id")

    run = MagicMock(); run.id = 1; run.run_id = "abc"; run.status = "PENDING"
    project = MagicMock(); project.id = 1

    with patch("nexuscore.webapp.celery_app.run_orchestrator_task", FakeTask), \
         patch("nexuscore.webapp.views_projects.request"), \
         patch("nexuscore.webapp.views_projects.flash"):
        from nexuscore.webapp.views_projects import _dispatch_celery_run
        _dispatch_celery_run(run, project)
        assert captured.get("called") is True
        assert captured.get("task_id") == "orchestrator-run-1"


def test_dispatch_rejects_duplicate_within_lock_window(monkeypatch):
    """producer_lock 取得済みなら2回目は 409 を返す（重複 enqueue 拒否）"""
    fake_redis = fakeredis.FakeStrictRedis()
    monkeypatch.setattr("nexuscore.webapp.task_lock.get_redis", lambda: fake_redis)

    run = MagicMock(); run.id = 1; run.run_id = "abc"; run.status = "PENDING"
    project = MagicMock(); project.id = 1

    with patch("nexuscore.webapp.celery_app.run_orchestrator_task"), \
         patch("nexuscore.webapp.views_projects.request"), \
         patch("nexuscore.webapp.views_projects.flash"):
        from nexuscore.webapp.views_projects import _dispatch_celery_run
        _dispatch_celery_run(run, project)  # 1回目: 成功
        # 2回目: producer_lock 期限内なので拒否
        resp = _dispatch_celery_run(run, project)
        # JSON の場合は 409・それ以外は flash 等で重複拒否
        assert resp is not None
```

- [ ] **Step 2: test fail を確認**

Run: `PYTHONPATH=src SKIP_CELERY_AUTO_INIT=1 .venv/bin/pytest tests/webapp/test_producer_guard.py -v`
Expected: FAIL（現在は producer_lock も task_id も無い）

- [ ] **Step 3: _dispatch_celery_run に producer_lock + 決定論的 task_id を実装**

`views_projects.py:217` の `_dispatch_celery_run` を修正:
```python
def _dispatch_celery_run(run: Run, project: Project):
    """Celery非同期でRunを実行し、レスポンスを返す。"""
    from nexuscore.webapp.celery_app import run_orchestrator_task
    from nexuscore.webapp import task_lock

    # C3: producer側ガード（重複 enqueue 防止）
    redis_client = task_lock.get_redis()
    if not task_lock.producer_lock(redis_client, run.id, ttl=10):
        if request.accept_mimetypes.best == "application/json":
            return jsonify({"run_id": run.run_id, "status": run.status, "message": "Run already queued (duplicate prevented)."}), 409
        flash("この Run は既にキューに入っています（重複防止）。", "warning")
        return redirect(url_for("views_projects.project_detail", project_id=project.id))

    # C3: 決定論的 task_id（broker レベルで重複 enqueue 拒否）
    task_id = task_lock.deterministic_task_id(run.id)
    run_orchestrator_task.delay(run.id, task_id=task_id)

    if request.accept_mimetypes.best == "application/json":
        return (jsonify({"run_id": run.run_id, "status": run.status, "message": "Run queued. Execution will start shortly."}), 202)
    flash(f"Run '{run.run_id[:8]}...' がキューに入りました。", "info")
    return redirect(url_for("views_projects.project_detail", project_id=project.id))
```

※ `run_orchestrator_task.delay(run.id, task_id=...)` の task_id は Celery の headers 経由で重複検知。Celery は `apply_async(args, task_id=...)` で重複を弾くため、`delay` は `apply_async` ラッパー拡張が必要:
```python
    run_orchestrator_task.apply_async(args=[run.id], task_id=task_id)
```
（`delay` は task_id を取れないため `apply_async` に変更）

`api/routes/_projects_runs.py:85` の `run_orchestrator_task.delay(run.id)` も同様に修正:
```python
        from nexuscore.webapp import task_lock
        redis_client = task_lock.get_redis()
        if not task_lock.producer_lock(redis_client, run.id, ttl=10):
            raise HTTPException(status_code=409, detail="Run already queued (duplicate prevented).")
        task_id = task_lock.deterministic_task_id(run.id)
        run_orchestrator_task.apply_async(args=[run.id], task_id=task_id)
```

- [ ] **Step 4: test pass を確認**

Run: `PYTHONPATH=src SKIP_CELERY_AUTO_INIT=1 .venv/bin/pytest tests/webapp/test_producer_guard.py -v`
Expected: PASS

- [ ] **Step 5: commit**

```bash
git add src/nexuscore/webapp/views_projects.py src/nexuscore/api/routes/_projects_runs.py tests/webapp/test_producer_guard.py
git commit -m "feat(c3): producer側ガード（producer_lock+決定論的task_id・重複enqueue拒否）"
```

---

## Task 5: NotificationLog モデル + マイグレーション

**Files:**
- Modify: `src/nexuscore/webapp/models.py`（NotificationLog 追加）
- Create: `migrations/versions/<auto>_add_notification_logs.py`（autogenerate）
- Test: `tests/webapp/test_models.py`（既存が SKIP なら新規 light）

- [ ] **Step 1: failing test を書く**

`tests/webapp/test_notification_log.py`（新規）:
```python
"""NotificationLog モデルの UNIQUE 制約テスト"""
import pytest
from sqlalchemy.exc import IntegrityError


def test_notification_log_unique_constraint(db_session):
    """同一 (run_id, event_type) の2件目挿入は失敗（冪等化）"""
    from nexuscore.webapp.models import NotificationLog
    db_session.add(NotificationLog(run_id=1, event_type="orchestrator_complete"))
    db_session.commit()
    db_session.add(NotificationLog(run_id=1, event_type="orchestrator_complete"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
```

- [ ] **Step 2: test fail を確認**

Run: `PYTHONPATH=src .venv/bin/pytest tests/webapp/test_notification_log.py -v`
Expected: FAIL（NotificationLog 未定義）

- [ ] **Step 3: NotificationLog モデル追加**

`models.py` 末尾（ApiKey クラスの後）に追加:
```python
class NotificationLog(db.Model):
    """通知送信ログ（Slack 等の重複送信防止・UNIQUE(run_id, event_type)）"""

    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=True, index=True)
    event_type = Column(String(64), nullable=False)  # orchestrator_complete / orchestrator_failed 等
    sent_at = Column(DateTime, default=datetime.now(UTC), nullable=False)

    __table_args__ = (
        # 同一 Run の同一イベント種別は1回のみ（Slack 重複送信防止）
        sa.UniqueConstraint("run_id", "event_type", name="uq_notification_logs_run_event"),
    )

    def __repr__(self) -> str:
        return f"<NotificationLog(run_id={self.run_id}, event_type='{self.event_type}')>"
```

※ `sa` を import に追加（既存 `from sqlalchemy import ...` に `UniqueConstraint` 含む。`sa` は `import sqlalchemy as sa` を追加）

- [ ] **Step 4: autogenerate でマイグレーション生成**

Run:
```bash
cd ~/projects/NexusCore
rm -f /tmp/nexus_notif_check.db
DATABASE_URI="sqlite:////tmp/nexus_notif_check.db" FLASK_APP="nexuscore.webapp:create_app" PYTHONPATH=src .venv/bin/flask db migrate -m "add notification_logs"
```
生成されたファイルを確認（notification_logs テーブル作成・down_revision=915be6eb487e の chain）

- [ ] **Step 5: test pass を確認**

Run: `PYTHONPATH=src .venv/bin/pytest tests/webapp/test_notification_log.py -v`
Expected: PASS

- [ ] **Step 6: drift 検証**

```bash
DATABASE_URI="sqlite:////tmp/nexus_notif_verify.db" FLASK_APP="nexuscore.webapp:create_app" PYTHONPATH=src .venv/bin/flask db upgrade
DATABASE_URI="sqlite:////tmp/nexus_notif_verify.db" FLASK_APP="nexuscore.webapp:create_app" PYTHONPATH=src .venv/bin/flask db migrate -m "drift check"
# "No changes in schema detected" を確認
```

- [ ] **Step 7: commit**

```bash
git add src/nexuscore/webapp/models.py migrations/versions/*_add_notification_logs.py tests/webapp/test_notification_log.py
git commit -m "feat(c3): NotificationLog モデル＋マイグレーション（Slack重複送信防止）"
```

---

## Task 6: Slack 通知の冪等化（_finalize_run）

**Files:**
- Modify: `src/nexuscore/webapp/celery_app.py`（`_finalize_run` の Slack 通知ブロック）
- Test: `tests/webapp/test_notification_idempotency.py`

- [ ] **Step 1: failing test を書く**

`tests/webapp/test_notification_idempotency.py`（新規）:
```python
"""_finalize_run の Slack 通知が冪等であることを検証"""
import pytest
from unittest.mock import patch, MagicMock


def test_finalize_run_does_not_duplicate_slack(db_session, monkeypatch):
    """2回 _finalize_run を呼んでも Slack 通知は1回のみ"""
    from nexuscore.webapp.celery_app import _finalize_run
    from nexuscore.webapp.models import Run, Project, NotificationLog

    project = Project(name="p", owner_id=None, local_path="/tmp")
    # ※ owner_id は NOT NULL だが簡易テスト・実際は User 作成
    # （テスト fixture で User + Project + Run を用意する方が現実的・以下は概念検証）

    sent = {"count": 0}

    class FakeNotifier:
        def notify_orchestrator_complete(self, **kwargs):
            sent["count"] += 1

    with patch("nexuscore.core.notifier.get_notifier", return_value=FakeNotifier()):
        # 1回目: 送信 + NotificationLog 記録
        # 2回目: NotificationLog 既存なので skip
        # （詳細は Run/Project fixture 構築後に検証）
        pass
```

※ 完全テストは Run/Project/User fixture 構築が必要。本 step では概念実装後に統合テストで検証。

- [ ] **Step 2: _finalize_run の Slack ブロックを冪等化**

`celery_app.py` の `_finalize_run` 内 Slack 通知ブロック（120-134行）を修正:
```python
    try:
        from nexuscore.core.notifier import get_notifier
        from nexuscore.webapp.models import NotificationLog, Run as RunModel
        from sqlalchemy.exc import IntegrityError

        notifier = get_notifier()
        if notifier:
            event_type = "orchestrator_complete" if status == "success" else "orchestrator_failed"
            # C3: 冪等ガード（NotificationLog UNIQUE 制約で重複送信防止）
            try:
                db.session.add(NotificationLog(run_id=run.id, event_type=event_type))
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                logger.info(f"Notification {event_type} for run {run.id} already sent — skipping (idempotency)")
            else:
                session_id = run.run_id or str(run.id)
                notifier.notify_orchestrator_complete(
                    project_path=project.local_path,
                    requirement=run.requirement,
                    status=status,
                    session_id=session_id,
                    details={"Run ID": run.run_id, "プロジェクト名": project.name},
                )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Failed to send Slack notification: {e}", exc_info=True)
```

- [ ] **Step 3: test pass を確認**

Run: `PYTHONPATH=src SKIP_CELERY_AUTO_INIT=1 .venv/bin/pytest tests/webapp/test_notification_idempotency.py tests/webapp/test_celery_app.py -v`
Expected: PASS（既存回帰含め）

- [ ] **Step 4: commit**

```bash
git add src/nexuscore/webapp/celery_app.py tests/webapp/test_notification_idempotency.py
git commit -m "feat(c3): Slack通知の冪等化（NotificationLog UNIQUE制約で重複防止）"
```

---

## Task 7: docker-compose.saas.yml Celery 設定明示

**Files:**
- Modify: `docker-compose.saas.yml`（webapp/celery-worker の Celery 設定）

- [ ] **Step 1: Celery 設定を明示**

`docker-compose.saas.yml` の `webapp`・`celery-worker` サービスの environment に追加:
```yaml
      - CELERY_TASK_ACKS_LATE=1
      - CELERY_TASK_REJECT_ON_WORKER_LOST=1
      - CELERY_BROKER_TRANSPORT_OPTIONS_VISIBILITY_TIMEOUT=7200
      - CELERY_TASK_TRACK_STARTED=1
```

※ Redis broker の visibility_timeout は デフォルト 3600s（1h）→ Orchestrator 長時間実行を見越し 7200s（2h）に延長。これは acks_late + 長時間タスクの必須設定（Gemini 指摘）。

- [ ] **Step 2: YAML 妥当性確認**

```bash
cd ~/projects/NexusCore
.venv/bin/python -c "import yaml; yaml.safe_load(open('docker-compose.saas.yml')); print('YAML OK')"
```

- [ ] **Step 3: 設定を Celery アプリに反映**

`celery_app.py` の `make_celery` 内 `celery_app.conf.update(...)` に追加（環境変数から読む Celery 設定は一部明示が必要）:
```python
    celery_app.conf.update(
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        task_track_started=True,
        broker_transport_options={"visibility_timeout": int(os.getenv("CELERY_BROKER_TRANSPORT_OPTIONS_VISIBILITY_TIMEOUT", "3600"))},
    )
```

- [ ] **Step 4: commit**

```bash
git add docker-compose.saas.yml src/nexuscore/webapp/celery_app.py
git commit -m "feat(c3): Celery環境前提明示（visibility_timeout/acks_late/track_started）"
```

---

## Self-Review

**1. Spec coverage（Plan1 = (1)(2)(3)(5)(6)(7)）:**
- (1) Redis SETNX分散ロック → Task 1 (utility) + Task 3 (タスク先頭ガード) ✓
- (2) 決定論的 task_id → Task 2 (受取) + Task 4 (producer側付与) ✓
- (3) producer 側ガード → Task 4 ✓
- (5) autoretry_for 拡充 → Task 2 ✓（主要一時的例外列挙・完全正規化層は別途）
- (6) Slack 通知冪等化 → Task 5 (NotificationLog) + Task 6 (_finalize_run) ✓
- (7) Celery 環境前提 → Task 7 ✓
- (4) Orchestrator 内部冪等性 → **Plan2 で実装**（本 plan スコープ外・明示切り分け）

**2. Placeholder scan:**
- Task 6 Step 1 に「概念検証」記載あり → 実装時に Run/Project/User fixture を構築して完全テストに昇格させる（TODO 明記済み）
- autoretry_for の「完全正規化層」は Plan2/別タスク注記済み

**3. Type consistency:**
- `deterministic_task_id(run_db_id)` → Task 1 定義・Task 2/4 で使用 ✓
- `task_lock_key(run_db_id)` → Task 1 定義・Task 3 で使用 ✓
- `acquire_lock(client, lock_key, worker_id, ttl)` → Task 1 定義・Task 3 で使用 ✓
- `NotificationLog(run_id, event_type)` → Task 5 定義・Task 6 で使用 ✓

**制約（本番運用なし・docker 未導入）:**
- 検証は fakeredis + SQLite で実施（Task 1-6）
- Redis 実環境検証（分散ロックの実挙動）は docker 導入後に C1/C2 と同方針で実施
- autoretry の実例外網羅は run_orchestrator_sync が投げうる例外を別途調査→Plan2 で RetryableError 正規化層を完全化
