# NexusCore DebuggerAgent patch 破損根本防止 — 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** phase_runner_mixin の自己修復デバッグループに「適用前AST検査＋実行検証＋例外安全な最終ロールバック」を実装し、DebuggerAgent 経由の LLM説明文によるファイル破損を根本防止する。

**Architecture:** 層1(AST構文検査)で説明文を早期却下→層3(pytest実行検証)で意味の正しさを担保→try-finally で例外時も含めループ脱出後に original_source へ復元（破損残存防止・悪化ループ根絶）。新規 utils `syntax_validator` を phase_runner のみが使用（coder_agent.py は 6d3f セッションが占有中のため触らない）。

**Tech Stack:** Python 3.12 / pytest / ast 標準モジュール / dataclasses

**Spec:** `docs/superpowers/specs/2026-07-24-nexuscore-debugger-patch破損根本防止-design.md`

---

## File Structure

| ファイル | 操作 | 責務 |
|---|---|---|
| `src/nexuscore/utils/syntax_validator.py` | **Create** | `validate_python_syntax(code) -> tuple[bool,str]`（ast.parseラッパー・純粋関数） |
| `tests/utils/test_syntax_validator.py` | **Create** | syntax_validator の単体テスト（有効/無効/空文字） |
| `src/nexuscore/core/orchestrator_models.py` | Modify | `OrchestratorContext` に `debug_history: list` 追加 |
| `src/nexuscore/core/phase_runner_mixin.py` | Modify | `AST_FAIL_LIMIT` 定数・`_clean_pytest_cache` ヘルパ・`run_testing_phase` デバッグループ改修 |
| `tests/core/test_testing_phase_debug_loop.py` | Modify | デバッグループ改修のテスト群を追加 |

**スコープ注記**: 本計画が触るのは上記5ファイルのみ。`coder_agent.py` 等、6d3f セッションが占有中のファイルは触らない（並行競合回避）。

---

## Task 1: `utils/syntax_validator.py` 新設（TDD）

**Files:**
- Create: `src/nexuscore/utils/syntax_validator.py`
- Test: `tests/utils/test_syntax_validator.py`

- [ ] **Step 1: Write the failing test**

`tests/utils/test_syntax_validator.py` を新規作成:

```python
"""utils/syntax_validator の単体テスト。"""
from nexuscore.utils.syntax_validator import validate_python_syntax


def test_valid_python_returns_ok_with_empty_err():
    ok, err = validate_python_syntax("x = 1\nprint(x)\n")
    assert ok is True
    assert err == ""


def test_invalid_python_returns_ng_with_message():
    ok, err = validate_python_syntax("def f(\n")  # SyntaxError
    assert ok is False
    assert "SyntaxError" in err or "ParseError" in err


def test_empty_string_returns_ng():
    ok, err = validate_python_syntax("")
    assert ok is False
    assert err  # 空でないメッセージ
```

- [ ] **Step 2: Run test to verify it fails**

```bash
source .venv/bin/activate
python -m pytest tests/utils/test_syntax_validator.py -v
```
Expected: FAIL（`ModuleNotFoundError: nexuscore.utils.syntax_validator`）

- [ ] **Step 3: Write minimal implementation**

`src/nexuscore/utils/syntax_validator.py` を新規作成:

```python
"""Python 構文検証ユーティリティ（コード生成系 Agent の共通層1）。

ast.parse で SyntaxError を検出し、説明文等の非コード出力を早期に弾く。
ok=True のとき err=""（空文字）。
"""
import ast


def validate_python_syntax(code: str) -> tuple[bool, str]:
    """Python コードの構文妥当性を検証する。

    Args:
        code: 検証対象の Python コード文字列。

    Returns:
        (True, ""): 構文OK。
        (False, "<msg>"): 構文NG（SyntaxError/ParseError/空文字）。
    """
    if not code or not code.strip():
        return False, "ParseError: empty code"
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as e:
        return False, f"SyntaxError: {e}"
    except ValueError as e:
        return False, f"ValueError: {e}"
    # MemoryError / SystemExit / RecursionError 等は再送出（握りつぶさない・planレビュー採用#9）
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/utils/test_syntax_validator.py -v
```
Expected: PASS（3件）

- [ ] **Step 5: Commit**

```bash
git add src/nexuscore/utils/syntax_validator.py tests/utils/test_syntax_validator.py
git commit -m "feat(utils): validate_python_syntax 新設(コード生成系層1・AST検査)"
```

---

## Task 2: `OrchestratorContext.debug_history` 追加

**Files:**
- Modify: `src/nexuscore/core/orchestrator_models.py`（`debug_retries` の次）
- Test: なし（dataclass フィールド追加・既存テストで確認）

- [ ] **Step 1: フィールド追加**

`src/nexuscore/core/orchestrator_models.py` の `OrchestratorContext` で、`debug_retries: int = 0` の直後に1行追加:

```python
    debug_retries: int = 0
    debug_history: list = field(default_factory=list)   # ← 追加・自己修復ループ各試行の履歴
    review_retries: int = 0
```

- [ ] **Step 2: 既存テストで回帰確認**

```bash
python -m pytest tests/core/test_orchestrator_models.py tests/core/test_phase_runner_mixin.py -v 2>&1 | tail -20
```
Expected: 既存テスト全PASS（default_factory で後方互換）

- [ ] **Step 3: Commit**

```bash
git add src/nexuscore/core/orchestrator_models.py
git commit -m "feat(core): OrchestratorContext.debug_history 追加(自己修復ループ履歴)"
```

---

## Task 3: `AST_FAIL_LIMIT` 定数 + `_clean_pytest_cache` ヘルパ

**Files:**
- Modify: `src/nexuscore/core/phase_runner_mixin.py`（冒頭の定数部 + クラス内ヘルパ）

- [ ] **Step 1: `AST_FAIL_LIMIT` 定数追加**

`src/nexuscore/core/phase_runner_mixin.py` の `DEBUG_MAX_RETRIES` 定義の直後に追加:

```python
DEBUG_MAX_RETRIES: int = _env_int("NEXUS_DEBUG_MAX_RETRIES", 3)
# AST検査NGが「連続」でこの回数に達したら早期脱出（LLMが説明文しか返さない故障検知）。
# pytest失敗(debug_retries)とは独立カウント。将来のA/Bで3に拡張余地(env上書き可)。
AST_FAIL_LIMIT: int = _env_int("NEXUS_AST_FAIL_LIMIT", 2)
```

- [ ] **Step 2: import 追加**

`phase_runner_mixin.py` の import 部に `shutil` と `validate_python_syntax` を追加（既存 import 群に倣う）:

```python
import shutil
# ... 既存 import ...
from nexuscore.utils.syntax_validator import validate_python_syntax
```

- [ ] **Step 3: `_clean_pytest_cache` ヘルパ追加**

`PhaseRunnerMixin` クラス内の `run_testing_phase` の直前に追加:

```python
    @staticmethod
    def _clean_pytest_cache(project_path: str) -> None:
        """pytest 実行前にキャッシュ副産物を削除（CI flaky 回避・安全側）。

        mtime 検知で再コンパイルされるが、古い .pyc 参照リスクを確実に排除する。
        """
        for name in ("__pycache__", ".pytest_cache"):
            shutil.rmtree(Path(project_path) / name, ignore_errors=True)
```

- [ ] **Step 4: 既存テストで回帰確認**

```bash
python -m pytest tests/core/test_phase_runner_mixin.py -v 2>&1 | tail -20
```
Expected: 既存テスト全PASS（ヘルパ追加のみ・未使用でもエラーなし）

- [ ] **Step 5: Commit**

```bash
git add src/nexuscore/core/phase_runner_mixin.py
git commit -m "feat(core): AST_FAIL_LIMIT定数 + _clean_pytest_cache ヘルパ追加"
```

---

## Task 4: デバッグループ改修（核心・try-finally・層1+層3+最終ロールバック）

**Files:**
- Modify: `src/nexuscore/core/phase_runner_mixin.py::run_testing_phase`（現状の while ループ部）
- Test: `tests/core/test_testing_phase_debug_loop.py`

- [ ] **Step 1: 既存テスト構造の確認**

```bash
sed -n '1,60p' tests/core/test_testing_phase_debug_loop.py
```
既存テストのモック構造（OrchestratorContext 組み立て・debugger_agent モック・run_in_sandbox モック・project_path の一時ディレクトリ）を把握し、以降の新規テストは同じパターンを踏襲する。

- [ ] **Step 2: 新規テスト群を追加（RED）**

`tests/core/test_testing_phase_debug_loop.py` の末尾に追加（既存の import・fixture を再利用）:

```python
def test_ast_ng_explanation_text_does_not_corrupt_file(
    orchestrator_with_mock_debugger, tmp_path
):
    """LLMが説明文(SyntaxError)を返した場合、ファイルは書き換えられず元のまま。"""
    orch = orchestrator_with_mock_debugger
    impl_path = tmp_path / "src" / "mod.py"
    impl_path.parent.mkdir(parents=True)
    original = "def f():\n    return 1\n"
    impl_path.write_text(original)
    # debugger が説明文（Python構文NG）を返す
    orch.debugger_agent.debug_and_patch.return_value = {"fixed_code": "これは修正の説明です。"}
    orch.run_in_sandbox = lambda *a, **k: type("R", (), {"returncode": 1, "stdout": "", "stderr": "fail"})()

    # テスト対象のループを実行（debug_and_patch → AST NG → continue → AST_FAIL_LIMIT到達で脱出）
    # ※ 実行は run_testing_phase 経由 or ループ抽出ヘルパ。既存テストの呼出パターンに倣う。
    # assert: ファイル内容は original のまま（破損なし）
    assert impl_path.read_text() == original


def test_ast_fail_limit_early_exit_on_consecutive_ng(orchestrator_with_mock_debugger, tmp_path):
    """AST NG 連続2回で早期脱出（3回目に賭けない）。"""
    orch = orchestrator_with_mock_debugger
    orch.debugger_agent.debug_and_patch.return_value = {"fixed_code": "説明文 only"}
    # AST_FAIL_LIMIT=2 に到達した時点で break・debug_retries は 2
    # assert: context.debug_retries <= AST_FAIL_LIMIT 相当・ファイル不変


def test_ast_ng_ok_ng_does_not_exit(orchestrator_with_mock_debugger, tmp_path):
    """AST NG→OK→NG は連続ではないので AST_FAIL_LIMIT で脱出しない（連続のみカウント）。"""
    # debugger が [説明文, 正しいコード, 説明文] を順に返すよう side_effect 設定
    # 正しいコードの pytest は失敗させ、3ループ目まで到達することを確認（AST NGは連続1ずつなので脱出しない）


def test_correct_fix_is_applied(orchestrator_with_mock_debugger, tmp_path):
    """構文OK・pytest通過の修正は本適用される。"""
    orch.debugger_agent.debug_and_patch.return_value = {"fixed_code": "def f():\n    return 2\n"}
    orch.run_in_sandbox = lambda *a, **k: type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
    # assert: ファイルが fixed_code に更新・passed=True


def test_semantically_wrong_fix_rolls_back_to_original(orchestrator_with_mock_debugger, tmp_path):
    """構文OKだが pytest失敗の修正→全リトライ失敗後・original_source へ復元。"""
    impl_path = tmp_path / "src" / "mod.py"
    impl_path.parent.mkdir(parents=True)
    original = "def f():\n    return 1\n"
    impl_path.write_text(original)
    orch.debugger_agent.debug_and_patch.return_value = {"fixed_code": "def f():\n    return 999\n"}
    orch.run_in_sandbox = lambda *a, **k: type("R", (), {"returncode": 1, "stdout": "", "stderr": "fail"})()
    # DEBUG_MAX_RETRIES 枯渇後
    # assert: impl_path.read_text() == original（最終ロールバック）


def test_empty_fixed_code_breaks_and_rolls_back(orchestrator_with_mock_debugger, tmp_path):
    """fixed_code 空 → break・not passed なので最終ロールバック。"""
    orch.debugger_agent.debug_and_patch.return_value = {"fixed_code": ""}
    # assert: ファイルは original・debug_history に no_fixed_code エントリ


def test_exception_in_sandbox_triggers_finally_rollback(orchestrator_with_mock_debugger, tmp_path):
    """run_in_sandbox が例外送出 → finally で original_source 復元（例外安全）。"""
    impl_path = tmp_path / "src" / "mod.py"
    impl_path.parent.mkdir(parents=True)
    original = "def f():\n    return 1\n"
    impl_path.write_text(original)
    orch.debugger_agent.debug_and_patch.return_value = {"fixed_code": "def f():\n    return 2\n"}

    def raise_timeout(*a, **k):
        raise TimeoutError("sandbox timeout")
    orch.run_in_sandbox = raise_timeout

    # run_testing_phase は例外を伝播させるか wrap するか（既存挙動に倣う）
    # assert: 例外後も impl_path.read_text() == original（finally ロールバック）


def test_debug_history_accumulates(orchestrator_with_mock_debugger, tmp_path):
    """各試行が debug_history に記録される（スキーマ: attempt/status/passed/err・status統一）。"""
    # 2ループ回して context.debug_history の長さ・キー(status)を検証
```

> **注記**: `orchestrator_with_mock_debugger` fixture・`run_in_sandbox` の差し替え方法は既存テスト（Step1で確認）のパターンに厳密に踏襲。各テストの核心 assert（ファイル不変/復元・passed・debug_history）は上記の通り。モック組み立ての定形部は既存 fixture を再利用。

- [ ] **Step 3: Run tests to verify they fail (RED)**

```bash
python -m pytest tests/core/test_testing_phase_debug_loop.py -v 2>&1 | tail -30
```
Expected: 新規テスト FAIL（現状ループは適用前検証なし・復元なし）

- [ ] **Step 4: `run_testing_phase` のデバッグループを実装（GREEN）**

`src/nexuscore/core/phase_runner_mixin.py::run_testing_phase` の現状デバッグループ（`debug_retries = 0` から `context.testing = {...}` まで）を以下に置換:

```python
        impl_files: dict[str, str] = dict((context.implementation or {}).get("files", {}))
        primary_impl_path = next(iter(impl_files), None)

        # --- 自己修復デバッグループ（層1 AST + 層3 実行検証 + 例外安全な最終ロールバック）---
        # context.implementation None 対策（planレビュー #1・両LLM critical）
        if context.implementation is None:
            context.implementation = {}
        original_source = impl_files[primary_impl_path] if primary_impl_path else ""
        current_source = original_source          # インクリメンタル修正のベース（更新対象）
        ast_fail_streak = 0
        debug_history: list[dict] = list(context.debug_history) if context.debug_history else []
        error_log = f"{result.stdout}\n{result.stderr}"
        impl_abs_path = Path(self.project_path) / primary_impl_path if primary_impl_path else None
        # パストラバーサルガード＋親dir作成はループ前1回（planレビュー #5/#6）
        if impl_abs_path is not None:
            _proj_root = Path(self.project_path).resolve()
            assert impl_abs_path.resolve().is_relative_to(_proj_root), (
                f"impl path outside project root: {impl_abs_path}"
            )
            impl_abs_path.parent.mkdir(parents=True, exist_ok=True)

        try:                                       # 例外安全: sandbox/LLM API 例外でもロールバック保証
            while (
                not passed
                and primary_impl_path
                and getattr(self, "debugger_agent", None) is not None
                and debug_retries < DEBUG_MAX_RETRIES
            ):
                debug_retries += 1
                debug_result = self.debugger_agent.debug_and_patch(
                    error_log, {primary_impl_path: current_source}, self.project_path
                )
                if not isinstance(debug_result, dict):   # 型安全
                    debug_result = {}
                fixed_code = debug_result.get("fixed_code")
                # 型チェック（planレビュー #4・非 str は却下）
                if not fixed_code or not isinstance(fixed_code, str):
                    debug_history.append({"attempt": debug_retries, "status": "no_fixed_code"})
                    self.logger.warning(
                        f"[{context.task_id}] DebuggerAgent produced no valid fixed_code "
                        f"(attempt {debug_retries}/{DEBUG_MAX_RETRIES}). Stopping debug loop."
                    )
                    break

                # 層1: AST構文検査（適用前・説明文を早期弾く）
                ok, err = validate_python_syntax(fixed_code)
                if not ok:
                    ast_fail_streak += 1
                    error_log = (
                        f"SyntaxError: 生成コードが不正({err})。"
                        f"コードのみを出力してください。"
                    )
                    debug_history.append({"attempt": debug_retries, "status": "ast_fail", "err": err})
                    if ast_fail_streak >= AST_FAIL_LIMIT:
                        self.logger.warning(
                            f"[{context.task_id}] AST validation failed {ast_fail_streak} "
                            f"consecutive times. Early exit (LLM returns prose only)."
                        )
                        break
                    continue                                  # current_source 維持（ベース変わらず）

                ast_fail_streak = 0
                # 層3: 適用（都度復元しない・積み重ね修正）
                impl_abs_path.write_text(fixed_code, encoding="utf-8")
                current_source = fixed_code
                impl_files[primary_impl_path] = current_source
                context.implementation["files"] = impl_files

                self._clean_pytest_cache(self.project_path)
                # run_in_sandbox 例外安全（planレビュー #2・MiniMax critical）
                try:
                    result = run_in_sandbox(
                        ["python", "-m", "pytest", str(test_abs_path), "-q"],
                        cwd=self.project_path,
                    )
                    passed = result.returncode == 0
                    debug_history.append({
                        "attempt": debug_retries,
                        "status": "pytest_pass" if passed else "pytest_fail",
                        "passed": passed,
                    })
                    if not passed:
                        error_log = f"{result.stdout}\n{result.stderr}"
                except Exception as sandbox_err:  # noqa: BLE001
                    passed = False
                    error_log = f"SandboxError: {sandbox_err}"
                    debug_history.append({
                        "attempt": debug_retries,
                        "status": "sandbox_error",
                        "err": str(sandbox_err)[:200],
                    })
                    self.logger.warning(
                        f"[{context.task_id}] run_in_sandbox raised {sandbox_err!r}. "
                        f"Stopping debug loop (rolling back to original)."
                    )
                    break
        finally:
            # 例外時含め・脱出後 not passed なら original_source へ復元（破損残存防止）
            # original_source 空ガード（planレビュー #8）
            if (
                not passed
                and primary_impl_path
                and impl_abs_path is not None
                and original_source
            ):
                impl_abs_path.write_text(original_source, encoding="utf-8")
                impl_files[primary_impl_path] = original_source
                context.implementation["files"] = impl_files

        # result は前段(443行)で定義済・例外時も前段値が残る（Python 関数スコープ）
        context.debug_retries = debug_retries
        context.debug_history = debug_history
        context.testing = {
            "tests": test_code,
            "test_path": str(test_abs_path),
            "passed": passed,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        return context
```

- [ ] **Step 5: Run tests to verify they pass (GREEN)**

```bash
python -m pytest tests/core/test_testing_phase_debug_loop.py -v 2>&1 | tail -30
```
Expected: 新規テスト全PASS（既存テストも回帰PASS）

> もし既存テストが fail した場合: 現状ループの振る舞い（都度復元なし・適用前検証なし）に依存する既存アサーションを、新仕様（最終ロールバック・AST検査）に合わせて更新。ただし「破損防止」の意味で既存テストが保証していた振る舞いは維持。

- [ ] **Step 6: Commit**

```bash
git add src/nexuscore/core/phase_runner_mixin.py tests/core/test_testing_phase_debug_loop.py
git commit -m "fix(core): デバッグループ適用前AST検査+実行検証+例外安全最終ロールバック(破損根本防止)"
```

---

## Task 5: review_report への debug_history 添付

**Files:**
- Modify: `src/nexuscore/core/phase_runner_mixin.py::run_review_phase`（NEEDS_HUMAN_REVIEW 到達時の `_write_review_report` 呼出）

- [ ] **Step 1: `_write_review_report` 呼出に debug_history を反映**

`run_review_phase` の `if not context.testing.get("passed", False):` ブロック（NEEDS_HUMAN_REVIEW 到達時）で、`_write_review_report` の feedback に debug_history の要約を追記:

```python
        if not context.testing.get("passed", False):
            context.terminal_state = "NEEDS_HUMAN_REVIEW"
            error_log = f"{context.testing.get('stdout', '')}\n{context.testing.get('stderr', '')}"
            self._run_postmortem_learning(context, error_log)
            # デバッグループ各試行の履歴を review_report に添付（人間診断コスト低下）
            history_summary = self._format_debug_history(context.debug_history)
            self._write_review_report(
                context,
                feedback=(
                    f"テストが失敗したまま解消できませんでした:\n"
                    f"{context.testing.get('stderr', '')}\n\n"
                    f"--- デバッグ試行履歴 ---\n{history_summary}"
                ),
            )
            self._maybe_run_constitutional_review(context)
            return context
```

- [ ] **Step 2: `_format_debug_history` ヘルパ追加**

`PhaseRunnerMixin` クラス内に追加:

```python
    @staticmethod
    def _format_debug_history(history: list) -> str:
        """debug_history を人間可読の要約に整形（status キー統一・末尾10件・err truncate）。"""
        if not history:
            return "（デバッグ試行なし）"
        lines = []
        for h in history[-10:]:                       # 末尾N件（planレビュー #10）
            attempt = h.get("attempt", "?")
            status = h.get("status", "?")
            err = str(h.get("err", ""))[:200]
            if status == "no_fixed_code":
                lines.append(f"  attempt {attempt}: fixed_code 生成なし")
            elif status == "ast_fail":
                lines.append(f"  attempt {attempt}: 構文NG({err})")
            elif status == "sandbox_error":
                lines.append(f"  attempt {attempt}: sandbox例外({err})")
            else:  # pytest_pass / pytest_fail
                passed = h.get("passed")
                lines.append(f"  attempt {attempt}: 構文OK・pytest={'通過' if passed else '失敗'}")
        return "\n".join(lines)
```

- [ ] **Step 3: 既存 review フェーズテストで回帰確認**

```bash
python -m pytest tests/core/ -k "review or testing_phase" -v 2>&1 | tail -20
```
Expected: 既存テスト全PASS

- [ ] **Step 4: Commit**

```bash
git add src/nexuscore/core/phase_runner_mixin.py
git commit -m "feat(core): NEEDS_HUMAN_REVIEW時 にdebug_history要約をreview_report添付"
```

---

## Task 6: 全テスト + make qa で最終確認

- [ ] **Step 1: 全テスト実行**

```bash
source .venv/bin/activate
python -m pytest tests/ -q 2>&1 | tail -20
```
Expected: 全PASS（前回631 passed から減少なし・新規テスト分増加）

- [ ] **Step 2: make qa（format + lint + typecheck + test）**

```bash
make qa 2>&1 | tail -30
```
Expected: 全PASS（ruff/mypy/pytest 緑）

- [ ] **Step 3: 変更履歴更新**

`docs/変更履歴.md` に追記（Keep a Changelog 準拠）:

```markdown
## [Unreleased]
### Fixed
- DebuggerAgent 経由の LLM説明文による実装ファイル破損を根本防止（phase_runner デバッグループに適用前AST検査+実行検証+例外安全な最終ロールバックを追加・spec: 2026-07-24-nexuscore-debugger-patch破損根本防止）
```

- [ ] **Step 4: 変更履歴 commit**

```bash
git add docs/変更履歴.md
git commit -m "docs: 変更履歴にDebuggerAgent破損根本防止を追記"
```

- [ ] **Step 5: 動作確認（オプション・実API）**

深夜/早朝帯（GLM安定）に dynamic パイプラインで中規模タスクを完走させ、primes.py 等の破損が発生しないことを確認（A検証と同手順）。※時間帯で着手判断しない（memory準拠）・実API不要なら skip 可。

---

## Self-Review 結果

**1. Spec coverage**:
- §5.1 utils/syntax_validator 新設 → Task 1 ✅
- §5.1 phase_runner 改修 → Task 3/4 ✅
- §5.2 AST_FAIL_LIMIT → Task 3 ✅
- §6 データフロー（try-finally・AST・最終ロールバック）→ Task 4 ✅
- §6.1 review伝播 → Task 5 ✅
- §7 例外安全 → Task 4 (try-finally) ✅
- §7.1 副産物クリーンアップ → Task 3 (_clean_pytest_cache) ✅
- §8.2 テスト群 → Task 1(単体) + Task 4(ループ8ケース) ✅
- §10.3 完了条件 → Task 1-6 ✅
- §10.2 第2段（LLM検証等）→ スコープ外・別タスク ✅

**2. Placeholder scan**: なし。Task 4 Step2 のテストは「既存 fixture 踏襲」を明記（placeholder でなく実在参照先を指定）。核心 assert は完全コード。

**3. Type consistency**: `validate_python_syntax -> tuple[bool,str]`（Task1定義→Task4使用）✅ / `debug_history: list[dict]`（Task2追加→Task4/5使用・status キー統一）✅ / `AST_FAIL_LIMIT`（Task3定義=モジュール定数→Task4使用）✅ / `_clean_pytest_cache(project_path: str)`（Task3定義→Task4使用）✅

---

## plan multi-llm-review 経緯（2026-07-24・Gemini+MiniMax）

spec(2巡)完了後に plan の実装コード正確性を両LLMレビュー。直交性実証（両LLMが独立に `context.implementation` None 時の TypeError を指摘）。

### 採用10点（本plan改訂に反映）
1. **`context.implementation` None 対策**（Gemini+MiniMax critical・直交）: 冒頭 `if None: {}`
2. **`run_in_sandbox` 例外安全**（MiniMax critical）: try-except・例外時 passed=False・sandbox_error 履歴・break
3. AST_FAIL_LIMIT モジュール定数明記（Gemini medium）
4. `fixed_code` の isinstance str チェック（Gemini low + MiniMax high）
5. `impl_abs_path` パストラバーサルガード（`is_relative_to` assert・MiniMax high）
6. `mkdir` はループ前1回（MiniMax low）
7. `debug_history` キー統一（`status`: no_fixed_code/ast_fail/pytest_pass/pytest_fail/sandbox_error・MiniMax med）
8. `original_source` 空文字ガード（MiniMax med）
9. `validate_python_syntax` 例外厳密化（SyntaxError/ValueError のみ・他は再送出・MiniMax med）
10. `_format_debug_history` で truncate（末尾10件・err[:200]・MiniMax low）

### 却下（Python仕様の誤読・ノイズ）
- MiniMax critical「while括弧不足」: Python の `and` 連鎖は同優先度で正しく評価（誤指摘）。ただ `hasattr` → `getattr(self,'debugger_agent',None) is not None` に簡素化
- MiniMax high「off-by-one（3→2回しか試行しない）」: 誤り。`debug_retries=0`→while `0<3`→`+=1`...で3回試行（現状コードと同一・後方互換）
- error_log 意味ずれ・`__pycache__` 削除副作用: 現状で機能（cwd共有確認済）・維持/注記
