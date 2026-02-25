"""
self_healing_service.py (REFACTORED VERSION)

Self-Healing Code Review MVP の本体サービス - リファクタリング版

主な改善:
  - run_for_pull_request() を492行から~100行に削減
  - 33ブランチを分散して複雑度を低減
  - 8つの小さなメソッドに分解して保守性向上:
    1. _initialize_run_context() - 初期化
    2. _check_initial_tests() - 初期テスト実行とチェック
    3. _extract_relevant_context() - エラー関連ファイル抽出
    4. _generate_and_validate_patch() - パッチ生成と基本検証
    5. _check_test_file_modifications() - テストファイル変更チェック
    6. _review_patch_with_guardian() - Guardian自動レビュー
    7. _validate_patch_safety() - 危険性チェック (dry-run)
    8. _apply_patch_and_create_summary() - パッチ適用と差分サマリー生成
    9. _retest_and_compute_metrics() - 再テストとメトリクス計算
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
from datetime import UTC
from pathlib import Path
from typing import Any

from nexuscore.agents.patch_applier import PatchApplier
from nexuscore.config.self_healing_config import SelfHealingConfig
from nexuscore.core.diff_preview import summarize_diff_files, wrap_diff_as_markdown
from nexuscore.core.run_history import RunHistoryLogger
from nexuscore.core.session_control import SessionController
from nexuscore.core.stacktrace_mapper import extract_candidate_files
from nexuscore.diff.semantic_diff import compute_semantic_diff

# 4.4: Retry と例外分類
try:
    from nexuscore.core.errors import (
        SandboxExecutionError,
        convert_http_error_to_nexus_error,
    )
    from nexuscore.core.retry_utils import RetryContext
    from nexuscore.core.sandbox_executor import SandboxResult, run_in_sandbox

    HAS_RETRY = True
except ImportError:
    HAS_RETRY = False
    RetryContext = None
    SandboxExecutionError = Exception
    convert_http_error_to_nexus_error = None
    run_in_sandbox = None
    SandboxResult = None


logger = logging.getLogger(__name__)


class RunContext:
    """実行コンテキストを保持する軽量データクラス"""

    def __init__(
        self,
        run_id: str,
        session_id: str,
        repo_full_name: str,
        pr_number: int,
        head_sha: str,
        project_path: Path,
        started_ts: float,
        started_at: float,
        started_at_iso: str,
        retry_context: RetryContext | None,
    ):
        self.run_id = run_id
        self.session_id = session_id
        self.repo_full_name = repo_full_name
        self.pr_number = pr_number
        self.head_sha = head_sha
        self.project_path = project_path
        self.started_ts = started_ts
        self.started_at = started_at
        self.started_at_iso = started_at_iso
        self.retry_context = retry_context


class SelfHealingService:
    """
    GitHub PR を入力として Self-Healing コードレビューを実行するサービス。
    """

    def __init__(
        self,
        project_root: str,
        session_controller: SessionController | None = None,
        debugger_agent: Any = None,
        patch_applier: PatchApplier | None = None,
        history_logger: RunHistoryLogger | None = None,
        config: SelfHealingConfig | None = None,
    ) -> None:
        """
        :param project_root: NexusCore プロジェクトのルート
        :param session_controller: セッション中断/再開制御
        :param debugger_agent: error_log + files -> patch を生成できるエージェント
        :param patch_applier: PatchApplier インスタンス（省略時はデフォルト生成）
        :param history_logger: RunHistoryLogger（省略時は project_root から生成）
        :param config: Self-Healing の挙動を制御する設定。None の場合はデフォルト。
        """
        self.project_root = Path(project_root).resolve()
        self.session_controller = session_controller or SessionController(
            session_id="self_healing_default", root_dir=".nexus/sessions"
        )
        self.debugger_agent = debugger_agent
        self.patch_applier = patch_applier or PatchApplier()
        self.history_logger = history_logger or RunHistoryLogger(str(self.project_root))
        self.config = config or SelfHealingConfig.load(str(self.project_root))

        self.logger = logging.getLogger(self.__class__.__name__)

    # ------------------------------------------------------------------
    # 公開 API (リファクタリング版)
    # ------------------------------------------------------------------
    def run_for_pull_request(
        self,
        *,
        repo_full_name: str,
        pr_number: int,
        head_sha: str,
    ) -> dict[str, Any]:
        """
        指定された PR に対して Self-Healing コードレビューを 1 回実行する (リファクタリング版)。

        主要な改善:
          - 492行 → ~100行に削減
          - 9つの小さなメソッドに分解
          - 各ステップの責任を明確化

        戻り値:
            {
                "status": "fixed" | "not_fixed" | "no_issues" | "error",
                "summary": str,
                "details": {...},
                "run_id": str,
                "session_id": str,
                "started_at": float,
                "finished_at": float,
                "duration_seconds": float,
            }
        """
        try:
            # Step 1: 初期化 (run_id, timestamps, retry context, project_path)
            ctx = self._initialize_run_context(repo_full_name, pr_number, head_sha)
            self._maybe_stop(
                "start",
                {
                    "run_id": ctx.run_id,
                    "repo": repo_full_name,
                    "pr_number": pr_number,
                    "head_sha": head_sha,
                },
            )

            # Step 2: リポジトリ checkout
            self._clone_or_update_repo(
                repo_full_name=repo_full_name,
                pr_number=pr_number,
                head_sha=head_sha,
                target_dir=ctx.project_path,
            )
            self._maybe_stop("after_clone", {"project_path": str(ctx.project_path)})

            # Step 3: 初期テスト実行 (成功なら早期リターン)
            early_return = self._check_initial_tests(ctx)
            if early_return:
                return early_return
            self._maybe_stop("after_initial_tests", {"test_ok": False})

            # Step 4: エラー関連ファイルを抽出
            context_data = self._extract_relevant_context(ctx)
            if not context_data["relevant_files"]:
                return self._build_error_result(
                    ctx, "not_fixed", "No relevant files found for debugging.", context_data
                )

            # Step 5: Patch 生成
            patch_result = self._generate_and_validate_patch(ctx, context_data)
            if not patch_result["success"]:
                return patch_result["result"]
            patch_text = patch_result["patch_text"]
            debug_result = patch_result["debug_result"]
            self._maybe_stop("after_patch_generated", {})

            # Step 6: テストファイル変更チェック
            test_check = self._check_test_file_modifications(
                ctx, patch_text, context_data, debug_result
            )
            if not test_check["allowed"]:
                return test_check["result"]

            # Step 7: Guardian 自動レビュー
            guardian_result = self._review_patch_with_guardian(ctx, patch_text)
            if guardian_result and guardian_result.get("decision") == "REJECT":
                return self._build_rejection_result(
                    ctx, guardian_result, context_data, debug_result, patch_text
                )

            # Step 8: Dry-run 安全性チェック
            safety_check = self._validate_patch_safety(ctx, patch_text, context_data, debug_result)
            if not safety_check["safe"]:
                return safety_check["result"]
            dry_result = safety_check["dry_result"]

            # Step 9: Patch 適用 + 差分サマリー生成
            apply_result, diff_summary = self._apply_patch_and_create_summary(
                ctx, patch_text, guardian_result
            )
            self._maybe_stop("after_patch_apply", {"apply_result": apply_result})

            # Step 10: 再テスト + メトリクス計算 + 最終化
            return self._retest_and_compute_metrics(
                ctx,
                context_data,
                debug_result,
                dry_result,
                apply_result,
                patch_text,
                diff_summary,
                guardian_result,
            )

        except RuntimeError as e:
            if str(e) == "SessionStopped":
                return self._build_session_stopped_result(ctx)
            raise

    # ------------------------------------------------------------------
    # Refactored Private Methods (各ステップを分離)
    # ------------------------------------------------------------------

    def _initialize_run_context(
        self,
        repo_full_name: str,
        pr_number: int,
        head_sha: str,
    ) -> RunContext:
        """
        Step 1: 実行コンテキストの初期化

        Returns:
            RunContext オブジェクト
        """
        from datetime import datetime

        run_id = f"sh-{int(time.time())}-{pr_number}-{head_sha[:7]}"
        session_id = self.session_controller.session_id
        started_ts = time.monotonic()
        started_at = time.time()
        started_at_iso = datetime.now(UTC).isoformat()

        # Retry コンテキスト初期化
        retry_context = RetryContext() if HAS_RETRY and RetryContext else None
        if retry_context:
            if self.debugger_agent and hasattr(self.debugger_agent, "retry_context"):
                self.debugger_agent.retry_context = retry_context
            if (
                hasattr(self, "_guardian_agent")
                and self._guardian_agent
                and hasattr(self._guardian_agent, "retry_context")
            ):
                self._guardian_agent.retry_context = retry_context

        # プロジェクトパス設定
        repo_slug = repo_full_name.replace("/", "_")
        sandbox_root = self.project_root / ".nexus" / "self_healing_sandbox"
        sandbox_root.mkdir(parents=True, exist_ok=True)
        project_path = sandbox_root / f"{repo_slug}_pr_{pr_number}"

        return RunContext(
            run_id=run_id,
            session_id=session_id,
            repo_full_name=repo_full_name,
            pr_number=pr_number,
            head_sha=head_sha,
            project_path=project_path,
            started_ts=started_ts,
            started_at=started_at,
            started_at_iso=started_at_iso,
            retry_context=retry_context,
        )

    def _check_initial_tests(self, ctx: RunContext) -> dict[str, Any] | None:
        """
        Step 2: 初期テスト実行

        Returns:
            テストが成功している場合は早期リターン用の結果 dict、
            失敗している場合は None
        """
        ok, output = self._run_tests(ctx.project_path, retry_context=ctx.retry_context)

        if ok:
            retry_count, last_error_class = self._extract_retry_info(ctx.retry_context)
            return self._finalize(
                run_id=ctx.run_id,
                session_id=ctx.session_id,
                repo_full_name=ctx.repo_full_name,
                pr_number=ctx.pr_number,
                head_sha=ctx.head_sha,
                status="no_issues",
                summary="Tests already passing. No self-healing needed.",
                details={
                    "initial_test_output": output,
                    "retry_count": retry_count,
                    "last_error_class": last_error_class,
                },
                started_at=ctx.started_at,
                started_at_iso=ctx.started_at_iso,
                started_ts=ctx.started_ts,
            )

        # テスト失敗 -> 修復フローに進む
        return None

    def _extract_relevant_context(self, ctx: RunContext) -> dict[str, Any]:
        """
        Step 3: エラー関連ファイルの抽出

        Returns:
            {
                "error_output": str,
                "stacktrace_files": List[str],
                "changed_files": List[str],
                "relevant_files": Dict[str, str],
            }
        """
        ok, output = self._run_tests(ctx.project_path, retry_context=ctx.retry_context)
        stack_files = extract_candidate_files(output)
        changed_files = self._get_changed_files(ctx.project_path, base_ref=None, head_ref=None)
        relevant_files = self._collect_relevant_files(
            project_path=ctx.project_path,
            error_log=output,
            changed_files=changed_files,
            stacktrace_files=stack_files,
        )

        return {
            "error_output": output,
            "stacktrace_files": stack_files,
            "changed_files": changed_files,
            "relevant_files": relevant_files,
        }

    def _generate_and_validate_patch(
        self,
        ctx: RunContext,
        context_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Step 4: Patch 生成と基本検証

        Returns:
            {
                "success": bool,
                "patch_text": str (if success),
                "debug_result": dict (if success),
                "result": dict (if not success, early return用),
            }
        """
        if self.debugger_agent is None:
            retry_count, last_error_class = self._extract_retry_info(ctx.retry_context)
            return {
                "success": False,
                "result": self._finalize(
                    run_id=ctx.run_id,
                    session_id=ctx.session_id,
                    repo_full_name=ctx.repo_full_name,
                    pr_number=ctx.pr_number,
                    head_sha=ctx.head_sha,
                    status="not_fixed",
                    summary="DebuggerAgent not configured. Could not generate patch.",
                    details={
                        "initial_test_output": context_data["error_output"],
                        "stacktrace_files": context_data["stacktrace_files"],
                        "changed_files": context_data["changed_files"],
                        "retry_count": retry_count,
                        "last_error_class": last_error_class,
                    },
                    started_at=ctx.started_at,
                    started_at_iso=ctx.started_at_iso,
                    started_ts=ctx.started_ts,
                ),
            }

        debug_result = self._generate_patch_via_debugger(
            error_log=context_data["error_output"],
            files=context_data["relevant_files"],
            project_path=ctx.project_path,
        )
        patch_text = debug_result.get("patch", "") if isinstance(debug_result, dict) else ""

        if not patch_text.strip():
            retry_count, last_error_class = self._extract_retry_info(ctx.retry_context)
            return {
                "success": False,
                "result": self._finalize(
                    run_id=ctx.run_id,
                    session_id=ctx.session_id,
                    repo_full_name=ctx.repo_full_name,
                    pr_number=ctx.pr_number,
                    head_sha=ctx.head_sha,
                    status="not_fixed",
                    summary="DebuggerAgent did not produce a patch.",
                    details={
                        "initial_test_output": context_data["error_output"],
                        "stacktrace_files": context_data["stacktrace_files"],
                        "changed_files": context_data["changed_files"],
                        "debug_result": debug_result,
                        "retry_count": retry_count,
                        "last_error_class": last_error_class,
                    },
                    started_at=ctx.started_at,
                    started_at_iso=ctx.started_at_iso,
                    started_ts=ctx.started_ts,
                ),
            }

        return {
            "success": True,
            "patch_text": patch_text,
            "debug_result": debug_result,
        }

    def _check_test_file_modifications(
        self,
        ctx: RunContext,
        patch_text: str,
        context_data: dict[str, Any],
        debug_result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Step 5: テストファイル変更チェック

        Returns:
            {
                "allowed": bool,
                "result": dict (if not allowed, early return用),
            }
        """
        patch_changed_files = summarize_diff_files(patch_text)

        def _is_test_path(path: str) -> bool:
            norm = path.replace("\\", "/")
            if norm.startswith("tests/") or "/tests/" in norm:
                return True
            base = norm.rsplit("/", 1)[-1]
            if base.startswith("test_") and base.endswith(".py"):
                return True
            return False

        touched_tests = [p for p in patch_changed_files if _is_test_path(p)]

        if touched_tests and not (self.config and self.config.allow_test_modification):
            return {
                "allowed": False,
                "result": self._finalize(
                    run_id=ctx.run_id,
                    session_id=ctx.session_id,
                    repo_full_name=ctx.repo_full_name,
                    pr_number=ctx.pr_number,
                    head_sha=ctx.head_sha,
                    status="not_fixed",
                    summary="Patch was blocked because it modifies test files. "
                    "Modifying tests is not allowed by current self-healing policy.",
                    details={
                        "initial_test_output": context_data["error_output"],
                        "stacktrace_files": context_data["stacktrace_files"],
                        "changed_files": context_data["changed_files"],
                        "debug_result": debug_result,
                        "patch_preview": wrap_diff_as_markdown(patch_text),
                        "patch_changed_files": patch_changed_files,
                        "blocked_test_paths": touched_tests,
                    },
                    started_at=ctx.started_at,
                    started_at_iso=ctx.started_at_iso,
                    started_ts=ctx.started_ts,
                ),
            }

        return {"allowed": True}

    def _review_patch_with_guardian(
        self,
        ctx: RunContext,
        patch_text: str,
    ) -> dict[str, Any] | None:
        """
        Step 6: Guardian Agent による自動レビュー

        Returns:
            Guardian review result dict (or None if no guardian)
        """
        if not (hasattr(self, "_guardian_agent") and self._guardian_agent is not None):
            return None

        try:
            project_name = "nexuscore"
            if "atelier" in ctx.repo_full_name.lower() or "buyma" in ctx.repo_full_name.lower():
                project_name = "atelier-kyo-manager"

            guardian_review_result = self._guardian_agent.review_unified_diff(
                diff_text=patch_text,
                project_name=project_name,
            )
            self.logger.info(
                f"GuardianAgent auto-review: decision={guardian_review_result.get('decision')}"
            )
            return guardian_review_result
        except Exception as e:
            self.logger.warning(f"GuardianAgent review failed: {e}", exc_info=True)
            return None

    def _validate_patch_safety(
        self,
        ctx: RunContext,
        patch_text: str,
        context_data: dict[str, Any],
        debug_result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Step 7: Dry-run による安全性チェック

        Returns:
            {
                "safe": bool,
                "dry_result": dict,
                "result": dict (if not safe, early return用),
            }
        """
        allow_del = self.config.allow_deletions if self.config else False
        dry_result = self.patch_applier.apply_patch(
            patch_text=patch_text,
            project_path=str(ctx.project_path),
            dry_run=True,
            allow_deletions=allow_del,
        )
        dangerous = bool(dry_result.get("dangerous", False))
        delete_lines = int(dry_result.get("delete_lines", 0))

        if dangerous and not allow_del:
            return {
                "safe": False,
                "dry_result": dry_result,
                "result": self._finalize(
                    run_id=ctx.run_id,
                    session_id=ctx.session_id,
                    repo_full_name=ctx.repo_full_name,
                    pr_number=ctx.pr_number,
                    head_sha=ctx.head_sha,
                    status="not_fixed",
                    summary=f"Patch contains {delete_lines} deleted lines and was blocked by "
                    f"Danger Guard (allow_deletions={allow_del}).",
                    details={
                        "initial_test_output": context_data["error_output"],
                        "stacktrace_files": context_data["stacktrace_files"],
                        "changed_files": context_data["changed_files"],
                        "debug_result": debug_result,
                        "dry_run_result": dry_result,
                        "patch_preview": wrap_diff_as_markdown(patch_text),
                    },
                    started_at=ctx.started_at,
                    started_at_iso=ctx.started_at_iso,
                    started_ts=ctx.started_ts,
                ),
            }

        return {"safe": True, "dry_result": dry_result}

    def _apply_patch_and_create_summary(
        self,
        ctx: RunContext,
        patch_text: str,
        guardian_result: dict[str, Any] | None,
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        """
        Step 8: Patch 適用 + Semantic Diff サマリー生成

        Returns:
            (apply_result, diff_summary)
        """
        allow_del = self.config.allow_deletions if self.config else False
        patch_changed_files = summarize_diff_files(patch_text)

        # パッチ適用前に before コードを取得
        before_code_by_file: dict[str, str] = {}
        for file_path in patch_changed_files:
            full_path = ctx.project_path / file_path
            if full_path.exists():
                try:
                    before_code_by_file[file_path] = full_path.read_text(encoding="utf-8")
                except Exception as e:
                    self.logger.warning(f"Failed to read before code for {file_path}: {e}")

        # Patch 適用
        apply_result = self.patch_applier.apply_patch(
            patch_text=patch_text,
            project_path=str(ctx.project_path),
            dry_run=False,
            allow_deletions=allow_del,
        )

        # パッチ適用後に after コードを取得し、Semantic Diff を生成
        diff_summary = None
        if (
            before_code_by_file
            and hasattr(self, "_guardian_agent")
            and self._guardian_agent is not None
        ):
            try:
                file_diffs: dict[str, dict[str, str]] = {}
                semantic_diffs: dict[str, dict[str, object]] = {}

                for file_path, before_code in before_code_by_file.items():
                    full_path = ctx.project_path / file_path
                    if full_path.exists():
                        after_code = full_path.read_text(encoding="utf-8")
                        file_diffs[file_path] = {"before": before_code, "after": after_code}

                        try:
                            result = compute_semantic_diff(
                                file_path=ctx.project_path / file_path,
                                before_code=before_code,
                                after_code=after_code,
                                language="python",
                            )
                            semantic_diffs[file_path] = result.to_dict()
                        except Exception as exc:
                            self.logger.warning(
                                f"Failed to compute semantic diff for {file_path}: {exc}",
                                exc_info=True,
                            )

                if file_diffs:
                    diff_summary = self._guardian_agent.generate_diff_summary(
                        file_diffs=file_diffs,
                        semantic_diffs=semantic_diffs if semantic_diffs else None,
                        model="gpt-4.1",
                    )
                    self.logger.info(
                        f"Generated diff summary for {len(file_diffs)} files via GuardianAgent"
                    )
            except Exception as e:
                self.logger.warning(f"Failed to generate diff summary: {e}", exc_info=True)

        return apply_result, diff_summary

    def _retest_and_compute_metrics(
        self,
        ctx: RunContext,
        context_data: dict[str, Any],
        debug_result: dict[str, Any],
        dry_result: dict[str, Any],
        apply_result: dict[str, Any],
        patch_text: str,
        diff_summary: dict[str, Any] | None,
        guardian_result: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """
        Step 9: 再テスト + メトリクス計算 + 最終化

        Returns:
            最終的な結果 dict
        """
        ok2, output2 = self._run_tests(ctx.project_path, retry_context=ctx.retry_context)
        self._maybe_stop("after_rerun_tests", {"test_ok_after": ok2})

        status = "fixed" if ok2 else "not_fixed"
        summary = (
            "Self-healing patch applied and tests are now passing."
            if ok2
            else "Patch applied but tests are still failing."
        )

        # メトリクス計算
        finished_ts = time.monotonic()
        duration_seconds = round(finished_ts - ctx.started_ts, 2)
        execution_ms = int(duration_seconds * 1000)
        patch_changed_files = summarize_diff_files(patch_text)
        files_changed = len(patch_changed_files)

        retry_count, last_error_class = self._extract_retry_info(ctx.retry_context)

        details = {
            "initial_test_output": context_data["error_output"],
            "rerun_test_output": output2,
            "stacktrace_files": context_data["stacktrace_files"],
            "changed_files": context_data["changed_files"],
            "debug_result": debug_result,
            "dry_run_result": dry_result,
            "apply_result": apply_result,
            "patch_preview": wrap_diff_as_markdown(patch_text),
            "patch_changed_files": patch_changed_files,
            "execution_ms": execution_ms,
            "retry_count": retry_count,
            "files_changed": files_changed,
            "last_error_class": last_error_class,
        }

        if diff_summary:
            details["diff_summary"] = diff_summary

        if guardian_result:
            details["guardian_review"] = guardian_result
            details["guardian_status"] = guardian_result.get("decision", "unknown")
            auto_review = guardian_result.get("auto_review")
            if auto_review:
                details["guardian_comment"] = auto_review.get("summary", "")
            elif guardian_result.get("reason"):
                details["guardian_comment"] = guardian_result.get("reason")

        return self._finalize(
            run_id=ctx.run_id,
            session_id=ctx.session_id,
            repo_full_name=ctx.repo_full_name,
            pr_number=ctx.pr_number,
            head_sha=ctx.head_sha,
            status=status,
            summary=summary,
            details=details,
            started_at=ctx.started_at,
            started_at_iso=ctx.started_at_iso,
            started_ts=ctx.started_ts,
        )

    # ------------------------------------------------------------------
    # ヘルパーメソッド
    # ------------------------------------------------------------------

    def _extract_retry_info(
        self, retry_context: RetryContext | None
    ) -> tuple[int, str | None]:
        """RetryContext から retry_count と last_error_class を抽出"""
        if not retry_context:
            return 0, None
        retry_info = retry_context.to_dict()
        return retry_info.get("retry_count", 0), retry_info.get("last_error_class")

    def _build_error_result(
        self,
        ctx: RunContext,
        status: str,
        summary: str,
        context_data: dict[str, Any],
    ) -> dict[str, Any]:
        """エラー結果を構築"""
        retry_count, last_error_class = self._extract_retry_info(ctx.retry_context)
        return self._finalize(
            run_id=ctx.run_id,
            session_id=ctx.session_id,
            repo_full_name=ctx.repo_full_name,
            pr_number=ctx.pr_number,
            head_sha=ctx.head_sha,
            status=status,
            summary=summary,
            details={
                "initial_test_output": context_data.get("error_output", ""),
                "stacktrace_files": context_data.get("stacktrace_files", []),
                "changed_files": context_data.get("changed_files", []),
                "retry_count": retry_count,
                "last_error_class": last_error_class,
            },
            started_at=ctx.started_at,
            started_at_iso=ctx.started_at_iso,
            started_ts=ctx.started_ts,
        )

    def _build_rejection_result(
        self,
        ctx: RunContext,
        guardian_result: dict[str, Any],
        context_data: dict[str, Any],
        debug_result: dict[str, Any],
        patch_text: str,
    ) -> dict[str, Any]:
        """Guardian による拒否結果を構築"""
        patch_changed_files = summarize_diff_files(patch_text)
        return self._finalize(
            run_id=ctx.run_id,
            session_id=ctx.session_id,
            repo_full_name=ctx.repo_full_name,
            pr_number=ctx.pr_number,
            head_sha=ctx.head_sha,
            status="not_fixed",
            summary=f"Patch was rejected by GuardianAgent auto-review. "
            f"Reason: {guardian_result.get('reason', 'N/A')}",
            details={
                "initial_test_output": context_data["error_output"],
                "stacktrace_files": context_data["stacktrace_files"],
                "changed_files": context_data["changed_files"],
                "debug_result": debug_result,
                "patch_preview": wrap_diff_as_markdown(patch_text),
                "patch_changed_files": patch_changed_files,
                "guardian_review": guardian_result,
            },
            started_at=ctx.started_at,
            started_at_iso=ctx.started_at_iso,
            started_ts=ctx.started_ts,
        )

    def _build_session_stopped_result(self, ctx: RunContext) -> dict[str, Any]:
        """セッション停止結果を構築"""
        return self._finalize(
            run_id=ctx.run_id,
            session_id=ctx.session_id,
            repo_full_name=ctx.repo_full_name,
            pr_number=ctx.pr_number,
            head_sha=ctx.head_sha,
            status="error",
            summary="Self-healing run was stopped by user request.",
            details={},
            started_at=ctx.started_at,
            started_at_iso=ctx.started_at_iso,
            started_ts=ctx.started_ts,
        )

    # ------------------------------------------------------------------
    # 内部ユーティリティ (既存メソッドは変更なし)
    # ------------------------------------------------------------------
    def _maybe_stop(self, phase: str, meta: dict[str, Any] | None = None) -> None:
        if not self.session_controller:
            return
        try:
            self.session_controller.checkpoint(phase, meta or {})
        except Exception:
            self.logger.exception(f"Failed to checkpoint at phase='{phase}'")
        if self.session_controller.should_stop():
            self.logger.warning(f"Session stop requested at phase='{phase}'.")
            raise RuntimeError("SessionStopped")

    def _clone_or_update_repo(
        self,
        *,
        repo_full_name: str,
        pr_number: int,
        head_sha: str,
        target_dir: Path,
    ) -> None:
        """
        sandbox ディレクトリに対象リポジトリを clone し、指定の head_sha を checkout する。

        優先度:
          1. 環境変数 NEXUS_REPO_BASE_DIR が設定されている場合:
             - そこに {owner}/{repo} が既に clone 済みである前提で、そこからコピーする
          2. それ以外:
             - https://github.com/{repo_full_name}.git を clone する（public repo 想定）

        認証が必要な場合は、NEXUS_GITHUB_CLONE_URL_TEMPLATE を使う:
          例) "https://x-access-token:{TOKEN}@github.com/{repo_full_name}.git"
        """
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.parent.mkdir(parents=True, exist_ok=True)

        base_dir = os.getenv("NEXUS_REPO_BASE_DIR")
        if base_dir:
            from_repo = Path(base_dir) / repo_full_name
            if from_repo.exists():
                self.logger.info(f"Copying existing repo from {from_repo} to sandbox {target_dir}")
                shutil.copytree(from_repo, target_dir)
            else:
                self.logger.warning(
                    f"NEXUS_REPO_BASE_DIR is set but repo {from_repo} does not exist. "
                    f"Falling back to direct clone."
                )

        if not target_dir.exists():
            template = os.getenv("NEXUS_GITHUB_CLONE_URL_TEMPLATE")
            if template:
                if "{repo_full_name}" in template:
                    clone_url = template.format(repo_full_name=repo_full_name)
                else:
                    clone_url = template
            else:
                clone_url = f"https://github.com/{repo_full_name}.git"

            self.logger.info(f"Cloning repo: {clone_url} -> {target_dir}")
            try:
                subprocess.run(
                    ["git", "clone", clone_url, str(target_dir)],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
            except subprocess.CalledProcessError as e:
                self.logger.error(f"git clone failed: {e.stdout}", exc_info=True)
                raise

        try:
            self.logger.info(f"Checking out commit {head_sha} in {target_dir}")
            subprocess.run(
                ["git", "-C", str(target_dir), "checkout", head_sha],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            self.logger.error(f"git checkout {head_sha} failed: {e.stdout}", exc_info=True)
            raise

    def _run_tests(
        self, project_path: Path, retry_context: RetryContext | None = None
    ) -> tuple[bool, str]:
        """
        プロジェクト配下でテストコマンドを実行する。
        デフォルトは pytest。環境変数 NEXUS_SELF_HEALING_TEST_CMD で上書き可能。

        Args:
            project_path: プロジェクトパス
            retry_context: RetryContext インスタンス（retry_count と error_class を記録）

        Returns:
            (成功フラグ, 出力文字列)
        """
        cmd_str = os.getenv("NEXUS_SELF_HEALING_TEST_CMD", "pytest -q")
        self.logger.info(f"Running tests with command: {cmd_str} (cwd={project_path})")

        if HAS_RETRY and run_in_sandbox:
            try:
                cmd_list = cmd_str.split()
                if not cmd_list:
                    cmd_list = ["pytest", "-q"]

                timeout_sec = int(os.getenv("NEXUS_SANDBOX_TIMEOUT_SEC", "300"))
                result: SandboxResult = run_in_sandbox(
                    cmd=cmd_list,
                    timeout_sec=timeout_sec,
                    cwd=str(project_path),
                    retry_on_errors=True,
                )

                if retry_context and result.exception_type:
                    from nexuscore.core.errors import SandboxExecutionError

                    error = SandboxExecutionError(f"Sandbox execution failed: {result.stderr}")
                    retry_context.record_attempt(
                        attempt=0,
                        error=error if result.returncode != 0 else None,
                    )

                success = result.returncode == 0 and not result.timed_out
                output = result.stdout + result.stderr if result.stderr else result.stdout
                return success, output

            except Exception as e:
                msg = f"Exception while running tests: {e}"
                self.logger.error(msg, exc_info=True)
                if retry_context:
                    retry_context.record_attempt(attempt=0, error=e)
                return False, msg
        else:
            try:
                proc = subprocess.run(
                    cmd_str,
                    cwd=str(project_path),
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                output = proc.stdout
                success = proc.returncode == 0
                return success, output
            except Exception as e:
                msg = f"Exception while running tests: {e}"
                self.logger.error(msg, exc_info=True)
                return False, msg

    def _get_changed_files(
        self,
        project_path: Path,
        base_ref: str | None,
        head_ref: str | None,
    ) -> list[str]:
        """
        PR で変更されたファイル一覧を git diff から取得する。

        優先度:
          1. base_ref / head_ref が指定されている場合:
             - git diff --name-only base_ref...head_ref
          2. それ以外:
             - 直近のコミット差分: git diff --name-only HEAD~1..HEAD
        """
        try:
            if base_ref and head_ref:
                diff_range = f"{base_ref}...{head_ref}"
                cmd = ["git", "-C", str(project_path), "diff", "--name-only", diff_range]
            else:
                cmd = ["git", "-C", str(project_path), "diff", "--name-only", "HEAD~1..HEAD"]

            self.logger.info(f"Running git diff to get changed files: {' '.join(cmd)}")
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )

            if proc.returncode != 0:
                self.logger.warning(f"git diff failed (code={proc.returncode}): {proc.stderr}")
                return []

            files: list[str] = []
            for line in proc.stdout.splitlines():
                path = line.strip()
                if path:
                    files.append(path)

            return files
        except Exception as e:
            self.logger.error(f"_get_changed_files failed: {e}", exc_info=True)
            return []

    def _collect_relevant_files(
        self,
        *,
        project_path: Path,
        error_log: str,
        changed_files: list[str],
        stacktrace_files: list[str],
    ) -> dict[str, str]:
        """
        DebuggerAgent に渡す対象ファイルの内容を集める。

        優先度:
          1. stacktrace_files
          2. changed_files
        """
        candidates: list[str] = []
        for path in stacktrace_files:
            if path not in candidates:
                candidates.append(path)
        for path in changed_files:
            if path not in candidates:
                candidates.append(path)

        files_dict: dict[str, str] = {}

        for p in candidates:
            abs_path = Path(p)
            if not abs_path.is_absolute():
                abs_path = project_path / p
            if not abs_path.exists():
                alt = project_path / p
                if alt.exists():
                    abs_path = alt
                else:
                    continue

            try:
                content = abs_path.read_text(encoding="utf-8", errors="ignore")
                rel = str(abs_path.relative_to(project_path))
                files_dict[rel] = content
            except Exception:
                continue

        if not files_dict:
            for py in project_path.rglob("*.py"):
                try:
                    content = py.read_text(encoding="utf-8", errors="ignore")
                    rel = str(py.relative_to(project_path))
                    files_dict[rel] = content
                except Exception:
                    continue
                if len(files_dict) >= 10:
                    break

        return files_dict

    def _generate_patch_via_debugger(
        self,
        error_log: str,
        files: dict[str, str],
        project_path: Path,
    ) -> dict[str, Any]:
        """
        DebuggerAgent にエラーとファイル情報を渡して patch を生成させる。

        優先的に DebuggerAgent.debug_and_patch(...) を呼び、
        それが無い場合のみ generate_patch(...) にフォールバックする。
        """
        if not self.debugger_agent:
            self.logger.warning("DebuggerAgent is not configured.")
            return {}

        try:
            if hasattr(self.debugger_agent, "debug_and_patch"):
                return self.debugger_agent.debug_and_patch(
                    error_log=error_log,
                    files_content=files,
                    project_path=str(project_path),
                )

            if hasattr(self.debugger_agent, "generate_patch"):
                return self.debugger_agent.generate_patch(
                    error_log=error_log,
                    files=files,
                )

            self.logger.warning("DebuggerAgent has neither 'debug_and_patch' nor 'generate_patch'.")
            return {}
        except Exception as e:
            self.logger.error(
                f"DebuggerAgent call failed: {e}",
                exc_info=True,
            )
            return {}

    def _finalize(
        self,
        *,
        run_id: str,
        session_id: str,
        repo_full_name: str,
        pr_number: int,
        head_sha: str,
        status: str,
        summary: str,
        details: dict[str, Any],
        started_at: float,
        started_at_iso: str | None = None,
        started_ts: float | None = None,
    ) -> dict[str, Any]:
        """
        RunHistoryLogger への記録と戻り値 dict の生成をまとめる。
        """
        from datetime import datetime

        finished_at = time.time()
        finished_at_iso = datetime.now(UTC).isoformat()

        if started_ts is not None:
            finished_ts = time.monotonic()
            duration_seconds = round(finished_ts - started_ts, 2)
        else:
            duration_seconds = round(finished_at - started_at, 2)

        if started_at_iso is None:
            started_at_iso = datetime.fromtimestamp(started_at, tz=UTC).isoformat()

        try:
            record = self.history_logger.new_self_healing_record(
                run_id=run_id,
                session_id=session_id,
                repo_full_name=repo_full_name,
                pr_number=pr_number,
                head_sha=head_sha,
                status=status,
                summary=summary,
                details=details,
                started_at=started_at,
                finished_at=finished_at,
            )
            self.history_logger.log_run(record)
        except Exception:
            self.logger.exception("Failed to log self-healing run history.")

        # Run レポート生成 (optional)
        try:
            from nexuscore.integration.run_report_generator import write_run_report_file
            from nexuscore.webapp.models import Run

            run = Run.query.filter_by(run_id=run_id).first()
            if run and hasattr(run, "id"):
                report_path = write_run_report_file(run.id, base_dir=self.project_root)
                self.logger.info(f"Run report generated: {report_path}")
        except ImportError:
            pass
        except Exception as e:
            self.logger.warning(f"Failed to generate run report: {e}", exc_info=True)

        return {
            "status": status,
            "summary": summary,
            "details": details,
            "run_id": run_id,
            "session_id": session_id,
            "started_at": started_at,
            "started_at_iso": started_at_iso,
            "finished_at": finished_at,
            "finished_at_iso": finished_at_iso,
            "duration_seconds": duration_seconds,
        }
