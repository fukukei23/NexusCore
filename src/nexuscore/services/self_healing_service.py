"""
self_healing_service.py

Self-Healing Code Review MVP のオーケストレーターサービス。

実際の処理は以下のモジュールに委譲:
  - git_operations: リポジトリの clone / checkout
  - test_runner: テストコマンド実行（sandbox + retry 対応）
  - patch_workflow: パッチ生成・検証・Guardian review

本モジュールは全体のワークフロー制御と結果記録のみを担当。
"""

from __future__ import annotations

import logging
import time
from datetime import UTC
from pathlib import Path
from typing import Any

from nexuscore.config.self_healing_config import SelfHealingConfig
from nexuscore.core.diff_preview import summarize_diff_files, wrap_diff_as_markdown
from nexuscore.core.run_history import RunHistoryLogger
from nexuscore.core.session_control import SessionController
from nexuscore.core.stacktrace_mapper import extract_candidate_files
from nexuscore.services.git_operations import clone_or_update_repo, get_changed_files
from nexuscore.services.patch_applier import PatchApplier
from nexuscore.services.patch_workflow import (
    check_dry_run,
    check_test_modification,
    collect_relevant_files,
    generate_diff_summary,
    generate_patch_via_debugger,
    run_guardian_review,
)
from nexuscore.services.test_runner import run_tests

try:
    from nexuscore.core.retry_utils import RetryContext

    HAS_RETRY = True
except ImportError:
    HAS_RETRY = False
    RetryContext = None


logger = logging.getLogger(__name__)


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
    # 公開 API
    # ------------------------------------------------------------------
    def run_for_pull_request(
        self,
        *,
        repo_full_name: str,
        pr_number: int,
        head_sha: str,
    ) -> dict[str, Any]:
        """
        指定された PR に対して Self-Healing コードレビューを 1 回実行する。
        """
        from datetime import datetime

        run_id = f"sh-{int(time.time())}-{pr_number}-{head_sha[:7]}"
        session_id = self.session_controller.session_id

        started_ts = time.monotonic()
        started_at_iso = datetime.now(UTC).isoformat()
        started_at = time.time()

        retry_context = RetryContext() if HAS_RETRY and RetryContext else None
        self._inject_retry_context(retry_context)

        repo_slug = repo_full_name.replace("/", "_")
        sandbox_root = self.project_root / ".nexus" / "self_healing_sandbox"
        sandbox_root.mkdir(parents=True, exist_ok=True)
        project_path = sandbox_root / f"{repo_slug}_pr_{pr_number}"

        try:
            self._maybe_stop(
                "start",
                {"run_id": run_id, "repo": repo_full_name, "pr_number": pr_number, "head_sha": head_sha},
            )

            # 1. リポジトリ checkout / update
            clone_or_update_repo(
                repo_full_name=repo_full_name,
                pr_number=pr_number,
                head_sha=head_sha,
                target_dir=project_path,
            )
            self._maybe_stop("after_clone", {"project_path": str(project_path)})

            # 2. 既存テスト実行
            ok, output = run_tests(project_path, retry_context=retry_context)
            self._maybe_stop("after_initial_tests", {"test_ok": ok})

            if ok:
                return self._finalize(
                    run_id=run_id, session_id=session_id, repo_full_name=repo_full_name,
                    pr_number=pr_number, head_sha=head_sha,
                    status="no_issues", summary="Tests already passing. No self-healing needed.",
                    details={"initial_test_output": output, **self._retry_info(retry_context)},
                    started_at=started_at, started_at_iso=started_at_iso, started_ts=started_ts,
                )

            # 3. 失敗ログから関連ファイル候補を抽出
            stack_files = extract_candidate_files(output)
            changed_files = get_changed_files(project_path, base_ref=None, head_ref=None)

            # 4. DebuggerAgent に渡すファイル集合を決定
            relevant_files = collect_relevant_files(
                project_path=project_path,
                error_log=output,
                changed_files=changed_files,
                stacktrace_files=stack_files,
            )

            # 5. DebuggerAgent で patch を生成
            if self.debugger_agent is None:
                self.logger.warning("DebuggerAgent is not provided. Skipping patch generation.")
                return self._finalize(
                    run_id=run_id, session_id=session_id, repo_full_name=repo_full_name,
                    pr_number=pr_number, head_sha=head_sha,
                    status="not_fixed", summary="DebuggerAgent not configured. Could not generate patch.",
                    details={
                        "initial_test_output": output,
                        "stacktrace_files": stack_files,
                        "changed_files": changed_files,
                        **self._retry_info(retry_context),
                    },
                    started_at=started_at, started_at_iso=started_at_iso, started_ts=started_ts,
                )

            debug_result = generate_patch_via_debugger(
                self.debugger_agent, output, relevant_files, project_path,
            )
            patch_text = debug_result.get("patch", "") if isinstance(debug_result, dict) else ""

            if not patch_text.strip():
                return self._finalize(
                    run_id=run_id, session_id=session_id, repo_full_name=repo_full_name,
                    pr_number=pr_number, head_sha=head_sha,
                    status="not_fixed", summary="DebuggerAgent did not produce a patch.",
                    details={
                        "initial_test_output": output,
                        "stacktrace_files": stack_files,
                        "changed_files": changed_files,
                        "debug_result": debug_result,
                        **self._retry_info(retry_context),
                    },
                    started_at=started_at, started_at_iso=started_at_iso, started_ts=started_ts,
                )

            self._maybe_stop("after_patch_generated", {})

            # 6-A. tests/ への変更チェック
            blocked, block_summary, touched_tests = check_test_modification(patch_text, self.config)
            if blocked:
                return self._finalize(
                    run_id=run_id, session_id=session_id, repo_full_name=repo_full_name,
                    pr_number=pr_number, head_sha=head_sha,
                    status="not_fixed", summary=block_summary,
                    details={
                        "initial_test_output": output,
                        "stacktrace_files": stack_files,
                        "changed_files": changed_files,
                        "debug_result": debug_result,
                        "patch_preview": wrap_diff_as_markdown(patch_text),
                        "patch_changed_files": summarize_diff_files(patch_text),
                        "blocked_test_paths": touched_tests,
                    },
                    started_at=started_at, started_at_iso=started_at_iso, started_ts=started_ts,
                )

            # 6-B. GuardianAgent による自動レビュー
            guardian_review_result = run_guardian_review(
                patch_text, repo_full_name, getattr(self, "_guardian_agent", None),
            )

            if guardian_review_result and guardian_review_result.get("decision") == "REJECT":
                return self._finalize(
                    run_id=run_id, session_id=session_id, repo_full_name=repo_full_name,
                    pr_number=pr_number, head_sha=head_sha,
                    status="not_fixed",
                    summary=f"Patch was rejected by GuardianAgent auto-review. "
                            f"Reason: {guardian_review_result.get('reason', 'N/A')}",
                    details={
                        "initial_test_output": output,
                        "stacktrace_files": stack_files,
                        "changed_files": changed_files,
                        "debug_result": debug_result,
                        "patch_preview": wrap_diff_as_markdown(patch_text),
                        "patch_changed_files": summarize_diff_files(patch_text),
                        "guardian_review": guardian_review_result,
                    },
                    started_at=started_at, started_at_iso=started_at_iso, started_ts=started_ts,
                )

            # 6-C. Dry-Run 安全性チェック
            dry_blocked, dry_summary, dry_result = check_dry_run(
                patch_text, str(project_path), self.patch_applier, self.config,
            )
            if dry_blocked:
                return self._finalize(
                    run_id=run_id, session_id=session_id, repo_full_name=repo_full_name,
                    pr_number=pr_number, head_sha=head_sha,
                    status="not_fixed", summary=dry_summary,
                    details={
                        "initial_test_output": output,
                        "stacktrace_files": stack_files,
                        "changed_files": changed_files,
                        "debug_result": debug_result,
                        "dry_run_result": dry_result,
                        "patch_preview": wrap_diff_as_markdown(patch_text),
                    },
                    started_at=started_at, started_at_iso=started_at_iso, started_ts=started_ts,
                )

            # 7. パッチ適用
            allow_del = self.config.allow_deletions if self.config else False
            apply_result = self.patch_applier.apply_patch(
                patch_text=patch_text,
                project_path=str(project_path),
                dry_run=False,
                allow_deletions=allow_del,
            )
            self._maybe_stop("after_patch_apply", {"apply_result": apply_result})

            # E-5: Semantic Diff 生成
            guardian_agent = getattr(self, "_guardian_agent", None)
            diff_summary = generate_diff_summary(patch_text, project_path, guardian_agent)

            # 8. 再テスト
            ok2, output2 = run_tests(project_path, retry_context=retry_context)
            self._maybe_stop("after_rerun_tests", {"test_ok_after": ok2})

            if ok2:
                status = "fixed"
                summary = "Self-healing patch applied and tests are now passing."
            else:
                status = "not_fixed"
                summary = "Patch applied but tests are still failing."

            finished_ts = time.monotonic()
            duration_seconds = round(finished_ts - started_ts, 2) if started_ts else None
            execution_ms = int(duration_seconds * 1000) if duration_seconds else None

            patch_changed_files = summarize_diff_files(patch_text)
            retry_info = self._retry_info(retry_context)

            details: dict[str, Any] = {
                "initial_test_output": output,
                "rerun_test_output": output2,
                "stacktrace_files": stack_files,
                "changed_files": changed_files,
                "debug_result": debug_result,
                "dry_run_result": dry_result,
                "apply_result": apply_result,
                "patch_preview": wrap_diff_as_markdown(patch_text),
                "patch_changed_files": patch_changed_files,
                "execution_ms": execution_ms,
                "files_changed": len(patch_changed_files),
                **retry_info,
            }

            if diff_summary:
                details["diff_summary"] = diff_summary

            if guardian_agent and hasattr(guardian_agent, "model") and guardian_agent.model:
                details["model"] = guardian_agent.model

            if guardian_review_result:
                details["guardian_review"] = guardian_review_result
                details["guardian_status"] = guardian_review_result.get("decision", "unknown")
                auto_review = guardian_review_result.get("auto_review")
                if auto_review:
                    details["guardian_comment"] = auto_review.get("summary", "")
                elif guardian_review_result.get("reason"):
                    details["guardian_comment"] = guardian_review_result.get("reason")

            return self._finalize(
                run_id=run_id, session_id=session_id, repo_full_name=repo_full_name,
                pr_number=pr_number, head_sha=head_sha,
                status=status, summary=summary, details=details,
                started_at=started_at,
            )

        except RuntimeError as e:
            if str(e) == "SessionStopped":
                return self._finalize(
                    run_id=run_id, session_id=session_id, repo_full_name=repo_full_name,
                    pr_number=pr_number, head_sha=head_sha,
                    status="error", summary="Self-healing run was stopped by user request.",
                    details={},
                    started_at=started_at, started_at_iso=started_at_iso, started_ts=started_ts,
                )
            raise

    # ------------------------------------------------------------------
    # 内部ユーティリティ
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

    def _inject_retry_context(self, retry_context: Any | None) -> None:
        if not retry_context:
            return
        if self.debugger_agent and hasattr(self.debugger_agent, "retry_context"):
            self.debugger_agent.retry_context = retry_context
        guardian = getattr(self, "_guardian_agent", None)
        if guardian and hasattr(guardian, "retry_context"):
            guardian.retry_context = retry_context

    def _retry_info(self, retry_context: Any | None) -> dict[str, Any]:
        if not retry_context:
            return {"retry_count": 0, "last_error_class": None}
        info = retry_context.to_dict()
        return {
            "retry_count": info.get("retry_count", 0),
            "last_error_class": info.get("last_error_class"),
        }

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
                run_id=run_id, session_id=session_id, repo_full_name=repo_full_name,
                pr_number=pr_number, head_sha=head_sha, status=status,
                summary=summary, details=details,
                started_at=started_at, finished_at=finished_at,
            )
            self.history_logger.log_run(record)
        except Exception:
            self.logger.exception("Failed to log self-healing run history.")

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
