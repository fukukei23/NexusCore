# Stage 3 学習レイヤー実装 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** postmortem / knowledge_curator / policy_agent の3体を固定パイプラインに実配線し、「12エージェント協調」を実態と一致させる（Stage 3・spec §5）。

**Architecture:** Phase 6 (`run_review_phase`) の2つの終端点に学習フックを追加する。(a) テスト失敗枯渇でNEEDS_HUMAN_REVIEWになる分岐で `postmortem_agent.analyze_failure_and_suggest_fkb_entry()` → `knowledge_curator_agent.validate_fkb_suggestion()` を呼び、サンドボックスで実際にテストが通ることを検証できた解のみ中央FKB（`database.knowledge_base.add_knowledge()`）へ永続化する（汚染防止）。分析結果自体は検証の成否に関わらず既存の `context.postmortem_report` フィールドへ格納し、既に実装済みだが今まで発火していなかった `_maybe_run_constitutional_review()` を初めて起動させる。(b) guardianがAPPROVEした直後に `policy_agent.audit()` の結果を `allow_commit` として `guardian_agent.review_and_commit()` に渡し、ポリシー違反時はコミットをブロックする。debuggerがFKBを参照する経路（`_find_solution_from_kb`）は既存実装のみで接続済みのため、コード変更なしで回帰テストのみ追加する。

**Tech Stack:** Python 3.12 / pytest / SQLAlchemy（`database/knowledge_base.py`・SQLite tmp file で検証）/ 既存エージェント（PostmortemAgent / KnowledgeCuratorAgent / PolicyAgent / GuardianAgent.review_and_commit）

---

## 前提

- ブランチ: `feat/stage3-learning-layer`（`main` から作成）
- 各タスク完了ごとに `python -m pytest tests/core/ tests/agents/ -q` を実行し緑を確認してからcommit
- 最終タスクで全4,800+テストの回帰ゲートを実行

---

### Task 1: ブランチ作成

**Files:** なし（git操作のみ）

- [ ] **Step 1: worktreeまたはブランチを作成**

```bash
git checkout main && git pull --ff-only
git checkout -b feat/stage3-learning-layer
```

---

### Task 2: postmortem学習フック（`_run_postmortem_learning`）

**Files:**
- Modify: `src/nexuscore/core/phase_runner_mixin.py`
- Test: `tests/core/test_postmortem_learning_hook.py`（新規）

- [ ] **Step 1: 失敗するテストを書く**

`tests/core/test_postmortem_learning_hook.py` を新規作成:

```python
"""run_review_phase() のpostmortem学習フックのテスト（Stage 3・spec §5）。"""

from typing import Any
from unittest.mock import Mock, patch

from nexuscore.core.orchestrator import Orchestrator, OrchestratorContext
from nexuscore.llm.llm_router import LLMRouter


def _create_mock_agents() -> dict[str, Any]:
    architect_agent = Mock()
    architect_agent.design_architecture.return_value = {"design_directive": "d"}
    guardian_agent = Mock()
    guardian_agent.review = Mock(return_value={"decision": "APPROVE", "reason": "ok"})
    policy_agent = Mock()
    policy_agent.audit = Mock(return_value={"result": "APPROVED", "violations": []})
    guardian_agent.review_and_commit = Mock(
        return_value={"decision": "APPROVE", "reason": "ok", "commit": "abc123"}
    )
    return {
        "requirement_agent": Mock(),
        "architect_agent": architect_agent,
        "planner_agent": Mock(),
        "coder_agent": Mock(),
        "tester_agent": Mock(),
        "debugger_agent": Mock(),
        "guardian_agent": guardian_agent,
        "policy_agent": policy_agent,
        "postmortem_agent": Mock(),
        "knowledge_curator_agent": Mock(),
        "patch_applier_agent": Mock(),
    }


def _make_orchestrator(tmp_path, agents):
    return Orchestrator(
        project_path=str(tmp_path),
        constitution={"rule": "x"},
        llm_router=Mock(spec=LLMRouter),
        **agents,
    )


def _failing_test_context(tmp_path):
    test_path = tmp_path / "tests" / "test_main.py"
    test_path.parent.mkdir(parents=True, exist_ok=True)
    test_path.write_text("def test_x():\n    assert False\n", encoding="utf-8")

    context = OrchestratorContext(task_id="t1", user_requirement="req")
    context.implementation = {"files": {"main.py": "def broken(): return 1/0"}}
    context.testing = {
        "tests": "def test_x():\n    assert False\n",
        "test_path": str(test_path),
        "passed": False,
        "stdout": "",
        "stderr": "ZeroDivisionError: division by zero",
    }
    return context


class TestPostmortemLearningHook:
    def test_validated_suggestion_is_persisted_to_fkb(self, tmp_path):
        agents = _create_mock_agents()
        suggestion = {
            "id": "FKB-SUGGESTION-0001",
            "error_signature": "ZeroDivisionError",
            "cause": "ゼロ除算",
            "target": "source_file",
            "solution_pattern": {"type": "llm_diagnose_and_fix", "instruction": "fix it"},
            "description": "desc",
        }
        agents["postmortem_agent"].analyze_failure_and_suggest_fkb_entry = Mock(
            return_value=suggestion
        )
        agents["knowledge_curator_agent"].validate_fkb_suggestion = Mock(return_value=True)

        orchestrator = _make_orchestrator(tmp_path, agents)
        context = _failing_test_context(tmp_path)

        with patch("database.knowledge_base.knowledge_base") as mock_kb:
            mock_kb.add_knowledge.return_value = "created"
            result = orchestrator.run_review_phase(context)

        assert result.terminal_state == "NEEDS_HUMAN_REVIEW"
        assert result.postmortem_report == suggestion
        agents["knowledge_curator_agent"].validate_fkb_suggestion.assert_called_once()
        mock_kb.add_knowledge.assert_called_once_with(suggestion)

    def test_unvalidated_suggestion_is_not_persisted(self, tmp_path):
        agents = _create_mock_agents()
        suggestion = {
            "id": "FKB-SUGGESTION-0002",
            "error_signature": "ZeroDivisionError",
            "cause": "c",
            "target": "source_file",
            "solution_pattern": {"type": "llm_diagnose_and_fix", "instruction": "i"},
            "description": "d",
        }
        agents["postmortem_agent"].analyze_failure_and_suggest_fkb_entry = Mock(
            return_value=suggestion
        )
        agents["knowledge_curator_agent"].validate_fkb_suggestion = Mock(return_value=False)

        orchestrator = _make_orchestrator(tmp_path, agents)
        context = _failing_test_context(tmp_path)

        with patch("database.knowledge_base.knowledge_base") as mock_kb:
            result = orchestrator.run_review_phase(context)

        assert result.postmortem_report == suggestion
        mock_kb.add_knowledge.assert_not_called()

    def test_no_suggestion_leaves_postmortem_report_empty(self, tmp_path):
        agents = _create_mock_agents()
        agents["postmortem_agent"].analyze_failure_and_suggest_fkb_entry = Mock(
            return_value=None
        )

        orchestrator = _make_orchestrator(tmp_path, agents)
        context = _failing_test_context(tmp_path)

        result = orchestrator.run_review_phase(context)

        assert result.postmortem_report == {}
        agents["knowledge_curator_agent"].validate_fkb_suggestion.assert_not_called()
```

- [ ] **Step 2: テストを実行し失敗を確認**

Run: `python -m pytest tests/core/test_postmortem_learning_hook.py -v`
Expected: FAIL（`postmortem_agent.analyze_failure_and_suggest_fkb_entry` が呼ばれず `result.postmortem_report == {}` のまま・assert失敗）

- [ ] **Step 3: `_run_postmortem_learning` を実装**

`src/nexuscore/core/phase_runner_mixin.py` の `_write_review_report` メソッドの直前（586行目付近、`_maybe_run_constitutional_review` の直前）に以下を追加:

```python
    def _run_postmortem_learning(self, context: OrchestratorContext, error_log: str) -> None:
        """postmortemで失敗分析→knowledge_curatorで検証→検証済みのみFKBへ永続化する（spec §5）。

        分析結果は検証の成否に関わらず context.postmortem_report に格納し、
        既存の _maybe_run_constitutional_review に渡す（同フックは実装済みだが
        postmortem_report が常に空だったため今まで発火していなかった）。
        """
        postmortem_agent = getattr(self, "postmortem_agent", None)
        if postmortem_agent is None or not hasattr(
            postmortem_agent, "analyze_failure_and_suggest_fkb_entry"
        ):
            return

        impl_files = (context.implementation or {}).get("files", {})
        source_rel_path = next(iter(impl_files), None)
        test_abs_path = context.testing.get("test_path")
        if not source_rel_path or not test_abs_path:
            return

        source_code = impl_files[source_rel_path]
        source_abs_path = str(Path(self.project_path) / source_rel_path)
        try:
            test_code = Path(test_abs_path).read_text(encoding="utf-8")
        except OSError:
            test_code = context.testing.get("tests", "")

        try:
            suggestion = postmortem_agent.analyze_failure_and_suggest_fkb_entry(
                error_log=error_log,
                source_code=source_code,
                test_code=test_code,
                source_file_path=source_abs_path,
                test_file_path=str(test_abs_path),
            )
        except Exception as e:  # noqa: BLE001 — optional learning step, graceful skip
            self.logger.warning(f"[{context.task_id}] PostmortemAgent failed (graceful skip): {e}")
            return

        if not suggestion:
            return

        context.postmortem_report = suggestion

        curator = getattr(self, "knowledge_curator_agent", None)
        if curator is None or not hasattr(curator, "validate_fkb_suggestion"):
            return

        try:
            validated = curator.validate_fkb_suggestion(
                suggestion=suggestion,
                original_project_path=self.project_path,
                failed_test_path=str(test_abs_path),
                related_source_path=source_abs_path,
                original_test_output=error_log,
            )
        except Exception as e:  # noqa: BLE001 — optional learning step, graceful skip
            self.logger.warning(f"[{context.task_id}] KnowledgeCuratorAgent validation failed: {e}")
            return

        if not validated:
            self.logger.info(
                f"[{context.task_id}] FKB suggestion failed sandbox validation; not persisted (spec §5)."
            )
            return

        try:
            from database.knowledge_base import knowledge_base

            status = knowledge_base.add_knowledge(suggestion)
            self.logger.info(f"[{context.task_id}] FKB entry persisted: status={status}")
        except Exception as e:  # noqa: BLE001 — optional learning step, graceful skip
            self.logger.warning(f"[{context.task_id}] Failed to persist FKB entry: {e}")
```

- [ ] **Step 4: `run_review_phase` のテスト失敗枯渇分岐から呼び出す**

`src/nexuscore/core/phase_runner_mixin.py` の `run_review_phase` 内、以下の既存コード:

```python
        # spec §4-4(b): debugリトライ枯渇でテスト失敗のままの場合はguardianを呼ばずNEEDS_HUMAN_REVIEW
        if not context.testing.get("passed", False):
            context.terminal_state = "NEEDS_HUMAN_REVIEW"
            self._write_review_report(
                context, feedback=f"テストが失敗したまま解消できませんでした:\n{context.testing.get('stderr', '')}"
            )
            self._maybe_run_constitutional_review(context)
            return context
```

を以下に置き換える:

```python
        # spec §4-4(b): debugリトライ枯渇でテスト失敗のままの場合はguardianを呼ばずNEEDS_HUMAN_REVIEW
        if not context.testing.get("passed", False):
            context.terminal_state = "NEEDS_HUMAN_REVIEW"
            error_log = f"{context.testing.get('stdout', '')}\n{context.testing.get('stderr', '')}"
            self._run_postmortem_learning(context, error_log)
            self._write_review_report(
                context, feedback=f"テストが失敗したまま解消できませんでした:\n{context.testing.get('stderr', '')}"
            )
            self._maybe_run_constitutional_review(context)
            return context
```

- [ ] **Step 5: テストを実行し成功を確認**

Run: `python -m pytest tests/core/test_postmortem_learning_hook.py -v`
Expected: PASS（3件）

- [ ] **Step 6: 既存のPhase 5/6回帰テストを確認**

Run: `python -m pytest tests/core/test_testing_phase_debug_loop.py tests/core/test_review_phase_guardian_loop.py -v`
Expected: 全PASS（`test_review_phase_skips_guardian_when_tests_still_failing` は `postmortem_agent`/`knowledge_curator_agent` がMockのままなので、`analyze_failure_and_suggest_fkb_entry` の戻り値が自動生成Mockオブジェクト＝truthyになり `context.postmortem_report` にMockが入るだけで、既存assertion（`terminal_state`/`review_report.md`）には影響しない）

- [ ] **Step 7: Commit**

```bash
git add src/nexuscore/core/phase_runner_mixin.py tests/core/test_postmortem_learning_hook.py
git commit -m "feat: postmortem学習フックを実配線（テスト失敗枯渇時にFKB検証済み知見のみ永続化・spec §5）"
```

---

### Task 3: policy_agent + review_and_commit 接続

**Files:**
- Modify: `src/nexuscore/core/phase_runner_mixin.py`
- Modify: `tests/core/test_review_phase_guardian_loop.py`

- [ ] **Step 1: 既存テストの `_create_mock_agents` に `review_and_commit` と `policy_agent.audit` のモックを追加**

`tests/core/test_review_phase_guardian_loop.py` の `_create_mock_agents` 内、以下の行:

```python
    guardian_agent = Mock()
    guardian_agent.review = Mock(return_value={"decision": "APPROVE", "reason": "ok"})
```

を以下に置き換える:

```python
    guardian_agent = Mock()
    guardian_agent.review = Mock(return_value={"decision": "APPROVE", "reason": "ok"})
    guardian_agent.review_and_commit = Mock(
        return_value={"decision": "APPROVE", "reason": "ok", "commit": "abc123"}
    )
```

同ファイル内、以下の行:

```python
    return {
        "requirement_agent": requirement_agent,
        "architect_agent": architect_agent,
        "planner_agent": Mock(),
        "coder_agent": Mock(),
        "tester_agent": tester_agent,
        "debugger_agent": debugger_agent,
        "guardian_agent": guardian_agent,
        "policy_agent": Mock(),
        "postmortem_agent": Mock(),
        "knowledge_curator_agent": Mock(),
        "patch_applier_agent": Mock(),
    }
```

を以下に置き換える（`policy_agent.audit` を明示的にAPPROVED返却へ）:

```python
    policy_agent = Mock()
    policy_agent.audit = Mock(return_value={"result": "APPROVED", "violations": []})
    return {
        "requirement_agent": requirement_agent,
        "architect_agent": architect_agent,
        "planner_agent": Mock(),
        "coder_agent": Mock(),
        "tester_agent": tester_agent,
        "debugger_agent": debugger_agent,
        "guardian_agent": guardian_agent,
        "policy_agent": policy_agent,
        "postmortem_agent": Mock(),
        "knowledge_curator_agent": Mock(),
        "patch_applier_agent": Mock(),
    }
```

- [ ] **Step 2: 新規テストを追加（policyブロック時にNEEDS_HUMAN_REVIEWになること）**

`tests/core/test_review_phase_guardian_loop.py` の `TestReviewPhaseGuardianLoop` クラス末尾（`test_review_phase_bypasses_guardian_in_fast_lane` の後）に追加:

```python
    def test_review_phase_calls_review_and_commit_with_policy_allow_commit(self, tmp_path):
        """guardian APPROVE後、policy_agent.auditの結果がallow_commitとしてreview_and_commitに渡ること"""
        agents = _create_mock_agents()
        agents["guardian_agent"].review.return_value = {"decision": "APPROVE", "reason": "ok"}
        agents["guardian_agent"].review_and_commit.return_value = {
            "decision": "APPROVE", "reason": "ok", "commit": "deadbeef",
        }

        orchestrator = self._make_orchestrator(tmp_path, agents)
        context = self._context_with_passing_tests(tmp_path)

        result = orchestrator.run_review_phase(context)

        assert result.terminal_state == "APPROVED"
        agents["policy_agent"].audit.assert_called_once()
        agents["guardian_agent"].review_and_commit.assert_called_once()
        call_kwargs = agents["guardian_agent"].review_and_commit.call_args.kwargs
        assert call_kwargs["allow_commit"] is True
        assert call_kwargs["changed_files"] == ["app.py"]
        assert result.review["commit"] == "deadbeef"

    def test_review_phase_blocks_commit_on_policy_violation(self, tmp_path):
        """policy_agent.auditがREJECTEDならallow_commit=Falseで渡し、review_and_commitがREJECTを返したらNEEDS_HUMAN_REVIEWになること"""
        agents = _create_mock_agents()
        agents["guardian_agent"].review.return_value = {"decision": "APPROVE", "reason": "ok"}
        agents["policy_agent"].audit.return_value = {
            "result": "REJECTED", "violations": ["banned pattern"],
        }
        agents["guardian_agent"].review_and_commit.return_value = {
            "decision": "REJECT", "reason": "policy blocked", "feedback_for_coder": "ポリシー違反",
        }

        orchestrator = self._make_orchestrator(tmp_path, agents)
        context = self._context_with_passing_tests(tmp_path)

        result = orchestrator.run_review_phase(context)

        call_kwargs = agents["guardian_agent"].review_and_commit.call_args.kwargs
        assert call_kwargs["allow_commit"] is False
        assert result.terminal_state == "NEEDS_HUMAN_REVIEW"
        report_path = tmp_path / "review_report.md"
        assert "ポリシー違反" in report_path.read_text(encoding="utf-8")
```

- [ ] **Step 3: テストを実行し失敗を確認**

Run: `python -m pytest tests/core/test_review_phase_guardian_loop.py -v`
Expected: 新規2件が `AttributeError: 'dict' object has no attribute...` または `assert_called_once` の呼び出しゼロで FAIL（`review_and_commit`/`policy_agent.audit` がまだ呼ばれていないため）

- [ ] **Step 4: `_run_policy_gated_commit` を実装し `run_review_phase` から呼び出す**

`src/nexuscore/core/phase_runner_mixin.py` の `run_review_phase` 内、以下の既存コード:

```python
        if review_data.get("decision") == "APPROVE":
            context.terminal_state = "APPROVED"
            context.review = review_data
        else:
            context.terminal_state = "NEEDS_HUMAN_REVIEW"
            context.review = review_data
            self._write_review_report(
                context, feedback=review_data.get("feedback_for_coder", review_data.get("reason", ""))
            )

        self._maybe_run_constitutional_review(context)
        return context
```

を以下に置き換える:

```python
        if review_data.get("decision") == "APPROVE":
            review_data = self._run_policy_gated_commit(
                context, code_draft, test_code, test_result, constitution_str
            )

        if review_data.get("decision") == "APPROVE":
            context.terminal_state = "APPROVED"
            context.review = review_data
        else:
            context.terminal_state = "NEEDS_HUMAN_REVIEW"
            context.review = review_data
            self._write_review_report(
                context, feedback=review_data.get("feedback_for_coder", review_data.get("reason", ""))
            )

        self._maybe_run_constitutional_review(context)
        return context

    def _run_policy_gated_commit(
        self,
        context: OrchestratorContext,
        code_draft: str,
        test_code: str,
        test_result: str,
        constitution_str: str,
    ) -> dict[str, Any]:
        """guardian承認後、policy_agentの監査結果をallow_commitとしてreview_and_commitに渡す（spec §5）。

        policy_agent/review_and_commitが未提供の場合はガードなしで従来のAPPROVE結果をそのまま返す。
        """
        policy_agent = getattr(self, "policy_agent", None)
        guardian_agent = self.guardian_agent
        if (
            policy_agent is None
            or not hasattr(policy_agent, "audit")
            or not hasattr(guardian_agent, "review_and_commit")
        ):
            return {"decision": "APPROVE", "reason": "policy gate not configured"}

        files = context.implementation.get("files", {})
        files_to_check = [{"path": p, "content": c} for p, c in files.items()]
        try:
            audit_result = policy_agent.audit(files_to_check, project_path=self.project_path)
        except Exception as e:  # noqa: BLE001 — optional gate, fail-safe to no-commit
            self.logger.warning(f"[{context.task_id}] PolicyAgent audit failed (allow_commit=False): {e}")
            audit_result = {"result": "REJECTED", "violations": [str(e)]}

        allow_commit = audit_result.get("result") == "APPROVED"
        if not allow_commit:
            self.logger.info(
                f"[{context.task_id}] Commit blocked by policy audit: {audit_result.get('violations')}"
            )

        return guardian_agent.review_and_commit(
            code_draft, test_code, test_result, "", constitution_str, context.user_requirement,
            changed_files=list(files.keys()),
            allow_commit=allow_commit,
        )
```

- [ ] **Step 5: テストを実行し成功を確認**

Run: `python -m pytest tests/core/test_review_phase_guardian_loop.py -v`
Expected: 全PASS（既存6件＋新規2件＝8件）

- [ ] **Step 6: Commit**

```bash
git add src/nexuscore/core/phase_runner_mixin.py tests/core/test_review_phase_guardian_loop.py
git commit -m "feat: policy_agentをguardian承認後のcommitゲートとして実配線（review_and_commit・spec §5）"
```

---

### Task 4: debugger⇔中央FKB の接続を回帰テストで担保

**Files:**
- Test: `tests/core/test_knowledge_base_debugger_integration.py`（新規）

このタスクはコード変更なし。`DebuggerAgent._find_solution_from_kb` は既に `database.knowledge_base.knowledge_base.find_solution()` を参照する実装済みの機構であり、Task 2 で `knowledge_base.add_knowledge()` を接続したことで初めてエンドツーエンドの学習ループが成立する。ここではその接続を実データで検証する。

- [ ] **Step 1: 失敗するテストを書く**

`tests/core/test_knowledge_base_debugger_integration.py` を新規作成:

```python
"""中央FKB(database.knowledge_base)への永続化がDebuggerAgentの検索から
参照可能であることを検証する回帰テスト（Stage 3・spec §5「debuggerとの接続」）。

新規DBは作らない設計のため、DebuggerAgent側の `knowledge_base` シングルトンを
一時SQLiteに差し替えて検証する。
"""

from unittest.mock import patch

from database.knowledge_base import KnowledgeBase


def test_debugger_finds_solution_persisted_via_add_knowledge(tmp_path):
    db_path = tmp_path / "fkb_test.db"
    kb = KnowledgeBase(db_url=f"sqlite:///{db_path}")

    entry = {
        "error_signature": "ZeroDivisionError: division by zero",
        "cause": "ゼロ除算",
        "target": "source_file",
        "solution_pattern": {"type": "llm_diagnose_and_fix", "instruction": "guard against zero"},
        "description": "desc",
    }
    status = kb.add_knowledge(entry)
    assert status == "created"

    with patch("nexuscore.agents.debugger_agent.knowledge_base", kb):
        from nexuscore.agents.debugger_agent import DebuggerAgent

        debugger = DebuggerAgent()
        solution = debugger._find_solution_from_kb("Traceback...\nZeroDivisionError: division by zero")

    assert solution is not None
    assert solution["error_signature"] == "ZeroDivisionError: division by zero"
    assert solution["solution_pattern"]["instruction"] == "guard against zero"
```

- [ ] **Step 2: テストを実行し失敗しないことを確認（本タスクはコード変更なしのため既に成功する想定）**

Run: `python -m pytest tests/core/test_knowledge_base_debugger_integration.py -v`
Expected: PASS（1件）。もし `sqlalchemy` が未インストール等でFAILする場合は `requirements.txt` を確認しスキップ理由をコミットメッセージに明記する。

- [ ] **Step 3: Commit**

```bash
git add tests/core/test_knowledge_base_debugger_integration.py
git commit -m "test: 中央FKB永続化→DebuggerAgent検索の回帰テスト追加（既存機構への接続のみ・spec §5）"
```

---

### Task 5: 変更履歴・回帰ゲート・仕上げ

**Files:**
- Modify: `docs/変更履歴.md`

- [ ] **Step 1: 全テストスイートの回帰ゲートを実行**

Run: `python -m pytest tests/ -q 2>&1 | tail -30`
Expected: 既存4,800+件 + 本タスクで追加した6件が全PASS（failed 0）。失敗があれば原因を特定し該当タスクに戻って修正する。

- [ ] **Step 2: `docs/変更履歴.md` の `## [Unreleased]` → `### Added` セクションに追記**

`## [Unreleased]` の直後（`### Fixed` の前）に `### Added` セクションが無ければ新設し、以下を追記:

```markdown
### Added
- Stage 3 学習レイヤー実配線（`src/nexuscore/core/phase_runner_mixin.py`）: ①テスト失敗枯渇時に `postmortem_agent.analyze_failure_and_suggest_fkb_entry()` → `knowledge_curator_agent.validate_fkb_suggestion()` を実行し、サンドボックスで実際にテストが通ることを検証できた解のみ中央FKB（`database.knowledge_base.add_knowledge()`）へ永続化（汚染防止・spec §5）。分析結果は検証の成否に関わらず `context.postmortem_report` へ格納し、実装済みだが未発火だった `_maybe_run_constitutional_review()` を初めて起動 ②guardian APPROVE後に `policy_agent.audit()` の結果を `allow_commit` として `guardian_agent.review_and_commit()` に接続し、ポリシー違反時はコミットをブロック ③debugger⇔中央FKBの接続（`_find_solution_from_kb`）は既存実装のみで成立することを回帰テストで担保。spec: `docs/superpowers/specs/2026-07-17-twelve-agent-pipeline-design.md` §5。詳細: `01_DECISIONS/NexusCore/2026-07-21_Stage3学習レイヤー実装.md`
```

- [ ] **Step 3: Commit**

```bash
git add docs/変更履歴.md
git commit -m "docs: 変更履歴にStage3学習レイヤー実配線を追記"
```

- [ ] **Step 4: プッシュしてPR作成**

```bash
git push -u origin feat/stage3-learning-layer
gh pr create --title "feat: Stage 3 学習レイヤー実配線（postmortem/knowledge_curator/policy_agent）" --body "$(cat <<'EOF'
## Summary
- spec §5に基づき、テスト失敗枯渇時のFKB学習ループ（postmortem→knowledge_curator検証→中央FKB永続化）を実配線
- guardian承認後のpolicy_agentコミットゲート（review_and_commit・allow_commit）を実配線
- debugger⇔中央FKBの接続は既存実装のみで成立することを回帰テストで担保

## Test plan
- [x] tests/core/test_postmortem_learning_hook.py（新規3件）
- [x] tests/core/test_review_phase_guardian_loop.py（既存6件＋新規2件）
- [x] tests/core/test_knowledge_base_debugger_integration.py（新規1件）
- [x] 全体回帰: `python -m pytest tests/ -q`

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Spec カバレッジ確認（自己レビュー済み）

| spec §5 項目 | 対応タスク |
|---|---|
| postmortem: NEEDS_HUMAN_REVIEW/テスト失敗枯渇時に分析 | Task 2 |
| knowledge_curator: 検証済み解のみ記録・新規DB禁止 | Task 2（`database.knowledge_base.add_knowledge` を使用・新規テーブル追加なし） |
| debuggerとの接続: 次回実行時に `_find_solution_from_kb` が参照 | Task 4（既存実装・回帰テストのみ） |
| policy_agent: guardian承認後のcommit可否判定元 | Task 3 |
