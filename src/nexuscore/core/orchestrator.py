# ==============================================================================
# 操作するソフト : VSCode（推奨）
# フォルダ       : src/nexuscore/core/
# ファイル名     : orchestrator.py
#
# 日付 (JST)     : 2025-11-14
# バージョン     : 8.2.0J (NPE Function-Based Integration + WSL Safe)
#
# 要旨:
#   - 旧設計の NexusProtocolEngine クラス依存を完全に排除。
#   - NPE は engine.guardedd_llm_call() を中核とする「関数ベース・プロトコル」として統合。
#   - Orchestrator に LLMRouter を正式に注入し、NPE → Router → Provider の経路を確立。
#   - WSL/Windows の差異に依存しないよう、ファイルパス/ログ周りをシンプル化。
#   - main_cli.py からの import 時に ImportError が出ないことを最優先設計。
# ==============================================================================

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional

# ------------------------------------------------------------------------------
# パス設定 (自己完結性を高めるため: src/ を sys.path に追加)
# ------------------------------------------------------------------------------
try:
    current_dir = Path(__file__).resolve().parent          # .../src/nexuscore/core
    src_dir = current_dir.parents[2]                       # .../src
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
except Exception:
    print("[orchestrator] Warning: could not determine src directory.", file=sys.stderr)

# ------------------------------------------------------------------------------
# 依存モジュール (Agents / NPE / Router / Utils)
# ------------------------------------------------------------------------------

# エージェント群
from nexuscore.agents.requirement_agent import RequirementAgent
from nexuscore.agents.architect_agent import ArchitectAgent
from nexuscore.agents.planner_agent import PlannerAgent
from nexuscore.agents.coder_agent import CoderAgent
from nexuscore.agents.tester_agent import TesterAgent
from nexuscore.agents.debugger_agent import DebuggerAgent
from nexuscore.agents.guardian_agent import GuardianAgent
from nexuscore.agents.policy_agent import PolicyAgent
from nexuscore.agents.postmortem_agent import PostmortemAgent
from nexuscore.agents.knowledge_curator_agent import KnowledgeCuratorAgent
from nexuscore.agents.patch_applier import PatchApplier

# NPE: クラスではなく「関数ベース・プロトコル」として利用
from nexuscore.npe.engine import guarded_llm_call

# LLM ルーター
from nexuscore.llm.llm_router import LLMRouter

# セッション制御
from nexuscore.core.session_control import SessionController

# ユーティリティ (必要に応じて使用)
try:
    from nexuscore.utils.clean_output import clean_output
except Exception:
    # クリーンアップ関数が存在しない場合でも Orchestrator 自体は動作させる
    def clean_output(x: str) -> str:
        return x


# ==============================================================================
# Orchestrator 本体
# ==============================================================================


class OrchestratorPhase(Enum):
    """
    開発フローのフェーズを表現する Enum。

    Requirement → Plan → Architecture → Implementation → Testing → Review
    の順序で実行される。
    """
    REQUIREMENTS = auto()
    PLAN = auto()
    ARCHITECTURE = auto()
    IMPLEMENTATION = auto()
    TESTING = auto()
    REVIEW = auto()


@dataclass
class OrchestratorContext:
    """
    Orchestrator の実行コンテキストを保持するデータクラス。

    各フェーズ間で状態を引き継ぐために使用される。
    """
    task_id: str
    user_requirement: str
    language: str = "ja"
    fast_lane: bool = False
    run_db_id: Optional[int] = None

    # フェーズごとの出力
    specs: Dict[str, Any] = field(default_factory=dict)
    plan: Dict[str, Any] = field(default_factory=dict)
    architecture: Dict[str, Any] = field(default_factory=dict)
    implementation: Dict[str, Any] = field(default_factory=dict)
    testing: Dict[str, Any] = field(default_factory=dict)
    review: Dict[str, Any] = field(default_factory=dict)

    # フェーズ実行ログ（テスト用）
    phase_log: List[str] = field(default_factory=list)


@dataclass
class Orchestrator:
    """
    NexusCore の中核となるオーケストレータ。
    - Requirement → Planning → Architecture → Coding → Testing → Review → Postmortem
    の大まかな流れを制御する。
    - 実際の LLM 呼び出しは「NPE (guarded_llm_call) → LLMRouter.complete」に委譲する。
    """

    project_path: str
    constitution: Dict[str, Any]

    # --- エージェント群 ---
    requirement_agent: RequirementAgent
    architect_agent: ArchitectAgent
    planner_agent: PlannerAgent
    coder_agent: CoderAgent
    tester_agent: TesterAgent
    debugger_agent: DebuggerAgent
    guardian_agent: GuardianAgent
    policy_agent: PolicyAgent
    postmortem_agent: PostmortemAgent
    knowledge_curator_agent: KnowledgeCuratorAgent
    patch_applier_agent: PatchApplier

    # --- LLM Router / 設定 ---
    llm_router: LLMRouter
    max_retries: int = 5

    # 新規: セッション制御オブジェクト（省略可能）
    session_controller: Optional[SessionController] = None

    # --- 内部状態 ---
    logger: logging.Logger = field(init=False)

    # ------------------------------------------------------------------
    # 初期化
    # ------------------------------------------------------------------
    def __post_init__(self) -> None:
        # ロガーの準備
        self._setup_logger()
        self.logger.info("Orchestrator v8.2 initialized.")
        self.logger.info(f"Project path: {self.project_path}")
        self.logger.info("NPE (function-based guarded_llm_call) is ready.")
        self.logger.info("LLMRouter is attached to Orchestrator.")

    def _setup_logger(self) -> None:
        log_dir = os.path.join(self.project_path, "logs", "orchestrator")
        os.makedirs(log_dir, exist_ok=True)

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)

        # 重複ハンドラ防止: 複数インスタンス生成時にもハンドラが多重登録されないようにする。
        if not self.logger.handlers:
            log_path = os.path.join(log_dir, f"orchestrator_{int(time.time())}.log")
            fh = logging.FileHandler(log_path, encoding="utf-8")
            ch = logging.StreamHandler(sys.stdout)

            fmt = logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            fh.setFormatter(fmt)
            ch.setFormatter(fmt)

            self.logger.addHandler(fh)
            self.logger.addHandler(ch)

    def _maybe_stop(self, phase: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """
        フェーズの境目で呼び出される中断判定ヘルパー。

        - `checkpoint` を更新して、どこまで進んだか state.json に保存。
        - `control.json` に stop/pause 指示があれば RuntimeError("SessionStopped")
          を投げて処理全体を安全に中断する。
        """
        if not self.session_controller:
            return

        # まずチェックポイントを保存（「ここまでで一旦保存して」に相当）
        try:
            self.session_controller.checkpoint(phase, extra or {})
        except Exception:
            # チェックポイント保存に失敗してもメイン処理は継続させる
            self.logger.exception(f"Failed to checkpoint session at phase '{phase}'")

        # 中断指示が出ているか確認
        try:
            if self.session_controller.should_stop():
                self.logger.warning(
                    f"Session stop requested at phase '{phase}'. Aborting gracefully."
                )
                raise RuntimeError("SessionStopped")
        except RuntimeError:
            # そのまま上位に投げる
            raise
        except Exception:
            # 予期せぬエラーはログだけ出して継続
            self.logger.exception("Error while checking session stop request.")

    # ------------------------------------------------------------------
    # NPE 経由で LLM を叩くヘルパー
    # ------------------------------------------------------------------
    def _execute_task_via_npe(self, prompt: str, metadata: Dict[str, Any]) -> str:
        """
        最新 NPE 仕様に基づき、guarded_llm_call() 経由で LLMRouter を呼び出す。
        - 予算ガード / ログ / ポリシーは NPE 側の engine/budget/logger/policies に委譲。
        - metadata['task_type'] に応じて llm_router.task_model_map を選択する。
        - guarded_llm_call は dict を返す想定で、その content を抽出する（文字列の場合はそのまま）。
        - metadata['as_json'] が True の場合はシステムプロンプトが JSON 指向になる前提で、将来拡張も想定。
        """
        task_type = metadata.get("task_type") or "generic"
        self.logger.info(f"[NPE] Delegating task '{task_type}' to guarded_llm_call().")

        # Router 側の task_model_map / default_model を尊重
        task_model_map = getattr(self.llm_router, "task_model_map", {}) or {}
        default_model = getattr(self.llm_router, "default_model", None)
        model = task_model_map.get(task_type, default_model)

        # system_prompt は軽量な規律程度に留める（必要なら今後強化）
        system_prompt = (
            "You are the NexusCore Orchestration LLM. "
            "Follow metadata.task_type and return concise, machine-consumable output. "
            "If metadata.as_json is True, return strictly valid JSON."
        )

        result = guarded_llm_call(
            model=model,
            task=task_type,
            system_prompt=system_prompt,
            user_prompt=prompt,
            llm_complete_fn=self.llm_router.complete,
        )

        # NPE 戻り値の標準形: dict {"ok": bool, "reason": str, "content": str, "usage": {...}}
        if isinstance(result, dict):
            content = result.get("content", "")
        else:
            content = str(result)

        return clean_output(content)

    # ------------------------------------------------------------------
    # フェーズ別メソッド（各フェーズの責務を明確化）
    # ------------------------------------------------------------------
    def run_requirements_phase(self, context: OrchestratorContext) -> OrchestratorContext:
        """
        Phase 1: Requirement Definition

        Args:
            context: OrchestratorContext

        Returns:
            更新された OrchestratorContext
        """
        self.logger.info(f"[{context.task_id}] Phase 1: Requirement Definition")
        self._maybe_stop("before_requirement", {"task_id": context.task_id})
        context.phase_log.append("REQUIREMENTS")

        specs: Dict[str, Any] = {}

        try:
            use_ui = bool(getattr(self.requirement_agent, "use_ui", False))
            if use_ui and hasattr(self.requirement_agent, "launch_gradio_ui"):
                specs = self.requirement_agent.launch_gradio_ui(share=False)
            elif hasattr(self.requirement_agent, "analyze_requirement"):
                specs = self.requirement_agent.analyze_requirement(context.user_requirement)
            else:
                # 最低限、テキストとして持っておく
                specs = {"raw_requirement": context.user_requirement}
        except Exception as e:
            self.logger.error(f"[{context.task_id}] Requirement phase failed: {e}", exc_info=True)
            raise

        if not specs:
            self.logger.error(f"[{context.task_id}] Requirement definition returned empty specs. Aborting.")
            raise ValueError("Requirement definition returned empty specs")

        context.specs = specs
        self._maybe_stop("after_requirement", {"specs_summary": str(specs)[:500] if specs else ""})

        # Orchestrator ログフック（Requirement完了）
        try:
            from nexuscore.core.orchestrator_db_hook import log_orchestrator_event

            log_orchestrator_event(
                run_db_id=context.run_db_id,
                phase="requirement",
                status="SUCCESS",
                message="Requirement phase completed",
            )
        except Exception:
            pass

        return context

    def run_planning_phase(self, context: OrchestratorContext) -> OrchestratorContext:
        """
        Phase 2: Planning

        FastLane モードの場合は、Planning / Coding / Testing を並列実行する。

        Args:
            context: OrchestratorContext

        Returns:
            更新された OrchestratorContext
        """
        self.logger.info(f"[{context.task_id}] Phase 2: Planning (fast_lane={context.fast_lane})")
        self._maybe_stop("before_planning", {})
        context.phase_log.append("PLAN")

        def _run_plan():
            if hasattr(self.planner_agent, "generate_plan"):
                req_json = json.dumps(context.specs, ensure_ascii=False, indent=2)
                return self.planner_agent.generate_plan(req_json)
            plan_prompt = (
                "以下の要件仕様に基づき、実装タスクの計画を立ててください。\n"
                "可能であれば JSON 形式で 'functions_to_implement' 配列を含めてください。\n\n"
                f"{json.dumps(context.specs, ensure_ascii=False, indent=2)}"
            )
            return self._execute_task_via_npe(
                prompt=plan_prompt,
                metadata={"task_type": "planning", "as_json": False},
            )

        def _run_code():
            if hasattr(self.coder_agent, "implement_code"):
                return self.coder_agent.implement_code(
                    task_description=context.user_requirement,
                    existing_code="",
                    code_language=os.getenv("NEXUS_CODE_LANG", "python"),
                )
            return ""

        def _run_test():
            if hasattr(self.tester_agent, "generate_tests"):
                return self.tester_agent.generate_tests(context.user_requirement)
            return ""

        try:
            if context.fast_lane:
                # FastLane: Planning / Coding / Testing を並列実行
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=3) as ex:
                    future_plan = ex.submit(_run_plan)
                    future_code = ex.submit(_run_code)
                    future_test = ex.submit(_run_test)
                    plan_text = future_plan.result()
                    code_result = future_code.result()
                    test_result = future_test.result()

                # FastLane のテスト結果を補完
                test_result = self._ensure_fastlane_tests(
                    initial_result=test_result,
                    plan_text=plan_text,
                    code_result=code_result,
                    requirement=context.user_requirement,
                )

                # 結果をコンテキストに保存（Implementation と Testing フェーズで使用）
                context.implementation = {"code": code_result}
                context.testing = {"tests": test_result}
            else:
                # 通常モード: Planning のみ実行
                plan_text = _run_plan()

            try:
                plan = json.loads(plan_text)
            except Exception:
                plan = {"raw_plan": plan_text}

            context.plan = plan
            self._maybe_stop("after_planning", {"plan_preview": str(plan_text)[:500] if plan_text else ""})

            # Orchestrator ログフック（Planning完了）
            try:
                from nexuscore.core.orchestrator_db_hook import log_orchestrator_event

                log_orchestrator_event(
                    run_db_id=context.run_db_id,
                    phase="planning",
                    status="SUCCESS",
                    message="Planning phase completed",
                    extra={"fast_lane": context.fast_lane},
                )
            except Exception:
                pass

        except Exception as e:
            self.logger.error(f"[{context.task_id}] Planning phase failed: {e}", exc_info=True)
            context.plan = {"error": str(e), "raw_specs": context.specs}
            # Orchestrator ログフック（Planning失敗）
            try:
                from nexuscore.core.orchestrator_db_hook import log_orchestrator_event

                log_orchestrator_event(
                    run_db_id=context.run_db_id,
                    phase="planning",
                    status="FAILED",
                    message=f"Planning phase failed: {str(e)[:200]}",
                )
            except Exception:
                pass
            raise

        return context

    def run_architecture_phase(self, context: OrchestratorContext) -> OrchestratorContext:
        """
        Phase 3: Architecture

        Args:
            context: OrchestratorContext

        Returns:
            更新された OrchestratorContext
        """
        self.logger.info(f"[{context.task_id}] Phase 3: Architecture")
        context.phase_log.append("ARCHITECTURE")

        # 将来拡張用: 現在は空の実装
        context.architecture = {}

        return context

    def run_implementation_phase(self, context: OrchestratorContext) -> OrchestratorContext:
        """
        Phase 4: Implementation (Coding)

        FastLane モードの場合は、Planning フェーズで既に実行済みのためスキップ。

        Args:
            context: OrchestratorContext

        Returns:
            更新された OrchestratorContext
        """
        self.logger.info(f"[{context.task_id}] Phase 4: Implementation")
        context.phase_log.append("IMPLEMENTATION")

        # FastLane の場合は既に実行済み
        if context.fast_lane and context.implementation:
            return context

        def _run_code():
            if hasattr(self.coder_agent, "implement_code"):
                return self.coder_agent.implement_code(
                    task_description=context.user_requirement,
                    existing_code="",
                    code_language=os.getenv("NEXUS_CODE_LANG", "python"),
                )
            return ""

        code_result = _run_code()
        context.implementation = {"code": code_result}

        # 生成されたコードをファイルに保存
        if code_result:
            try:
                # hello.py として保存（Smoke Test要件）
                hello_path = Path(self.project_path) / "hello.py"
                hello_path.parent.mkdir(parents=True, exist_ok=True)
                hello_path.write_text(code_result, encoding="utf-8")
                self.logger.info(f"Generated code saved to: {hello_path}")

                # README.md も生成（Smoke Test要件）
                readme_path = Path(self.project_path) / "README.md"
                readme_content = f"""# {Path(self.project_path).name}

## 概要
{context.user_requirement}

## 実行方法

```bash
python hello.py
```

## 生成されたファイル

- `hello.py` - Hello World を表示する Python スクリプト

## 作成日時
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
                readme_path.write_text(readme_content, encoding="utf-8")
                self.logger.info(f"README.md saved to: {readme_path}")
            except Exception as e:
                self.logger.warning(f"Failed to save files: {e}")

        return context

    def run_testing_phase(self, context: OrchestratorContext) -> OrchestratorContext:
        """
        Phase 5: Testing

        FastLane モードの場合は、Planning フェーズで既に実行済みのためスキップ。

        Args:
            context: OrchestratorContext

        Returns:
            更新された OrchestratorContext
        """
        self.logger.info(f"[{context.task_id}] Phase 5: Testing")
        context.phase_log.append("TESTING")

        # FastLane の場合は既に実行済み
        if context.fast_lane and context.testing:
            return context

        def _run_test():
            if hasattr(self.tester_agent, "generate_tests"):
                return self.tester_agent.generate_tests(context.user_requirement)
            return ""

        test_result = _run_test()
        context.testing = {"tests": test_result}

        return context

    def run_review_phase(self, context: OrchestratorContext) -> OrchestratorContext:
        """
        Phase 6: Review

        Args:
            context: OrchestratorContext

        Returns:
            更新された OrchestratorContext
        """
        self.logger.info(f"[{context.task_id}] Phase 6: Review")
        context.phase_log.append("REVIEW")

        # 将来拡張用: 現在は空の実装
        context.review = {}

        return context

    # ------------------------------------------------------------------
    # メインフロー (フェーズ分割後の簡素化版)
    # ------------------------------------------------------------------
    def run_full_project(
        self,
        user_requirement: str,
        language: str = "ja",
        fast_lane: bool = False,
        run_db_id: Optional[int] = None,
    ) -> None:
        """
        高レベルな「フルプロジェクト」実行フロー。

        フェーズ分割後の簡素化版: 各フェーズメソッドを順番に呼び出すだけの構造。

        Args:
            user_requirement: ユーザー要件
            language: 言語（デフォルト: "ja"）
            fast_lane: 高速レーン実行フラグ
            run_db_id: Run.id（Webapp側でRunレコードを作成したときのID、CLI実行時はNone）
        """
        self.logger.info(f"=== Full Project Run Start === requirement='{user_requirement}'")
        task_id = uuid.uuid4().hex

        # Orchestrator ログフック（開始時）
        try:
            from nexuscore.core.orchestrator_db_hook import log_orchestrator_event

            log_orchestrator_event(
                run_db_id=run_db_id,
                phase="startup",
                status="STARTED",
                message="Orchestrator run started",
                extra={
                    "task_id": task_id,
                    "requirement": user_requirement[:200],
                    "autonomy_level": self.constitution.get("automation_policy", {}).get("autonomy_level"),
                },
            )
        except Exception:
            # ログ失敗は既存の処理を止めない
            pass

        # 初期コンテキストの作成
        context = OrchestratorContext(
            task_id=task_id,
            user_requirement=user_requirement,
            language=language,
            fast_lane=fast_lane,
            run_db_id=run_db_id,
        )

        try:
            # Phase 0: 開始直後のチェックポイント
            self._maybe_stop("start", {"task_id": task_id, "requirement": user_requirement})

            # フェーズを順番に実行
            context = self.run_requirements_phase(context)
            context = self.run_planning_phase(context)
            context = self.run_architecture_phase(context)
            context = self.run_implementation_phase(context)
            context = self.run_testing_phase(context)
            context = self.run_review_phase(context)

            # FastLane の場合の後処理（ログ出力）
            if fast_lane:
                code_result = context.implementation.get("code", "")
                test_result = context.testing.get("tests", "")
                plan_text = json.dumps(context.plan, ensure_ascii=False, indent=2)
                self.logger.info(
                    "[FastLane] coder output length=%s, tester output length=%s",
                    len(code_result) if code_result else 0,
                    len(test_result) if test_result else 0,
                )
                if not hasattr(self, "last_fastlane_outputs"):
                    self.last_fastlane_outputs = {}
                self.last_fastlane_outputs = {
                    "code": code_result,
                    "tests": test_result,
                    "plan": plan_text,
                }

            # Phase 3 以降の開発サイクル（将来拡張用）
            tasks = context.plan.get("functions_to_implement", []) if isinstance(context.plan, dict) else []
            self.logger.info(f"[{task_id}] Phase 3: Development Cycle (tasks={len(tasks)})")

            self.logger.info(f"=== Full Project Run Finished === requirement='{user_requirement}'")

            # Orchestrator ログフック（完了）
            try:
                from nexuscore.core.orchestrator_db_hook import log_orchestrator_event

                log_orchestrator_event(
                    run_db_id=run_db_id,
                    phase="shutdown",
                    status="FINISHED",
                    message="Orchestrator run finished",
                )
            except Exception:
                pass

        except RuntimeError as e:
            if str(e) == "SessionStopped":
                self.logger.info(
                    f"Project run stopped by user request. "
                    f"All generated files remain on disk for session resume."
                )
                # Orchestrator ログフック（中断）
                try:
                    from nexuscore.core.orchestrator_db_hook import log_orchestrator_event

                    log_orchestrator_event(
                        run_db_id=run_db_id,
                        phase="shutdown",
                        status="INTERRUPTED",
                        message="Orchestrator run stopped by user request",
                    )
                except Exception:
                    pass
                return
            # それ以外の RuntimeError は従来通り上位に投げる
            raise
        except Exception as e:
            self.logger.error(f"[{task_id}] Orchestrator run failed: {e}", exc_info=True)
            # Orchestrator ログフック（例外）
            try:
                from nexuscore.core.orchestrator_db_hook import log_orchestrator_event

                log_orchestrator_event(
                    run_db_id=run_db_id,
                    phase="orchestrator",
                    status="FAILED",
                    message=f"Orchestrator run failed: {str(e)[:200]}",
                )
            except Exception:
                pass
            raise

    def _ensure_fastlane_tests(
        self,
        initial_result: str,
        plan_text: str,
        code_result: str,
        requirement: str,
    ) -> str:
        """
        Fast-Lane で tester が要件だけを参照した際、追加コンテキストを与えて再実行する。
        """
        result = initial_result or ""
        tester = getattr(self, "tester_agent", None)
        if not tester:
            return result

        def _call_with_logging(func_name: str, *args, **kwargs) -> str:
            func = getattr(tester, func_name, None)
            if not callable(func):
                return ""
            try:
                self.logger.info("[FastLane] tester fallback via %s", func_name)
                return func(*args, **kwargs) or ""
            except Exception as err:
                self.logger.warning(
                    "[FastLane] tester fallback %s failed: %s", func_name, err,
                    exc_info=True,
                )
                return ""

        if result:
            return result

        # 1) Use plan JSON if available.
        if plan_text:
            try:
                plan_json = json.loads(plan_text)
            except Exception:
                plan_json = None
            if plan_json:
                module_hint = os.getenv(
                    "FAST_LANE_TEST_MODULE", "fast_lane.regression_suite"
                )
                result = _call_with_logging(
                    "generate_tests_from_plan",
                    plan_json,
                    module_hint,
                )
                if result:
                    return result

        # 2) Use the generated code snippet if any.
        if code_result:
            result = _call_with_logging(
                "generate_tests_and_testimony",
                code_result,
            )
            if result:
                return result

        # 3) Final fallback to requirement summary.
        if hasattr(tester, "generate_tests"):
            fallback = tester.generate_tests(requirement) or ""
            return fallback

        return result


# ==============================================================================
# Agent チームの組成
# ==============================================================================

def assemble_agent_team(project_path: str) -> Dict[str, Any]:
    """
    ハイブリッド・アーキテクチャに基づき、Orchestrator に渡すエージェント群と LLMRouter を生成する。
    API サーバ等の外部エントリポイントからも再利用され得るデフォルトのチーム編成。

    戻り値:
        {
            "requirement_agent": RequirementAgent(...),
            "architect_agent":   ArchitectAgent(...),
            ...
            "patch_applier_agent": PatchApplier(...),
            "llm_router":        LLMRouter(...),
        }
    """
    logger = logging.getLogger("AgentAssembler")
    logger.info("Assembling agent team for NexusCore Orchestrator v8.2...")

    # LLM Router を最初に作成しておく（必要ならエージェントに渡せるようにする）
    llm_router = LLMRouter()

    # ここでは、各 Agent がデフォルトコンストラクタで生成できる前提とし、
    # 追加の依存は将来的に渡せるよう拡張余地を残す。
    requirement_agent = RequirementAgent()
    architect_agent = ArchitectAgent()
    planner_agent = PlannerAgent()
    coder_agent = CoderAgent()
    tester_agent = TesterAgent()
    debugger_agent = DebuggerAgent()
    guardian_agent = GuardianAgent()
    policy_agent = PolicyAgent()
    postmortem_agent = PostmortemAgent()
    curator_api_key = os.getenv("ANTHROPIC_API_KEY", "")
    curator_model = os.getenv("NEXUS_TASK_MODEL_KNOWLEDGE", "claude-3.5-sonnet")

    if not curator_api_key:
        raise RuntimeError(
            "KnowledgeCuratorAgent requires ANTHROPIC_API_KEY. Set it in the environment before assembling agent team."
        )

    knowledge_curator_agent = KnowledgeCuratorAgent(
        api_key=curator_api_key,
        model=curator_model,
    )
    patch_applier_agent = PatchApplier()

    agents: Dict[str, Any] = {
        "requirement_agent": requirement_agent,
        "architect_agent": architect_agent,
        "planner_agent": planner_agent,
        "coder_agent": coder_agent,
        "tester_agent": tester_agent,
        "debugger_agent": debugger_agent,
        "guardian_agent": guardian_agent,
        "policy_agent": policy_agent,
        "postmortem_agent": postmortem_agent,
        "knowledge_curator_agent": knowledge_curator_agent,
        "patch_applier_agent": patch_applier_agent,
        "llm_router": llm_router,
    }

    logger.info(f"Agent team assembled. total={len(agents)} (including llm_router).")
    return agents


# ==============================================================================
# CLI エントリポイント (main_cli.py からも直接 import されることを想定)
# ==============================================================================

def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="NexusCore Orchestrator v8.2 (NPE + Router Integrated)"
    )
    parser.add_argument(
        "--project",
        type=str,
        default=str(Path.cwd()),
        help="プロジェクトのルートパス（デフォルト: カレントディレクトリ）",
    )
    parser.add_argument(
        "--requirement",
        type=str,
        default="サンプルの要件です。",
        help="自然言語での要件（デモ・テスト用）",
    )
    parser.add_argument(
        "--autonomy-level",
        type=int,
        default=1,
        help="自動化レベル（0=対話中心, 1=半自動, 2=ほぼ全自動）",
    )
    parser.add_argument(
        "--fast-lane",
        action="store_true",
        help="Planner/Coder/Tester を並列で走らせる高速モードを有効化",
    )
    # 新規: セッションID（省略時は自動生成）
    parser.add_argument(
        "--session-id",
        type=str,
        help="セッションID（省略時は UUID で自動生成されます）",
    )
    return parser


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    parser = _build_arg_parser()
    args = parser.parse_args()

    logger = logging.getLogger("CLI_LAUNCHER")
    logger.info("Orchestrator launch sequence initiated (v8.2).")

    constitution = {
        "automation_policy": {
            "autonomy_level": args.autonomy_level,
        }
    }

    # セッションIDの決定（指定がなければ UUID を採用）
    session_id = args.session_id or uuid.uuid4().hex
    logger.info(f"Using session_id={session_id} for this run.")

    # SessionController を初期化
    session_controller = SessionController(
        session_id=session_id,
        root_dir=os.path.join(args.project, ".nexus", "sessions")
    )

    try:
        agent_team = assemble_agent_team(project_path=args.project)
        orch = Orchestrator(
            project_path=args.project,
            constitution=constitution,
            session_controller=session_controller,
            **agent_team,
        )
        logger.info("Orchestrator instance created. Starting full project run.")
        orch.run_full_project(args.requirement, fast_lane=args.fast_lane)
        logger.info("Orchestrator process finished successfully.")
    except RuntimeError as e:
        if str(e) == "SessionStopped":
            logger.info("Orchestrator stopped by user request (SessionStopped).")
            sys.exit(0)  # 正常終了として扱う
        raise
    except Exception as e:
        logger.critical(f"A critical error occurred in Orchestrator: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
