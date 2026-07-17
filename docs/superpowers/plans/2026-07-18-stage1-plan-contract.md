# Stage 1: 土台修正（plan契約化・hello.py廃止）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 固定パイプラインの実装フェーズを「hello.py固定」から「planner が出す target_files 契約に基づく複数ファイル生成」に置き換える（spec §3・監査C-2解消）。

**Architecture:** 新モジュール `plan_contract.py` に target_files の検証・フォールバックを純粋関数として切り出し、`PhaseRunnerMixin.run_implementation_phase` と `main_cli.py` の Smoke Test をそれに接続する。coder は依存順に1ファイルずつ呼び、生成済みファイルを `existing_code` で伝搬する。

**Tech Stack:** Python 3.12 / pytest 7.4.4（`-n auto` 並列可）/ 既存 BaseAgent・LLMRouter はモックで遮断

**前提:**
- spec: `docs/superpowers/specs/2026-07-17-twelve-agent-pipeline-design.md`（承認済み）
- 実行環境: WSL (`~/projects/NexusCore`)。`source .venv/bin/activate && export PYTHONPATH=src`
- 回帰ゲート: 既存テスト 4801 passed を維持（`python -m pytest tests/ -n auto -q`）

---

### Task 1: plan_contract モジュール（target_files 検証・フォールバック）

**Files:**
- Create: `src/nexuscore/core/plan_contract.py`
- Test: `tests/core/test_plan_contract.py`（`tests/core/` が無ければ `__init__.py` 不要・pytest はディレクトリ自動収集）

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/core/test_plan_contract.py
"""plan_contract（target_files 契約）のユニットテスト。spec §3-1"""
from __future__ import annotations

import logging

from nexuscore.core.plan_contract import extract_target_files


class TestExtractTargetFiles:
    def test_valid_plan_returns_entries_and_not_degraded(self):
        plan = {
            "target_files": [
                {"path": "app/calc.py", "role": "implementation"},
                {"path": "tests/test_calc.py", "role": "test"},
                {"path": "config.toml", "role": "config"},
            ]
        }
        files, degraded = extract_target_files(plan)
        assert degraded is False
        assert files == plan["target_files"]

    def test_missing_target_files_falls_back_to_main_py(self, caplog):
        with caplog.at_level(logging.WARNING):
            files, degraded = extract_target_files({"functions_to_implement": []})
        assert degraded is True
        assert files == [{"path": "main.py", "role": "implementation"}]
        assert "劣化モード" in caplog.text

    def test_none_plan_falls_back(self):
        files, degraded = extract_target_files(None)
        assert degraded is True
        assert files[0]["path"] == "main.py"

    def test_invalid_role_entries_are_dropped(self):
        plan = {
            "target_files": [
                {"path": "app/a.py", "role": "implementation"},
                {"path": "app/b.py", "role": "banana"},
                {"path": "app/c.py"},
                "not-a-dict",
            ]
        }
        files, degraded = extract_target_files(plan)
        assert degraded is False
        assert files == [{"path": "app/a.py", "role": "implementation"}]

    def test_no_implementation_role_falls_back(self):
        plan = {"target_files": [{"path": "tests/test_x.py", "role": "test"}]}
        files, degraded = extract_target_files(plan)
        assert degraded is True
        assert files == [{"path": "main.py", "role": "implementation"}]

    def test_path_traversal_and_absolute_paths_are_dropped(self, caplog):
        plan = {
            "target_files": [
                {"path": "../evil.py", "role": "implementation"},
                {"path": "/etc/passwd", "role": "implementation"},
                {"path": "app/ok.py", "role": "implementation"},
            ]
        }
        with caplog.at_level(logging.WARNING):
            files, degraded = extract_target_files(plan)
        assert degraded is False
        assert files == [{"path": "app/ok.py", "role": "implementation"}]
        assert "不正パス" in caplog.text
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `cd ~/projects/NexusCore && source .venv/bin/activate && export PYTHONPATH=src && python -m pytest tests/core/test_plan_contract.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'nexuscore.core.plan_contract'`）

- [ ] **Step 3: 最小実装を書く**

```python
# src/nexuscore/core/plan_contract.py
"""plan JSON の target_files 契約（検証・フォールバック）。

spec: docs/superpowers/specs/2026-07-17-twelve-agent-pipeline-design.md §3-1
- role は implementation / test / config の3値
- 欠落・不正時は main.py 1枚の劣化モードに縮退（WARN ログ必須）
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

VALID_ROLES = frozenset({"implementation", "test", "config"})
FALLBACK_TARGET = {"path": "main.py", "role": "implementation"}


def extract_target_files(
    plan: dict[str, Any] | None,
) -> tuple[list[dict[str, str]], bool]:
    """plan から target_files を検証付きで取り出す。

    Returns:
        (target_files, degraded): degraded=True は劣化モード（フォールバック適用）。
    """
    raw = (plan or {}).get("target_files")
    if not isinstance(raw, list) or not raw:
        logger.warning(
            "[plan_contract] target_files が欠落。劣化モード（main.py 1枚）に縮退します"
        )
        return [dict(FALLBACK_TARGET)], True

    valid: list[dict[str, str]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        path = entry.get("path")
        role = entry.get("role")
        if not path or not isinstance(path, str) or role not in VALID_ROLES:
            continue
        if path.startswith("/") or ".." in path:
            logger.warning("[plan_contract] 不正パスを除外: %s", path)
            continue
        valid.append({"path": path, "role": role})

    if not any(e["role"] == "implementation" for e in valid):
        logger.warning(
            "[plan_contract] implementation ロールが無い。劣化モードに縮退します"
        )
        return [dict(FALLBACK_TARGET)], True

    return valid, False
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python -m pytest tests/core/test_plan_contract.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
cd ~/projects/NexusCore
git add src/nexuscore/core/plan_contract.py tests/core/test_plan_contract.py
git commit -m "feat: plan_contract 新設（target_files 検証・劣化モードフォールバック・spec §3-1）"
```

---

### Task 2: planner プロンプト拡張＋plan パース堅牢化

**Files:**
- Modify: `src/nexuscore/agents/planner_agent.py`（generate_plan 内プロンプト・34行目付近）
- Modify: `src/nexuscore/core/phase_runner_mixin.py`（run_planning_phase・214行目付近の `json.loads`）
- Test: `tests/core/test_planning_phase_parse.py`

- [ ] **Step 1: planner_agent.py のプロンプトに target_files 指示を追記**

`generate_plan` 内の prompt 文字列（`# 指示` で始まるブロック）の出力仕様部分に以下を追記する。まず現状を確認:

Run: `grep -n "functions_to_implement" src/nexuscore/agents/planner_agent.py`

プロンプト内の JSON 出力例・仕様説明の直後に、以下のブロックを追加:

```text
# 出力JSONに必ず含めるキー（追加仕様）
"target_files": 生成すべきファイルの配列。各要素は {"path": "<相対パス>", "role": "<implementation|test|config>"}。
- path はプロジェクトルートからの相対パス（絶対パス・"../" は禁止）
- 実装本体は role="implementation"、テストは role="test"、設定ファイルは role="config"
- 最低1つは role="implementation" を含めること
例: "target_files": [{"path": "app/calculator.py", "role": "implementation"}, {"path": "tests/test_calculator.py", "role": "test"}]
```

- [ ] **Step 2: 失敗するテストを書く（plan パースの dict/str 両対応＋fence除去）**

```python
# tests/core/test_planning_phase_parse.py
"""run_planning_phase の plan パース堅牢化テスト。spec §6-3"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from nexuscore.core.orchestrator_models import OrchestratorContext
from nexuscore.core.phase_runner_mixin import PhaseRunnerMixin


class _Host(PhaseRunnerMixin):
    """テスト用ホスト（Orchestrator の代役）。"""

    def __init__(self, planner):
        self.logger = logging.getLogger("test_host")
        self.session_controller = None
        self.llm_router = MagicMock()
        self.requirement_agent = MagicMock()
        self.planner_agent = planner
        self.coder_agent = MagicMock(spec=[])   # implement_code なし
        self.tester_agent = MagicMock(spec=[])  # generate_tests なし
        self.project_path = "/tmp/nexus_test"


def _ctx() -> OrchestratorContext:
    return OrchestratorContext(task_id="t1", user_requirement="電卓を作る")


def test_planner_returning_dict_is_used_directly():
    planner = MagicMock()
    planner.generate_plan.return_value = {"target_files": [], "functions_to_implement": []}
    host = _Host(planner)
    ctx = host.run_planning_phase(_ctx())
    assert ctx.plan == {"target_files": [], "functions_to_implement": []}


def test_planner_returning_json_string_is_parsed():
    planner = MagicMock()
    planner.generate_plan.return_value = '{"functions_to_implement": ["f1"]}'
    host = _Host(planner)
    ctx = host.run_planning_phase(_ctx())
    assert ctx.plan == {"functions_to_implement": ["f1"]}


def test_planner_returning_fenced_json_is_parsed():
    planner = MagicMock()
    planner.generate_plan.return_value = '```json\n{"functions_to_implement": ["f1"]}\n```'
    host = _Host(planner)
    ctx = host.run_planning_phase(_ctx())
    assert ctx.plan == {"functions_to_implement": ["f1"]}


def test_planner_returning_garbage_becomes_raw_plan():
    planner = MagicMock()
    planner.generate_plan.return_value = "これはJSONではない"
    host = _Host(planner)
    ctx = host.run_planning_phase(_ctx())
    assert ctx.plan == {"raw_plan": "これはJSONではない"}
```

- [ ] **Step 3: テストが失敗することを確認**

Run: `python -m pytest tests/core/test_planning_phase_parse.py -v`
Expected: `test_planner_returning_dict_is_used_directly` と `test_planner_returning_fenced_json_is_parsed` が FAIL（現行実装は dict に `json.loads` を適用して例外→re-raise、fence 未除去）

- [ ] **Step 4: run_planning_phase のパース部を書き換え**

`src/nexuscore/core/phase_runner_mixin.py` の `run_planning_phase` 内、

```python
            try:
                plan = json.loads(plan_text)
            except (json.JSONDecodeError, ValueError):
                plan = {"raw_plan": plan_text}
```

を以下に置換:

```python
            plan = self._coerce_plan(plan_text)
```

同クラスに以下のヘルパーを追加（`_execute_task_via_npe` の直後）:

```python
    @staticmethod
    def _coerce_plan(plan_output: Any) -> dict[str, Any]:
        """planner 出力を dict に正規化する（dict / JSON文字列 / fence付き / 非JSON）。"""
        if isinstance(plan_output, dict):
            return plan_output
        text = str(plan_output or "")
        try:
            from nexuscore.utils.clean_output import clean_output

            cleaned = clean_output(text)
        except Exception:  # noqa: BLE001 — clean_output 不在/失敗時は生テキスト
            cleaned = text
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass
        return {"raw_plan": text}
```

注意: `clean_output` が fence を除去しない実装だった場合に備え、`clean_output` の実挙動を先に確認する:

Run: `grep -n "def clean_output" -A 20 src/nexuscore/utils/clean_output.py`

fence（```json ... ```）除去が無ければ `_coerce_plan` 内で自前除去を追加:

```python
        cleaned = cleaned.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            cleaned = "\n".join(
                line for line in lines if not line.strip().startswith("```")
            )
```

- [ ] **Step 5: テストが通ることを確認＋回帰**

Run: `python -m pytest tests/core/test_planning_phase_parse.py -v`
Expected: 4 passed

Run: `python -m pytest tests/core/ tests/agents/ -n auto -q`
Expected: 既存テスト含め全緑（planner 関連の既存テストが `json.loads` 挙動に依存していた場合はここで検出→既存テストの期待値を新挙動に合わせて更新）

- [ ] **Step 6: Commit**

```bash
git add src/nexuscore/agents/planner_agent.py src/nexuscore/core/phase_runner_mixin.py tests/core/test_planning_phase_parse.py
git commit -m "feat: planner プロンプトに target_files 契約追加＋plan パース堅牢化（spec §3-1/§6-3）"
```

---

### Task 3: run_implementation_phase 書き換え（hello.py 廃止・複数ファイル生成）

**Files:**
- Modify: `src/nexuscore/core/phase_runner_mixin.py:267-317`（run_implementation_phase）
- Test: `tests/core/test_implementation_phase_contract.py`
- Modify: 既存テストのうち hello.py 依存のもの（Step 5 で特定）

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/core/test_implementation_phase_contract.py
"""run_implementation_phase の target_files 契約対応テスト。spec §3-2"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from nexuscore.core.orchestrator_models import OrchestratorContext
from nexuscore.core.phase_runner_mixin import PhaseRunnerMixin


class _Host(PhaseRunnerMixin):
    def __init__(self, coder, project_path):
        self.logger = logging.getLogger("test_host")
        self.session_controller = None
        self.llm_router = MagicMock()
        self.requirement_agent = MagicMock()
        self.planner_agent = MagicMock()
        self.coder_agent = coder
        self.tester_agent = MagicMock(spec=[])
        self.project_path = str(project_path)


def _ctx(plan) -> OrchestratorContext:
    ctx = OrchestratorContext(task_id="t1", user_requirement="電卓CLIを作る")
    ctx.plan = plan
    return ctx


def test_writes_each_target_file(tmp_path):
    coder = MagicMock()
    coder.implement_code.side_effect = ["# calc code", "# cli code"]
    host = _Host(coder, tmp_path)
    plan = {
        "target_files": [
            {"path": "app/calc.py", "role": "implementation"},
            {"path": "app/cli.py", "role": "implementation"},
            {"path": "tests/test_calc.py", "role": "test"},
        ]
    }
    ctx = host.run_implementation_phase(_ctx(plan))

    assert (tmp_path / "app/calc.py").read_text(encoding="utf-8") == "# calc code"
    assert (tmp_path / "app/cli.py").read_text(encoding="utf-8") == "# cli code"
    # role=test は実装フェーズでは書かない（Phase 5 の責務・spec §4-2）
    assert not (tmp_path / "tests/test_calc.py").exists()
    # hello.py はもう作られない
    assert not (tmp_path / "hello.py").exists()
    assert ctx.implementation["files"] == {
        "app/calc.py": "# calc code",
        "app/cli.py": "# cli code",
    }
    assert ctx.implementation["degraded"] is False


def test_generated_files_are_passed_as_context_to_next_call(tmp_path):
    coder = MagicMock()
    coder.implement_code.side_effect = ["# first", "# second"]
    host = _Host(coder, tmp_path)
    plan = {
        "target_files": [
            {"path": "a.py", "role": "implementation"},
            {"path": "b.py", "role": "implementation"},
        ]
    }
    host.run_implementation_phase(_ctx(plan))

    first_kwargs = coder.implement_code.call_args_list[0].kwargs
    second_kwargs = coder.implement_code.call_args_list[1].kwargs
    assert first_kwargs["existing_code"] == ""
    assert "a.py" in second_kwargs["existing_code"]
    assert "# first" in second_kwargs["existing_code"]


def test_missing_target_files_uses_fallback_main_py(tmp_path):
    coder = MagicMock()
    coder.implement_code.return_value = "# fallback code"
    host = _Host(coder, tmp_path)
    ctx = host.run_implementation_phase(_ctx({"functions_to_implement": []}))

    assert (tmp_path / "main.py").read_text(encoding="utf-8") == "# fallback code"
    assert ctx.implementation["degraded"] is True


def test_empty_coder_output_raises(tmp_path):
    coder = MagicMock()
    coder.implement_code.return_value = ""
    host = _Host(coder, tmp_path)
    plan = {"target_files": [{"path": "a.py", "role": "implementation"}]}
    with pytest.raises(RuntimeError, match="empty"):
        host.run_implementation_phase(_ctx(plan))


def test_readme_lists_actual_generated_files(tmp_path):
    coder = MagicMock()
    coder.implement_code.return_value = "# code"
    host = _Host(coder, tmp_path)
    plan = {"target_files": [{"path": "app/calc.py", "role": "implementation"}]}
    host.run_implementation_phase(_ctx(plan))

    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "app/calc.py" in readme
    assert "Hello World" not in readme
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python -m pytest tests/core/test_implementation_phase_contract.py -v`
Expected: FAIL（現行実装は hello.py に書き込み・`implementation["files"]` キー不在）

- [ ] **Step 3: run_implementation_phase を書き換え**

`src/nexuscore/core/phase_runner_mixin.py` の `run_implementation_phase` 全体（`def run_implementation_phase` から `return context` まで）を以下に置換:

```python
    def run_implementation_phase(self, context: OrchestratorContext) -> OrchestratorContext:
        self.logger.info(f"[{context.task_id}] Phase 4: Implementation")
        context.phase_log.append("IMPLEMENTATION")

        if context.fast_lane and context.implementation:
            return context

        from nexuscore.core.plan_contract import extract_target_files

        target_files, degraded = extract_target_files(context.plan)
        impl_targets = [e for e in target_files if e["role"] in ("implementation", "config")]

        generated: dict[str, str] = {}
        for entry in impl_targets:
            code = self._generate_one_file(context, entry, generated)
            out_path = Path(self.project_path) / entry["path"]
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(code, encoding="utf-8")
            generated[entry["path"]] = code
            self.logger.info(f"Generated code saved to: {out_path}")

        context.implementation = {"files": generated, "degraded": degraded}
        self._write_generated_readme(context, generated)
        return context

    def _generate_one_file(
        self,
        context: OrchestratorContext,
        entry: dict[str, str],
        generated: dict[str, str],
    ) -> str:
        """target_files の1エントリ分のコードを coder に生成させる。

        生成済みファイルを existing_code として渡し、ファイル間整合を担保する（spec §3-2）。
        空出力は失敗として扱う（spec §6-1）。
        """
        if not hasattr(self.coder_agent, "implement_code"):
            raise RuntimeError("CoderAgent does not support implement_code")

        task_description = (
            f"要件: {context.user_requirement}\n"
            f"生成対象ファイル: {entry['path']}（役割: {entry['role']}）\n"
            f"計画: {json.dumps(context.plan.get('functions_to_implement', []), ensure_ascii=False)}"
        )
        existing = "\n\n".join(
            f"# ==== {path} ====\n{code}" for path, code in generated.items()
        )
        code = self.coder_agent.implement_code(
            task_description=task_description,
            existing_code=existing,
            code_language=os.getenv("NEXUS_CODE_LANG", "python"),
        )
        if not code or not str(code).strip():
            raise RuntimeError(f"CoderAgent returned empty output for {entry['path']}")
        return str(code)

    def _write_generated_readme(
        self, context: OrchestratorContext, generated: dict[str, str]
    ) -> None:
        """実際の生成ファイル一覧から README を組み立てる（固定文言廃止・spec §3-2）。"""
        if not generated:
            return
        try:
            file_lines = "\n".join(f"- `{p}`" for p in generated)
            readme_content = (
                f"# {Path(self.project_path).name}\n\n"
                f"## 概要\n{context.user_requirement}\n\n"
                f"## 生成されたファイル\n\n{file_lines}\n\n"
                f"## 作成日時\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            readme_path = Path(self.project_path) / "README.md"
            readme_path.write_text(readme_content, encoding="utf-8")
            self.logger.info(f"README.md saved to: {readme_path}")
        except (OSError, UnicodeEncodeError) as e:
            self.logger.warning(f"Failed to save README: {e}")
```

- [ ] **Step 4: 新テストが通ることを確認**

Run: `python -m pytest tests/core/test_implementation_phase_contract.py -v`
Expected: 5 passed

- [ ] **Step 5: 既存テストの hello.py 依存を特定して更新**

Run: `grep -rln "hello\.py\|hello_path\|implementation\[.code.\]\|{\"code\"" tests/ --include="*.py" | head -20`

各ヒットを開き、以下の方針で更新する:
- `run_implementation_phase` が hello.py を書く前提のテスト → 新契約（`implementation["files"]`・target_files）の期待値に書き換え
- fast_lane 経路（`implementation = {"code": ...}`）のテスト → **変更しない**（fast_lane は旧形式を維持）
- 単なる文字列一致（無関係）→ 変更しない

Run: `python -m pytest tests/ -n auto -q 2>&1 | tail -3`
Expected: 全緑（4801+15 前後 passed / 0 failed）

- [ ] **Step 6: Commit**

```bash
git add src/nexuscore/core/phase_runner_mixin.py tests/core/test_implementation_phase_contract.py <更新した既存テスト>
git commit -m "feat: 実装フェーズを target_files 契約に接続（hello.py固定廃止・spec §3-2）"
```

---

### Task 4: run_full_project の context 返却＋Smoke Test 再定義

**Files:**
- Modify: `src/nexuscore/core/orchestrator.py:140-199`（run_full_project の戻り値）
- Modify: `main_cli.py:365-398`（Smoke Test ブロック）
- Test: `tests/core/test_smoke_gate.py`

- [ ] **Step 1: run_full_project が context を返すよう変更**

`src/nexuscore/core/orchestrator.py` の `run_full_project`:
- シグネチャの戻り値型を `-> None` から `-> OrchestratorContext | None` に変更
- 正常終了パス末尾（`self._log_orch_event(run_db_id, "shutdown", "FINISHED", ...)` の直後）に `return context` を追加
- `SessionStopped` パスの `return` は `return None` のまま（既存挙動維持）

既存呼び出し元は戻り値を無視しているため非破壊。

- [ ] **Step 2: 失敗するテストを書く（Smoke Test の新ロジックを関数化してテスト）**

新関数 `run_smoke_gate` を `main_cli.py` に切り出す前提でテストを書く:

```python
# tests/core/test_smoke_gate.py
"""main_cli の Smoke Test 再定義テスト。spec §3-3"""
from __future__ import annotations

import sys
from pathlib import Path

# main_cli はリポジトリルート直下のためパスを通す
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from main_cli import run_smoke_gate  # noqa: E402


def test_all_files_exist_and_compile(tmp_path):
    (tmp_path / "app").mkdir()
    (tmp_path / "app/calc.py").write_text("def add(a, b):\n    return a + b\n")
    target_files = [{"path": "app/calc.py", "role": "implementation"}]
    ok, errors = run_smoke_gate(str(tmp_path), target_files)
    assert ok is True
    assert errors == []


def test_missing_file_fails(tmp_path):
    target_files = [{"path": "app/missing.py", "role": "implementation"}]
    ok, errors = run_smoke_gate(str(tmp_path), target_files)
    assert ok is False
    assert any("missing.py" in e for e in errors)


def test_syntax_error_fails(tmp_path):
    (tmp_path / "bad.py").write_text("def broken(:\n")
    target_files = [{"path": "bad.py", "role": "implementation"}]
    ok, errors = run_smoke_gate(str(tmp_path), target_files)
    assert ok is False
    assert any("bad.py" in e for e in errors)


def test_config_files_skip_py_compile(tmp_path):
    (tmp_path / "config.toml").write_text("[tool]\nname = 'x'\n")
    target_files = [{"path": "config.toml", "role": "config"}]
    ok, errors = run_smoke_gate(str(tmp_path), target_files)
    assert ok is True
```

- [ ] **Step 3: テストが失敗することを確認**

Run: `python -m pytest tests/core/test_smoke_gate.py -v`
Expected: FAIL（`ImportError: cannot import name 'run_smoke_gate'`）

- [ ] **Step 4: main_cli.py に run_smoke_gate を実装し旧ブロックを置換**

`main_cli.py` に関数を追加（`_save_codex_artifacts` の直後）:

```python
def run_smoke_gate(
    project_path: str, target_files: list[dict[str, str]]
) -> tuple[bool, list[str]]:
    """成果物チェック（Smoke Test Gate）。

    plan の target_files 全実在 + .py の py_compile 通過を成功条件とする（spec §3-3）。
    role=test のファイルは Stage 1 時点では未生成のため検査対象外。
    """
    import py_compile

    errors: list[str] = []
    for entry in target_files:
        if entry.get("role") == "test":
            continue
        rel = entry.get("path", "")
        abs_path = os.path.join(project_path, rel)
        if not os.path.exists(abs_path):
            errors.append(f"missing artifact: {rel}")
            continue
        if rel.endswith(".py"):
            try:
                py_compile.compile(abs_path, doraise=True)
            except py_compile.PyCompileError as e:
                errors.append(f"syntax error in {rel}: {e.msg}")
    return (not errors), errors
```

`main()` 内の旧 Smoke Test ブロック（`# --- 6. 成果物チェック（Smoke Test Gate） ---` から `raise SystemExit(exit_code)` まで）を以下に置換:

```python
        # --- 6. 成果物チェック（Smoke Test Gate・spec §3-3） ---
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

        if exit_code != 0:
            run_status = "failure"
            raise SystemExit(exit_code)
```

あわせて `main()` 内の固定パイプライン呼び出しを戻り値受け取りに変更:

```python
            result_context = orchestrator.run_full_project(
                user_requirement=args.requirement,
                language=args.language
            )
```

（`--dynamic` 分岐側の直前に `result_context = None` の初期化を追加すること）

- [ ] **Step 5: テストが通ることを確認＋回帰**

Run: `python -m pytest tests/core/test_smoke_gate.py -v`
Expected: 4 passed

Run: `python -m pytest tests/ -n auto -q 2>&1 | tail -3`
Expected: 全緑（main_cli の Smoke Test を検証する既存テストがあれば新仕様に更新）

- [ ] **Step 6: Commit**

```bash
git add main_cli.py src/nexuscore/core/orchestrator.py tests/core/test_smoke_gate.py
git commit -m "feat: Smoke Test を target_files 実在+py_compile 検査に再定義（spec §3-3）"
```

---

### Task 5: ドキュメント整合＋Stage 1 クローズ

**Files:**
- Modify: `CLAUDE.md`（「14の自律エージェント」「14個の自律エージェント」→ 12）
- Modify: `docs/変更履歴.md`（Keep a Changelog 形式で追記）

- [ ] **Step 1: CLAUDE.md のエージェント数を是正**

Run: `grep -n "14" CLAUDE.md`

「14の自律エージェント」→「12の自律エージェント」、「14個の自律エージェント」→「12個の自律エージェント」に置換（spec §6-5）。

- [ ] **Step 2: 変更履歴.md に追記**

`docs/変更履歴.md` の先頭（最新エントリの上）に追加:

```markdown
## 2026-XX-XX（実施日に置換）

### Added
- `core/plan_contract.py`: plan JSON の target_files 契約（検証・劣化モードフォールバック）
- planner プロンプトに target_files 生成指示（path/role契約）

### Changed
- 実装フェーズ: hello.py 固定書き込みを廃止し、target_files に基づく複数ファイル生成に変更（生成済みファイルを existing_code で伝搬）
- Smoke Test: hello.py 存在+"Hello"出力 → target_files 全実在+py_compile 構文チェックに再定義
- `run_full_project` が OrchestratorContext を返すように変更（既存呼び出しは非破壊）
- README 自動生成: 固定文言を廃止し実際の生成ファイル一覧から組み立て

### Fixed
- CLAUDE.md のエージェント数 14→12（監査C-1関連のドキュメント整合）
- plan パース: dict/JSON文字列/fence付き/非JSON の4形態に対応
```

- [ ] **Step 3: 最終回帰（全テスト）**

Run: `python -m pytest tests/ -n auto -q 2>&1 | tail -3`
Expected: 0 failed

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md docs/変更履歴.md
git commit -m "docs: Stage 1 完了（エージェント数是正・変更履歴追記・spec §6-5）"
```

---

## Stage 2/3 について

Stage 2（品質ループ）・Stage 3（学習レイヤー）のプランは、Stage 1 完了後の実コードに合わせて別ファイルで起こす。
**Stage 2 プラン作成時の申し送り**:
- spec §4-1 の `architect.design_architecture(specs, plan)` は現存しない。実在するのは `design_project_structure(user_requirement) -> str`。既存メソッド活用か新設かを Stage 2 プラン冒頭で決定すること。
- spec §6-5 の README パイプライン説明更新（「12のAIエージェントが順次起動」の実態合わせ）は、12体が実際に稼働する Stage 3 完了後に実施する（Stage 1 で書き換えると再び主張過剰になるため）。
