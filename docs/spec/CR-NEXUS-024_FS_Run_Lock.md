# CR-NEXUS-024: FS Run Lock (File-System Lock) + Stale Reclaim

## 1. Implementation Task Overview（人間向け仕様書）

### 目的（Why）
NexusCore の `resume_run(run_id)` は CR-NEXUS-023（Concurrency Contract）に従い、同一 `run_id` の同時再開を防止する必要がある。現状の `run_lock.py` は in-memory lock のため、**プロセス間の競合**を防げない。これを **FSロック**に置換し、さらに **stale lock（TTL超過）を回収**できるようにする。

### 背景・問題（Context）
- `authority_runner.resume_run()` は lock acquisition に失敗した場合を **CONFLICT** として返し、**FAILED にしない**・**RunState を更新しない**のが契約（CR-019/023）。
- 長時間停止・クラッシュ時に残る lock を放置すると復旧不能になるため、**TTL による stale 回収**が必要。

### ゴール（Outcome / Goal）
- `src/nexuscore/orchestrator/run_lock.py` を FS ロックに置換する
- env 変数でロックディレクトリと TTL を制御する
- stale（expires_at 超過）を `.stale.<ts>` に退避して再獲得できる
- テストで conflict と stale 回収を再現できる

### スコープ
**In-Scope**
- `run_lock.py` の FS ロック実装（TTL と stale 回収）
- `tests/orchestrator/` のテスト更新（conflict 再現）＋ stale 回収テスト追加

**Out-of-Scope**
- 分散ロック、暗号署名、複数ノードでの強整合（将来CR）
- API/CLI の UX 変更

### リスク・依存
- FS の atomic create / rename に依存するため、Windows ネイティブでは挙動差があり得る（ただし本プロジェクトは WSL/Linux を前提）。
- release 時に他プロセスの lock を誤って削除しないため、**所有者トークン**をファイルに書いて検証する必要がある。

### Definition of Done（完了条件）
- `try_acquire_run_lock()` が FS ロックを取得できる
- lock 競合時は `ok=False` を返す（authority_runner 側で CONFLICT になる）
- stale lock を `.stale.<ts>` に退避して再獲得できる
- `tests/orchestrator/` の関連テストが PASS

---

## 2. Implementation Instruction for Cursor（Cursor 用実装指示書）

### 変更対象ファイル
- MUST UPDATE: `src/nexuscore/orchestrator/run_lock.py`
- MUST UPDATE: `tests/orchestrator/test_resume_lock_conflict.py`
- MUST ADD: `tests/orchestrator/test_run_lock_stale_reclaim.py`

### 必須変更内容（Required Changes）

#### A) FS ロック仕様（run_lock.py）
- MUST use env:
  - `NEXUSCORE_RUN_LOCK_DIR`: lock file directory
  - `NEXUSCORE_RUN_LOCK_TTL_SECONDS`: TTL seconds (int)
- MUST define lock file path:
  - `<NEXUSCORE_RUN_LOCK_DIR>/<safe_run_id>.lock`
  - `safe_run_id` MUST be a filesystem-safe fixed-length identifier (e.g. `sha256(run_id)` hex).
  - Original `run_id` MUST be stored inside the JSON payload (see below).
- MUST store JSON content in lock file (minimum fields):
  - `run_id: str`
  - `lock_id: str` (random token per acquisition attempt)
  - `pid: int`
  - `created_at: float` (epoch seconds)
  - `expires_at: float` (epoch seconds)
- MUST implement atomic acquisition:
  - Create file with exclusive create (O_CREAT|O_EXCL).
  - On success, write JSON and record ownership in-process for `release_run_lock`.
  - MUST handle partial-failure cleanup:
    - If file creation succeeded but JSON write fails, the implementation MUST delete the lock file (or rename to `*.stale.<ts>`) before raising/returning an error.
- MUST implement stale reclaim:
  - If lock file exists:
    - Read JSON; if parse fails → treat as stale
    - If `expires_at` < now → rename to `*.stale.<ts>` (ts is epoch seconds) and retry acquire
    - If rename fails due to race → return conflict
- MUST implement release:
  - Delete the lock file only if:
    - we currently hold it in-process (by `run_id -> lock_id`)
    - and the file on disk contains same `lock_id`
  - Otherwise no-op.

#### B) Conflict handling
- No changes required in `authority_runner.resume_run()` behavior:
  - lock acquisition failure already returns CONFLICT and does not update RunState.
- run_lock should return `(ok=False, reason=<code>)` where reason is stable string like:
  - `"LOCK_CONFLICT"` / `"LOCK_HELD"`

#### C) テスト更新
- `test_resume_lock_conflict.py`:
  - MUST set `NEXUSCORE_RUN_LOCK_DIR` to tmp dir.
  - MUST reproduce conflict by creating a **valid lock file** with `expires_at` in the future before calling `resume_run()`.
  - MUST assert (primary):
    - RunState is unchanged (no status transition / no update)
    - Returned value includes CONFLICT-equivalent reason/why_code (string match)
  - MAY assert (secondary, optional):
    - `result["status"] == "CONFLICT"` (if present)
- MUST ADD `test_run_lock_stale_reclaim.py`:
  - Create lock file with `expires_at` in the past.
  - Call `try_acquire_run_lock(run_id)` and assert it succeeds.
  - Assert the old lock file is moved to `*.stale.<ts>` and a new `<run_id>.lock` exists.

### 禁止事項（Prohibited Changes）
- MUST NOT modify `src/nexuscore/core/orchestrator.py`
- MUST NOT modify docs/spec Contract Layer (CR-NEXUS-016〜023)
- MUST NOT change `authority_runner.resume_run()` contract (CONFLICT not FAILED; no RunState update on conflict)

### テスト要件（commands）
- Run:
  - `bash dev_tools/run_tests.sh tests/orchestrator/`
- MUST generate and verify the auto-generated test report files (Markdown + JSON) and report:
  - total / passed / failed / skipped / errors / success rate / duration


