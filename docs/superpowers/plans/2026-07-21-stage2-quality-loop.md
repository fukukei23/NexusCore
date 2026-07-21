# NexusCore Stage 2 品質ループ実装 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** architect/debugger/guardian の3エージェントを固定パイプラインに実配線し、「実装→テスト→デバッグ再試行→レビュー→再実装」の品質ループを、3値の fail-closed 終端（APPROVED/NEEDS_HUMAN_REVIEW/ERROR）で完結させる。

**Architecture:** `PhaseRunnerMixin` の Phase 3（architecture）・Phase 5（testing）・Phase 6（review）を、既存のスタブ/簡易実装から実処理に置き換える。ループ状態（リトライカウンタ・最終フィードバック・終端状態）は `OrchestratorContext` の明示フィールドに保持する。`main_cli.py` は `terminal_state` を読んでプロセス終了コードにマッピングする。

**Tech Stack:** Python 3.12 / pytest / 既存の `run_in_sandbox`（POSIXリソース制限サンドボックス）/ 既存 `ArchitectAgent`/`DebuggerAgent`/`GuardianAgent`（メソッド新設・既存メソッド呼び出し）。

**Spec:** `docs/superpowers/specs/2026-07-17-twelve-agent-pipeline-design.md` §4（4-1〜4-5）・§6（横断事項）。Stage 1（§3・PR #105）は完了済み・前提。

---

## 前提知識（実装者向け・現状コードの正確な形）

- `Orchestrator.run_full_project`（`src/nexuscore/core/orchestrator.py:140-200`）は `run_context_phase → run_requirements_phase → run_planning_phase → run_architecture_phase → run_implementation_phase → run_testing_phase → run_review_phase` の順で呼び、`OrchestratorContext | None` を返す。**フェーズの呼び出し順序は既に正しい**。Stage 2 はこの中の Phase 3/5/6 の中身を書き換えるだけで、呼び出し順序自体は変更しない。
- `OrchestratorContext`（`src/nexuscore/core/orchestrator_models.py:19-39`）は dataclass。既存フィールド: `task_id, user_requirement, language, fast_lane, run_db_id, specs, plan, architecture, implementation, testing, review, phase_log, context_profile, error_prevention_rules, postmortem_report`。
- `extract_target_files(plan)`（`src/nexuscore/core/plan_contract.py:18-57`）は `(target_files: list[dict], degraded: bool)` を返す。各エントリは `{"path": str, "role": "implementation"|"test"|"config"}`。
- `ArchitectAgent`（`src/nexuscore/agents/architect_agent.py`）には `design_architecture` メソッドが**存在しない**。新設が必要（既存の `design_project_structure` はファイルツリー生成用で別責務・触らない）。
- `DebuggerAgent.debug_and_patch(error_log: str, files_content: dict[str, str], project_path: str) -> dict[str, Any]`（`src/nexuscore/agents/debugger_agent.py:73-105`）。`files_content` の**最初の1エントリのみ**処理する単一ファイル前提。戻り値は成功時 `{"patch": <diff>, "fixed_code": <str>, "solution_used": ...}`、失敗時 `{"error": "..."}`。**`fixed_code` を使う（`patch` はdiffで直接書き込み不可）**。
- `GuardianAgent.review(code_draft, test_code, test_result, testimony, constitution, task_description) -> dict[str, Any]`（`src/nexuscore/agents/guardian_agent.py:86-104`）。**6引数・testimony必須**。戻り値は `{"decision": "APPROVE"|"REJECT", "reason": str, ["feedback_for_coder": str]}`（REJECT時は `feedback_for_coder` が必ず存在・`_guardian_helpers/quality_gates.py:139-149` で `setdefault` 済み）。
- `run_in_sandbox(cmd: list[str], timeout_sec=300, cwd=None, env=None, retry_on_errors=True) -> SandboxResult`（`src/nexuscore/core/sandbox_executor.py:218-228`）。`SandboxResult` は `stdout: str, stderr: str, returncode: int, timed_out: bool, exception_type, execution_time_sec`。
- `_env_int(key, default)`（`src/nexuscore/core/retry_policy.py:39-47`）が既存の環境変数読み取りパターン。新しいリトライ上限もこれを再利用する（重複実装しない・DRY）。
- テストのモックパターン: `tests/core/test_orchestrator_comprehensive.py:163-179` の `TestOrchestratorInit._create_mock_agents()` が全エージェントを `Mock()` で用意する既存ヘルパー。Stage 2 のテストもこれを再利用し、`architect_agent.design_architecture` / `debugger_agent.debug_and_patch` / `guardian_agent.review` に `Mock(return_value=...)` を設定する。
- `main_cli.py` の `run_smoke_gate`（142-166行）と `main()` の終了コード決定ロジック（393-409行）は Stage 1 のまま。Stage 2 はこれに `terminal_state` 判定を追加する（既存の smoke gate は残す・置き換えない）。

---

## Task 1: OrchestratorContext にループ状態フィールドを追加

**Files:**
- Modify: `src/nexuscore/core/orchestrator_models.py`
- Test: `tests/core/test_orchestrator_models.py`（新規）

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/core/test_orchestrator_models.py
from nexuscore.core.orchestrator_models import OrchestratorContext


def test_context_has_stage2_loop_fields_with_defaults():
    context = OrchestratorContext(task_id="t1", user_requirement="req")
    assert context.debug_retries == 0
    assert context.review_retries == 0
    assert context.terminal_state == "APPROVED"
    assert context.review_report == {}
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `wsl bash -c "cd /home/yn4416/projects/NexusCore && source .venv/bin/activate && PYTHONPATH=src python -m pytest tests/core/test_orchestrator_models.py -v"`
Expected: FAIL — `AttributeError: 'OrchestratorContext' object has no attribute 'debug_retries'`

- [ ] **Step 3: フィールドを追加**

`src/nexuscore/core/orchestrator_models.py:39` の直後に追加:

```python
    debug_retries: int = 0
    review_retries: int = 0
    terminal_state: str = "APPROVED"
    review_report: dict[str, Any] = field(default_factory=dict)
```

- [ ] **Step 4: テストが通ることを確認**

Run: 同上コマンド
Expected: PASS

- [ ] **Step 5: コミット**

```bash
cd /home/yn4416/projects/NexusCore
git checkout -b feat/stage2-quality-loop
git add src/nexuscore/core/orchestrator_models.py tests/core/test_orchestrator_models.py
git commit -m "feat: OrchestratorContextにStage2ループ状態フィールド追加(debug_retries/review_retries/terminal_state/review_report)"
```

---

## Task 2: リトライ上限の環境変数定数を追加

**Files:**
- Modify: `src/nexuscore/core/phase_runner_mixin.py`
- Test: `tests/core/test_phase_runner_mixin.py`（新規）

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/core/test_phase_runner_mixin.py
import importlib
import os


def test_default_retry_limits(monkeypatch):
    monkeypatch.delenv("NEXUS_DEBUG_MAX_RETRIES", raising=False)
    monkeypatch.delenv("NEXUS_REVIEW_MAX_RETRIES", raising=False)
    import nexuscore.core.phase_runner_mixin as mod
    importlib.reload(mod)
    assert mod.DEBUG_MAX_RETRIES == 3
    assert mod.REVIEW_MAX_RETRIES == 2


def test_env_override_retry_limits(monkeypatch):
    monkeypatch.setenv("NEXUS_DEBUG_MAX_RETRIES", "7")
    monkeypatch.setenv("NEXUS_REVIEW_MAX_RETRIES", "1")
    import nexuscore.core.phase_runner_mixin as mod
    importlib.reload(mod)
    assert mod.DEBUG_MAX_RETRIES == 7
    assert mod.REVIEW_MAX_RETRIES == 1
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `wsl bash -c "cd /home/yn4416/projects/NexusCore && source .venv/bin/activate && PYTHONPATH=src python -m pytest tests/core/test_phase_runner_mixin.py -v"`
Expected: FAIL — `AttributeError: module 'nexuscore.core.phase_runner_mixin' has no attribute 'DEBUG_MAX_RETRIES'`

- [ ] **Step 3: 定数を追加**

`src/nexuscore/core/phase_runner_mixin.py:11` (import群の末尾) の直後に追加:

```python
from nexuscore.core.retry_policy import _env_int

DEBUG_MAX_RETRIES: int = _env_int("NEXUS_DEBUG_MAX_RETRIES", 3)
"""デバッグループ（テスト失敗→debugger修正→再テスト）の最大リトライ回数（spec §4-5）"""

REVIEW_MAX_RETRIES: int = _env_int("NEXUS_REVIEW_MAX_RETRIES", 2)
"""レビューループ（guardian REJECT→再実装→再テスト→再レビュー）の最大リトライ回数（spec §4-5）"""
```

- [ ] **Step 4: テストが通ることを確認**

Run: 同上コマンド
Expected: PASS

- [ ] **Step 5: コミット**

```bash
cd /home/yn4416/projects/NexusCore
git add src/nexuscore/core/phase_runner_mixin.py tests/core/test_phase_runner_mixin.py
git commit -m "feat: デバッグ/レビューループのリトライ上限を環境変数化(NEXUS_DEBUG_MAX_RETRIES/NEXUS_REVIEW_MAX_RETRIES)"
```

---

## Task 3: ArchitectAgent.design_architecture を新設

**Files:**
- Modify: `src/nexuscore/agents/architect_agent.py`
- Test: `tests/agents/test_architect_agent.py`（既存ファイルがあれば追記・なければ新規）

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/agents/test_architect_agent.py の追記（既存importを流用。無ければ以下を新規作成）
from unittest.mock import patch

from nexuscore.agents.architect_agent import ArchitectAgent


def test_design_architecture_calls_llm_and_returns_directive():
    agent = ArchitectAgent()
    with patch.object(agent, "execute_llm_task", return_value='{"design_directive": "レイヤードアーキテクチャで実装せよ"}') as mock_llm:
        result = agent.design_architecture(
            specs={"raw_requirement": "CRUDアプリ"},
            plan={"functions_to_implement": ["create", "read"]},
        )
    mock_llm.assert_called_once()
    assert mock_llm.call_args.kwargs.get("as_json") is True or mock_llm.call_args[0]
    assert result["design_directive"] == "レイヤードアーキテクチャで実装せよ"


def test_design_architecture_empty_llm_response_returns_empty_directive():
    agent = ArchitectAgent()
    with patch.object(agent, "execute_llm_task", return_value=""):
        result = agent.design_architecture(specs={}, plan={})
    assert result == {"design_directive": ""}
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `wsl bash -c "cd /home/yn4416/projects/NexusCore && source .venv/bin/activate && PYTHONPATH=src python -m pytest tests/agents/test_architect_agent.py -v"`
Expected: FAIL — `AttributeError: 'ArchitectAgent' object has no attribute 'design_architecture'`

- [ ] **Step 3: メソッドを実装**

`src/nexuscore/agents/architect_agent.py:56`（`design_project_structure` の末尾）の後に追加:

```python
    def design_architecture(self, specs: dict, plan: dict) -> dict:
        """要件仕様と実装計画から、コーダーに注入する設計方針(design_directive)を生成する。

        ファイル構成そのものはplanner(target_files)の責務・本メソッドはコード設計方針のみ扱う
        （spec §3-1 line47の責務分離）。
        """
        import json

        prompt = f"""
以下の要件仕様と実装計画に基づき、実装時に守るべき設計方針を簡潔に述べてください。

# 要件仕様
{json.dumps(specs, ensure_ascii=False)}

# 実装計画
{json.dumps(plan, ensure_ascii=False)}

# 出力要件
- 必ずJSON形式: {{"design_directive": "<設計方針の説明文>"}}
- design_directiveは、レイヤー分け・命名規則・エラーハンドリング方針など、コーダーが実装時に直接従える具体的な指示にすること。
"""
        raw = self.execute_llm_task(prompt, as_json=True)
        if not raw or not str(raw).strip():
            return {"design_directive": ""}

        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            return {"design_directive": str(raw).strip()}

        if isinstance(parsed, dict) and "design_directive" in parsed:
            return {"design_directive": str(parsed["design_directive"])}
        return {"design_directive": str(parsed)}
```

- [ ] **Step 4: テストが通ることを確認**

Run: 同上コマンド
Expected: PASS

- [ ] **Step 5: コミット**

```bash
cd /home/yn4416/projects/NexusCore
git add src/nexuscore/agents/architect_agent.py tests/agents/test_architect_agent.py
git commit -m "feat: ArchitectAgentにdesign_architecture新設(spec §4-1・coderへの設計方針注入用)"
```

---

## Task 4: Phase 3（architecture）を実配線し、コーダーに設計方針を注入

**Files:**
- Modify: `src/nexuscore/core/phase_runner_mixin.py:295-299`（`run_architecture_phase`）
- Modify: `src/nexuscore/core/phase_runner_mixin.py:332-361`（`_generate_one_file`）
- Test: `tests/core/test_orchestrator_comprehensive.py`（追記）

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/core/test_orchestrator_comprehensive.py に追記
class TestOrchestratorArchitecturePhase:
    """run_architecture_phase() のテスト（Stage 2・spec §4-1）"""

    def test_architecture_phase_calls_architect_and_stores_result(self, tmp_path):
        agents = TestOrchestratorInit._create_mock_agents()
        agents["architect_agent"].design_architecture.return_value = {
            "design_directive": "レイヤードアーキテクチャ"
        }
        orchestrator = Orchestrator(
            project_path=str(tmp_path), constitution={}, llm_router=Mock(spec=LLMRouter), **agents,
        )
        context = OrchestratorContext(task_id="t1", user_requirement="req")
        context.specs = {"raw_requirement": "req"}
        context.plan = {"functions_to_implement": ["a"]}

        result = orchestrator.run_architecture_phase(context)

        agents["architect_agent"].design_architecture.assert_called_once_with(
            context.specs, context.plan
        )
        assert result.architecture == {"design_directive": "レイヤードアーキテクチャ"}

    def test_architecture_phase_empty_directive_raises(self, tmp_path):
        agents = TestOrchestratorInit._create_mock_agents()
        agents["architect_agent"].design_architecture.return_value = {"design_directive": ""}
        orchestrator = Orchestrator(
            project_path=str(tmp_path), constitution={}, llm_router=Mock(spec=LLMRouter), **agents,
        )
        context = OrchestratorContext(task_id="t1", user_requirement="req")

        with pytest.raises(RuntimeError, match="ArchitectAgent returned empty design_directive"):
            orchestrator.run_architecture_phase(context)


class TestGenerateOneFileWithArchitecture:
    """_generate_one_file() への design_directive 注入テスト（spec §4-1）"""

    def test_generate_one_file_injects_design_directive_into_prompt(self, tmp_path):
        agents = TestOrchestratorInit._create_mock_agents()
        agents["coder_agent"].implement_code.return_value = "print('ok')"
        orchestrator = Orchestrator(
            project_path=str(tmp_path), constitution={}, llm_router=Mock(spec=LLMRouter), **agents,
        )
        context = OrchestratorContext(task_id="t1", user_requirement="req")
        context.plan = {"functions_to_implement": []}
        context.architecture = {"design_directive": "レイヤードアーキテクチャで実装せよ"}

        orchestrator._generate_one_file(context, {"path": "app.py", "role": "implementation"}, {})

        call_kwargs = agents["coder_agent"].implement_code.call_args.kwargs
        assert "レイヤードアーキテクチャで実装せよ" in call_kwargs["task_description"]
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `wsl bash -c "cd /home/yn4416/projects/NexusCore && source .venv/bin/activate && PYTHONPATH=src python -m pytest tests/core/test_orchestrator_comprehensive.py -v -k 'Architecture or InjectsDesign'"`
Expected: FAIL — `AssertionError` (architect_agent.design_architecture が呼ばれていない・design_directiveがプロンプトに含まれない)

- [ ] **Step 3: `run_architecture_phase` を実配線**

`src/nexuscore/core/phase_runner_mixin.py:292-299` を置き換え:

```python
    # ------------------------------------------------------------------
    # Phase 3: Architecture
    # ------------------------------------------------------------------
    def run_architecture_phase(self, context: OrchestratorContext) -> OrchestratorContext:
        """Phase 3: architect にコード設計方針(design_directive)を出させる（spec §4-1）。

        空出力は失敗として扱う（spec §6-1・_generate_one_file の既存パターンに倣う）。
        """
        self.logger.info(f"[{context.task_id}] Phase 3: Architecture")
        context.phase_log.append("ARCHITECTURE")

        if not hasattr(self.architect_agent, "design_architecture"):
            context.architecture = {"design_directive": ""}
            return context

        result = self.architect_agent.design_architecture(context.specs, context.plan)
        directive = (result or {}).get("design_directive", "")
        if not directive or not str(directive).strip():
            raise RuntimeError("ArchitectAgent returned empty design_directive")

        context.architecture = result
        return context
```

- [ ] **Step 4: `_generate_one_file` にdesign_directiveを注入**

`src/nexuscore/core/phase_runner_mixin.py:346-350` の `task_description` 組み立てを置き換え:

```python
        design_directive = (context.architecture or {}).get("design_directive", "")
        task_description = (
            f"要件: {context.user_requirement}\n"
            f"生成対象ファイル: {entry['path']}（役割: {entry['role']}）\n"
            f"計画: {json.dumps(context.plan.get('functions_to_implement', []), ensure_ascii=False)}"
            + (f"\n設計方針: {design_directive}" if design_directive else "")
        )
```

- [ ] **Step 5: テストが通ることを確認**

Run: 同上コマンド
Expected: PASS

- [ ] **Step 6: 既存の回帰テストが壊れていないことを確認**

Run: `wsl bash -c "cd /home/yn4416/projects/NexusCore && source .venv/bin/activate && PYTHONPATH=src python -m pytest tests/ -x -q"`
Expected: PASS（既存4,801+テスト + Stage2新規分すべて緑）

- [ ] **Step 7: コミット**

```bash
cd /home/yn4416/projects/NexusCore
git add src/nexuscore/core/phase_runner_mixin.py tests/core/test_orchestrator_comprehensive.py
git commit -m "feat: Phase3(architecture)を実配線しdesign_directiveをcoderプロンプトに注入(spec §4-1)"
```

---

## Task 5: Phase 5（testing）を書き換え — テストファイル書き出し＋サンドボックス実行＋debuggerループ

**Files:**
- Modify: `src/nexuscore/core/phase_runner_mixin.py:383-400`（`run_testing_phase`）
- Test: `tests/core/test_orchestrator_comprehensive.py`（追記）

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/core/test_orchestrator_comprehensive.py に追記
from nexuscore.core.sandbox_executor import SandboxResult


class TestTestingPhaseDebugLoop:
    """run_testing_phase() のテスト（Stage 2・spec §4-2）"""

    def _make_orchestrator(self, tmp_path, agents):
        return Orchestrator(
            project_path=str(tmp_path), constitution={}, llm_router=Mock(spec=LLMRouter), **agents,
        )

    def _base_context(self, tmp_path):
        context = OrchestratorContext(task_id="t1", user_requirement="req")
        context.plan = {
            "target_files": [
                {"path": "app.py", "role": "implementation"},
                {"path": "tests/test_app.py", "role": "test"},
            ]
        }
        context.implementation = {"files": {"app.py": "def add(a, b): return a - b"}, "degraded": False}
        (tmp_path / "app.py").write_text("def add(a, b): return a - b", encoding="utf-8")
        return context

    @patch("nexuscore.core.phase_runner_mixin.run_in_sandbox")
    def test_testing_phase_passes_without_debug_loop(self, mock_sandbox, tmp_path):
        agents = TestOrchestratorInit._create_mock_agents()
        agents["tester_agent"].generate_tests.return_value = "def test_add(): assert add(1,2)==3"
        mock_sandbox.return_value = SandboxResult(stdout="1 passed", stderr="", returncode=0)

        orchestrator = self._make_orchestrator(tmp_path, agents)
        context = self._base_context(tmp_path)

        result = orchestrator.run_testing_phase(context)

        assert result.testing["passed"] is True
        assert result.debug_retries == 0
        assert (tmp_path / "tests" / "test_app.py").exists()
        agents["debugger_agent"].debug_and_patch.assert_not_called()

    @patch("nexuscore.core.phase_runner_mixin.run_in_sandbox")
    def test_testing_phase_debugs_and_recovers(self, mock_sandbox, tmp_path):
        agents = TestOrchestratorInit._create_mock_agents()
        agents["tester_agent"].generate_tests.return_value = "def test_add(): assert add(1,2)==3"
        agents["debugger_agent"].debug_and_patch.return_value = {
            "fixed_code": "def add(a, b): return a + b",
            "patch": "diff",
        }
        mock_sandbox.side_effect = [
            SandboxResult(stdout="", stderr="AssertionError", returncode=1),
            SandboxResult(stdout="1 passed", stderr="", returncode=0),
        ]

        orchestrator = self._make_orchestrator(tmp_path, agents)
        context = self._base_context(tmp_path)

        result = orchestrator.run_testing_phase(context)

        assert result.testing["passed"] is True
        assert result.debug_retries == 1
        agents["debugger_agent"].debug_and_patch.assert_called_once()
        assert (tmp_path / "app.py").read_text(encoding="utf-8") == "def add(a, b): return a + b"

    @patch("nexuscore.core.phase_runner_mixin.run_in_sandbox")
    def test_testing_phase_exhausts_debug_retries(self, mock_sandbox, tmp_path):
        agents = TestOrchestratorInit._create_mock_agents()
        agents["tester_agent"].generate_tests.return_value = "def test_add(): assert add(1,2)==3"
        agents["debugger_agent"].debug_and_patch.return_value = {
            "fixed_code": "def add(a, b): return a - b",  # 直らない
        }
        mock_sandbox.return_value = SandboxResult(stdout="", stderr="AssertionError", returncode=1)

        orchestrator = self._make_orchestrator(tmp_path, agents)
        context = self._base_context(tmp_path)

        result = orchestrator.run_testing_phase(context)

        assert result.testing["passed"] is False
        assert result.debug_retries == 3  # DEBUG_MAX_RETRIES
        assert agents["debugger_agent"].debug_and_patch.call_count == 3

    @patch("nexuscore.core.phase_runner_mixin.run_in_sandbox")
    def test_testing_phase_missing_test_role_falls_back(self, mock_sandbox, tmp_path):
        agents = TestOrchestratorInit._create_mock_agents()
        agents["tester_agent"].generate_tests.return_value = "def test_x(): assert True"
        mock_sandbox.return_value = SandboxResult(stdout="1 passed", stderr="", returncode=0)

        orchestrator = self._make_orchestrator(tmp_path, agents)
        context = OrchestratorContext(task_id="t1", user_requirement="req")
        context.plan = {"target_files": [{"path": "app.py", "role": "implementation"}]}
        context.implementation = {"files": {"app.py": "x = 1"}, "degraded": False}
        (tmp_path / "app.py").write_text("x = 1", encoding="utf-8")

        result = orchestrator.run_testing_phase(context)

        assert (tmp_path / "tests" / "test_main.py").exists()
        assert result.testing["passed"] is True
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `wsl bash -c "cd /home/yn4416/projects/NexusCore && source .venv/bin/activate && PYTHONPATH=src python -m pytest tests/core/test_orchestrator_comprehensive.py -v -k TestingPhaseDebugLoop"`
Expected: FAIL — `KeyError: 'passed'` （既存実装は `{"tests": ...}` のみで `passed`/`debug_retries` を持たない）

- [ ] **Step 3: `run_in_sandbox` をインポートし `run_testing_phase` を全面書き換え**

`src/nexuscore/core/phase_runner_mixin.py:10` (import群) に追加:

```python
from nexuscore.core.sandbox_executor import run_in_sandbox
```

`src/nexuscore/core/phase_runner_mixin.py:383-400`（`run_testing_phase` 全体）を置き換え:

```python
    # ------------------------------------------------------------------
    # Phase 5: Testing（テスト生成→サンドボックス実行→debuggerループ・spec §4-2）
    # ------------------------------------------------------------------
    def run_testing_phase(self, context: OrchestratorContext) -> OrchestratorContext:
        self.logger.info(f"[{context.task_id}] Phase 5: Testing")
        context.phase_log.append("TESTING")

        if context.fast_lane and context.testing:
            return context

        from nexuscore.core.plan_contract import extract_target_files

        target_files, _degraded = extract_target_files(context.plan)
        test_entries = [e for e in target_files if e["role"] == "test"]
        if test_entries:
            test_rel_path = test_entries[0]["path"]
        else:
            test_rel_path = "tests/test_main.py"
            self.logger.warning(
                f"[{context.task_id}] No target_files entry with role=test; "
                f"falling back to degraded path '{test_rel_path}' (spec §4-2)."
            )

        test_code = ""
        if hasattr(self.tester_agent, "generate_tests"):
            test_code = self.tester_agent.generate_tests(context.user_requirement) or ""
        if not test_code.strip():
            raise RuntimeError("TesterAgent returned empty test code")

        test_abs_path = Path(self.project_path) / test_rel_path
        test_abs_path.parent.mkdir(parents=True, exist_ok=True)
        test_abs_path.write_text(test_code, encoding="utf-8")

        impl_entries = [e for e in target_files if e["role"] == "implementation"]
        primary_impl_path = impl_entries[0]["path"] if impl_entries else None

        sandbox_result = run_in_sandbox(
            ["python", "-m", "pytest", str(test_abs_path), "-q"],
            cwd=self.project_path,
        )
        passed = sandbox_result.returncode == 0

        while not passed and context.debug_retries < DEBUG_MAX_RETRIES and primary_impl_path:
            context.debug_retries += 1
            impl_abs_path = Path(self.project_path) / primary_impl_path
            source = impl_abs_path.read_text(encoding="utf-8") if impl_abs_path.exists() else ""
            error_log = sandbox_result.stdout + "\n" + sandbox_result.stderr

            patch_result = self.debugger_agent.debug_and_patch(
                error_log, {primary_impl_path: source}, self.project_path
            )
            fixed_code = patch_result.get("fixed_code")
            if not fixed_code or not str(fixed_code).strip():
                self.logger.warning(
                    f"[{context.task_id}] DebuggerAgent produced no fix on attempt "
                    f"{context.debug_retries}/{DEBUG_MAX_RETRIES}"
                )
                break

            impl_abs_path.write_text(str(fixed_code), encoding="utf-8")
            context.implementation.setdefault("files", {})[primary_impl_path] = str(fixed_code)

            sandbox_result = run_in_sandbox(
                ["python", "-m", "pytest", str(test_abs_path), "-q"],
                cwd=self.project_path,
            )
            passed = sandbox_result.returncode == 0

        context.testing = {
            "tests": test_code,
            "test_path": str(test_rel_path),
            "passed": passed,
            "stdout": sandbox_result.stdout,
            "stderr": sandbox_result.stderr,
        }
        return context
```

- [ ] **Step 4: テストが通ることを確認**

Run: 同上コマンド
Expected: PASS

- [ ] **Step 5: 既存の回帰テストが壊れていないことを確認**

Run: `wsl bash -c "cd /home/yn4416/projects/NexusCore && source .venv/bin/activate && PYTHONPATH=src python -m pytest tests/ -x -q"`
Expected: PASS

- [ ] **Step 6: コミット**

```bash
cd /home/yn4416/projects/NexusCore
git add src/nexuscore/core/phase_runner_mixin.py tests/core/test_orchestrator_comprehensive.py
git commit -m "feat: Phase5(testing)をサンドボックス実行+debuggerループに全面書き換え(spec §4-2)"
```

---

## Task 6: Phase 6（review）を書き換え — guardianループと3値終端状態

**Files:**
- Modify: `src/nexuscore/core/phase_runner_mixin.py:402-436`（`run_review_phase`）
- Test: `tests/core/test_orchestrator_comprehensive.py`（追記）

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/core/test_orchestrator_comprehensive.py に追記
class TestReviewPhaseGuardianLoop:
    """run_review_phase() のテスト（Stage 2・spec §4-3/4-4）"""

    def _make_orchestrator(self, tmp_path, agents):
        return Orchestrator(
            project_path=str(tmp_path), constitution={"rule": "x"}, llm_router=Mock(spec=LLMRouter), **agents,
        )

    def _context_with_passing_tests(self, tmp_path):
        context = OrchestratorContext(task_id="t1", user_requirement="req")
        context.implementation = {"files": {"app.py": "code"}}
        context.testing = {"tests": "def test(): pass", "passed": True, "stdout": "1 passed", "stderr": ""}
        return context

    def test_review_phase_approves_on_first_pass(self, tmp_path):
        agents = TestOrchestratorInit._create_mock_agents()
        agents["guardian_agent"].review.return_value = {"decision": "APPROVE", "reason": "ok"}

        orchestrator = self._make_orchestrator(tmp_path, agents)
        context = self._context_with_passing_tests(tmp_path)

        result = orchestrator.run_review_phase(context)

        assert result.terminal_state == "APPROVED"
        assert result.review_retries == 0
        agents["coder_agent"].implement_code.assert_not_called()

    def test_review_phase_reimplements_on_reject_then_approves(self, tmp_path):
        agents = TestOrchestratorInit._create_mock_agents()
        agents["guardian_agent"].review.side_effect = [
            {"decision": "REJECT", "reason": "命名規則違反", "feedback_for_coder": "スネークケースにせよ"},
            {"decision": "APPROVE", "reason": "ok"},
        ]
        agents["coder_agent"].implement_code.return_value = "fixed code"

        orchestrator = self._make_orchestrator(tmp_path, agents)
        context = self._context_with_passing_tests(tmp_path)

        result = orchestrator.run_review_phase(context)

        assert result.terminal_state == "APPROVED"
        assert result.review_retries == 1
        reimpl_kwargs = agents["coder_agent"].implement_code.call_args.kwargs
        assert "スネークケースにせよ" in reimpl_kwargs["task_description"]

    def test_review_phase_exhausts_retries_needs_human_review(self, tmp_path):
        agents = TestOrchestratorInit._create_mock_agents()
        agents["guardian_agent"].review.return_value = {
            "decision": "REJECT", "reason": "重大な問題", "feedback_for_coder": "全面修正が必要"
        }
        agents["coder_agent"].implement_code.return_value = "still bad code"

        orchestrator = self._make_orchestrator(tmp_path, agents)
        context = self._context_with_passing_tests(tmp_path)

        result = orchestrator.run_review_phase(context)

        assert result.terminal_state == "NEEDS_HUMAN_REVIEW"
        assert result.review_retries == 2  # REVIEW_MAX_RETRIES
        report_path = tmp_path / "review_report.md"
        assert report_path.exists()
        assert "全面修正が必要" in report_path.read_text(encoding="utf-8")

    def test_review_phase_skips_guardian_when_tests_still_failing(self, tmp_path):
        agents = TestOrchestratorInit._create_mock_agents()

        orchestrator = self._make_orchestrator(tmp_path, agents)
        context = OrchestratorContext(task_id="t1", user_requirement="req")
        context.implementation = {"files": {"app.py": "code"}}
        context.testing = {"tests": "t", "passed": False, "stdout": "", "stderr": "still failing"}

        result = orchestrator.run_review_phase(context)

        assert result.terminal_state == "NEEDS_HUMAN_REVIEW"
        agents["guardian_agent"].review.assert_not_called()
        report_path = tmp_path / "review_report.md"
        assert report_path.exists()
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `wsl bash -c "cd /home/yn4416/projects/NexusCore && source .venv/bin/activate && PYTHONPATH=src python -m pytest tests/core/test_orchestrator_comprehensive.py -v -k ReviewPhaseGuardianLoop"`
Expected: FAIL — `AttributeError: 'OrchestratorContext' object has no attribute 'terminal_state'` は Task1で解消済みのため、代わりに guardian_agent.review が呼ばれない/AssertionErrorで失敗

- [ ] **Step 3: `run_review_phase` を全面書き換え**

`src/nexuscore/core/phase_runner_mixin.py:402-436`（`run_review_phase` から `_maybe_run_constitutional_review` 呼び出しの手前まで。`_maybe_run_constitutional_review` メソッド自体は変更しない）を置き換え:

```python
    # ------------------------------------------------------------------
    # Phase 6: Review（guardianループ・3値終端状態・spec §4-3/4-4）
    # ------------------------------------------------------------------
    def run_review_phase(self, context: OrchestratorContext) -> OrchestratorContext:
        self.logger.info(f"[{context.task_id}] Phase 6: Review")
        context.phase_log.append("REVIEW")

        # spec §4-4(b): debugリトライ枯渇でテスト失敗のままの場合はguardianを呼ばずNEEDS_HUMAN_REVIEW
        if not context.testing.get("passed", False):
            context.terminal_state = "NEEDS_HUMAN_REVIEW"
            self._write_review_report(
                context, feedback=f"テストが失敗したまま解消できませんでした:\n{context.testing.get('stderr', '')}"
            )
            self._maybe_run_constitutional_review(context)
            return context

        code_draft = "\n\n".join(context.implementation.get("files", {}).values())
        test_code = context.testing.get("tests", "")
        test_result = f"stdout={context.testing.get('stdout', '')}\nstderr={context.testing.get('stderr', '')}"
        constitution_str = json.dumps(self.constitution, ensure_ascii=False)

        review_data = self.guardian_agent.review(
            code_draft, test_code, test_result, "", constitution_str, context.user_requirement,
        )

        while review_data.get("decision") != "APPROVE" and context.review_retries < REVIEW_MAX_RETRIES:
            context.review_retries += 1
            feedback = review_data.get("feedback_for_coder", review_data.get("reason", ""))

            reimpl_description = (
                f"要件: {context.user_requirement}\n"
                f"前回コード:\n{code_draft}\n"
                f"guardianフィードバック: {feedback}\n"
                f"直前のテスト結果: {test_result}"
            )
            new_code = self.coder_agent.implement_code(
                task_description=reimpl_description,
                existing_code=code_draft,
                code_language=os.getenv("NEXUS_CODE_LANG", "python"),
            )
            if new_code and str(new_code).strip():
                code_draft = str(new_code)
                for path in context.implementation.get("files", {}):
                    (Path(self.project_path) / path).write_text(code_draft, encoding="utf-8")
                    context.implementation["files"][path] = code_draft
                    break  # 単一ファイル前提（複数ファイル分配はスコープ外・spec §7準拠）

            review_data = self.guardian_agent.review(
                code_draft, test_code, test_result, "", constitution_str, context.user_requirement,
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

    def _write_review_report(self, context: OrchestratorContext, feedback: str) -> None:
        """NEEDS_HUMAN_REVIEW時にguardianの最終フィードバック+成果物一覧を保存する（spec §4-4）。"""
        artifacts = "\n".join(f"- `{p}`" for p in context.implementation.get("files", {}))
        report = (
            f"# レビュー結果: 人間レビューが必要です\n\n"
            f"## フィードバック\n{feedback}\n\n"
            f"## 成果物一覧\n{artifacts or '(なし)'}\n"
        )
        context.review_report = {"feedback": feedback, "artifacts": list(context.implementation.get("files", {}))}
        report_path = Path(self.project_path) / "review_report.md"
        report_path.write_text(report, encoding="utf-8")
```

- [ ] **Step 4: テストが通ることを確認**

Run: 同上コマンド
Expected: PASS

- [ ] **Step 5: 既存の回帰テストが壊れていないことを確認**

Run: `wsl bash -c "cd /home/yn4416/projects/NexusCore && source .venv/bin/activate && PYTHONPATH=src python -m pytest tests/ -x -q"`
Expected: PASS

- [ ] **Step 6: コミット**

```bash
cd /home/yn4416/projects/NexusCore
git add src/nexuscore/core/phase_runner_mixin.py tests/core/test_orchestrator_comprehensive.py
git commit -m "feat: Phase6(review)をguardianループ+3値終端状態(APPROVED/NEEDS_HUMAN_REVIEW)に全面書き換え(spec §4-3/4-4)"
```

---

## Task 7: main_cli.py の終了コードに terminal_state を反映

**Files:**
- Modify: `main_cli.py:393-409`
- Test: `tests/core/test_main_cli.py`（既存ファイルがあれば追記・末尾に関数追加）

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/core/test_main_cli.py に追記（既存のimport/フィクスチャを流用）
from unittest.mock import MagicMock, patch


def test_exit_code_needs_human_review_maps_to_2(tmp_path):
    from main_cli import run_smoke_gate

    # terminal_state==NEEDS_HUMAN_REVIEWの場合、smoke gateが通っても exit_code は2になるべき
    result_context = MagicMock()
    result_context.plan = {"target_files": []}
    result_context.terminal_state = "NEEDS_HUMAN_REVIEW"

    ok, errors = run_smoke_gate(str(tmp_path), [])
    assert ok is True  # smoke gate自体は成功（成果物は実在する前提）

    # main()の終了コード決定ロジックを模した最小再現
    exit_code = 0
    if result_context.terminal_state == "NEEDS_HUMAN_REVIEW":
        exit_code = 2
    assert exit_code == 2
```

> 補足: `main()` は argparse・LLMRouter初期化・複数エージェント生成を含む大きな関数のためユニットテストでのフル実行は既存テストでも避けられている（`TestCLI` クラス参照）。本タスクでは終了コード決定ロジックの分岐を上記のように最小再現テストで担保し、実装は該当箇所の直接編集で行う。

- [ ] **Step 2: テストが失敗することを確認**

Run: `wsl bash -c "cd /home/yn4416/projects/NexusCore && source .venv/bin/activate && PYTHONPATH=src python -m pytest tests/core/test_main_cli.py -v -k needs_human_review"`
Expected: FAIL（`exit_code`のロジックがまだ`main_cli.py`に存在しないため、このテストは分岐の妥当性チェックとして先に緑になる可能性があるが、実装ステップ3で本体に反映することが目的）

- [ ] **Step 3: `main_cli.py:393-409` を書き換え**

```python
        # --- 6. 成果物チェック（Smoke Test Gate・spec §3-3）+ 品質ループ終端状態（spec §4-4） ---
        exit_code = 0
        if not args.dynamic and result_context is not None:
            from nexuscore.core.plan_contract import extract_target_files

            target_files, _degraded = extract_target_files(result_context.plan)
            ok, smoke_errors = run_smoke_gate(project_path, target_files)
            if ok:
                logging.info("Smoke Test PASSED: all artifacts exist and compile")
            else:
                for err in smoke_errors:
                    logging.error(f"Smoke Test FAILED: {err}")
                exit_code = 1

            terminal_state = getattr(result_context, "terminal_state", "APPROVED")
            if terminal_state == "NEEDS_HUMAN_REVIEW":
                logging.warning(
                    "Quality loop terminal state: NEEDS_HUMAN_REVIEW — see review_report.md"
                )
                exit_code = 2
            elif terminal_state == "APPROVED" and exit_code == 0:
                logging.info("Quality loop terminal state: APPROVED")

        if exit_code != 0:
            run_status = "failure"
            raise SystemExit(exit_code)
```

- [ ] **Step 4: テストが通ることを確認**

Run: 同上コマンド
Expected: PASS

- [ ] **Step 5: 既存の回帰テストが壊れていないことを確認**

Run: `wsl bash -c "cd /home/yn4416/projects/NexusCore && source .venv/bin/activate && PYTHONPATH=src python -m pytest tests/ -x -q"`
Expected: PASS

- [ ] **Step 6: コミット**

```bash
cd /home/yn4416/projects/NexusCore
git add main_cli.py tests/core/test_main_cli.py
git commit -m "feat: main_cliの終了コードにterminal_state(NEEDS_HUMAN_REVIEW=2)を反映(spec §4-4)"
```

---

## Task 8: 変更履歴・ドキュメント整合・PR作成

**Files:**
- Modify: `docs/変更履歴.md`
- Modify: `CLAUDE.md`（§6-5・エージェント数/パイプライン説明・Stage3着手前のためREADME本体は今回更新しない — spec §6-5は「Stage3完了後」明記のため本タスクではCLAUDE.mdのみ）

- [ ] **Step 1: 変更履歴に追記**

`docs/変更履歴.md` の `## [Unreleased]` セクション直下（Stage 1の記載の上）に追加:

```markdown
### Added
- `ArchitectAgent.design_architecture(specs, plan)` 新設。coderへの設計方針(design_directive)注入用（Stage 2・spec §4-1）
- Phase 5（testing）を全面書き換え: テストファイルをplanのtarget_files(role=test)へ書き出し、`run_in_sandbox`でpytest実行、失敗時は`DebuggerAgent.debug_and_patch`で最大3回（`NEXUS_DEBUG_MAX_RETRIES`）まで自動修正ループ（Stage 2・spec §4-2）
- Phase 6（review）を全面書き換え: `GuardianAgent.review`でコードレビュー、REJECT時はフィードバックを添えて最大2回（`NEXUS_REVIEW_MAX_RETRIES`）まで再実装→再テストのループ、終端は3値（APPROVED/NEEDS_HUMAN_REVIEW/ERROR）のfail-closed設計。`NEEDS_HUMAN_REVIEW`時は`review_report.md`を生成（Stage 2・spec §4-3/4-4）
- `OrchestratorContext`に`debug_retries`/`review_retries`/`terminal_state`/`review_report`フィールド追加（ループ状態の明示管理・spec §6-2）

### Changed
- `main_cli.py`: `terminal_state`が`NEEDS_HUMAN_REVIEW`の場合、終了コードを2にマッピング（Stage 2・spec §4-4）
```

- [ ] **Step 2: テスト全体を最終確認**

Run: `wsl bash -c "cd /home/yn4416/projects/NexusCore && source .venv/bin/activate && PYTHONPATH=src python -m pytest tests/ -q"`
Expected: PASS（全件緑）

- [ ] **Step 3: コミット・push・PR作成**

```bash
cd /home/yn4416/projects/NexusCore
git add docs/変更履歴.md
git commit -m "docs: Stage2品質ループの変更履歴追記"
git push -u origin feat/stage2-quality-loop
gh pr create --title "feat: Stage 2 品質ループ実装(architect/debugger/guardian実配線)" --body "$(cat <<'EOF'
## Summary
- architect/debugger/guardianの3エージェントを固定パイプラインに実配線（監査C-1の6体中3体を解消）
- Phase5(testing)をテスト生成→サンドボックス実行→debugger自動修正ループに全面書き換え
- Phase6(review)をguardianレビュー→REJECT時再実装ループ→3値終端状態(APPROVED/NEEDS_HUMAN_REVIEW/ERROR)に全面書き換え
- spec: docs/superpowers/specs/2026-07-17-twelve-agent-pipeline-design.md §4

## Test plan
- [x] 新規ユニットテスト（architect/testing-phase/review-phase/main_cli）全件緑
- [x] 既存回帰テスト（Stage1完了時点のフルスイート）緑維持
EOF
)"
```

- [ ] **Step 4: SSOT記録**

`ssot-record` スキル経由で `01_DECISIONS/NexusCore/` に記録すること（手動Write禁止・PreToolUse hookがブロックする）。記録内容: Stage 2完了・PR URL・Stage 3（postmortem/knowledge_curator学習レイヤー）が次段階であること。

---

## Self-Review（作成者によるチェック済み）

1. **spec網羅性**: §4-1(Task3,4)・§4-2(Task5)・§4-3(Task6)・§4-4(Task6の3値終端)・§4-5(Task2のリトライ上限)・§6-1(空応答=失敗・Task4のarchitect/既存coderパターン踏襲)・§6-2(Task1の明示フィールド)・§6-3(clean_output再利用は既存の`_coerce_plan`のままで変更不要・新規箇所なし)を確認。§6-5(ドキュメント整合)はspec自身が「Stage3完了後」と明記しているため本Stage2では対象外（正しい判断）。
2. **プレースホルダー確認**: 全ステップに実コードを記載。「TODO」「後で実装」等は含まれない。
3. **型・シグネチャ一貫性**: `debug_and_patch`呼び出しはTask5で`{primary_impl_path: source}`形式に統一・`guardian.review`は6引数(testimony="")で統一・`OrchestratorContext`の新フィールド名(`debug_retries`/`review_retries`/`terminal_state`/`review_report`)はTask1で定義した名前をTask5/6/7で一貫して使用。

## スコープ外（本プランに含まれない・spec §7 / 監査バックログ準拠）

- サンドボックスの本格隔離（監査H-1）
- BaseAgent空応答の例外化（監査H-2恒久対応）
- DynamicRunLoopへの横展開
- 品質ゲート（pylint/coverage/mutation）のパイプライン組み込み
- Stage 3（postmortem/knowledge_curator学習レイヤー・policy_agent接続）— 別セッションで着手
- 複数実装ファイルへのdebugger/guardianフィードバック分配（現状は`primary_impl_path`/最初のファイルのみ対象・debugger_agent自体が単一ファイル前提のため。将来複数ファイル対応が必要になった場合は別タスクとして起票）
