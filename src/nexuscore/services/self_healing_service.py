"""
self_healing_service.py

Self-Healing Code Review MVP のオーケストレーターサービス。

実際の処理は以下のモジュールに委譲:
  - git_operations: リポジトリの clone / checkout
  - test_runner: テストコマンド実行（sandbox + retry 対応）
  - patch_workflow: パッチ生成・検証・Guardian review
  - _finalize: 結果記録・セッション制御
  - _validation: 検証ゲート（test modification / guardian / dry-run）

本モジュールは全体のワークフロー制御のみを担当。
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
    collect_relevant_files,
    generate_diff_summary,
    generate_patch_via_debugger,
)
from nexuscore.services.self_healing._finalize import (
    finalize_run,
    inject_retry_context,
    maybe_stop,
    retry_info,
)
from nexuscore.services.self_healing._validation import (
    validate_dry_run,
    validate_guardian_review,
    validate_test_modification,
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

        retry_ctx = RetryContext() if HAS_RETRY and RetryContext else None
        inject_retry_context(self.debugger_agent, getattr(self, "_guardian_agent", None), retry_ctx)

        # Sandbox setup
        repo_slug = repo_full_name.replace("/", "_")
        sandbox_root = self.project_root / ".nexus" / "self_healing_sandbox"
        sandbox_root.mkdir(parents=True, exist_ok=True)
        project_path = sandbox_root / f"{repo_slug}_pr_{pr_number}"

        # Common kwargs for _finalize calls
        fk = dict(
            run_id=run_id, session_id=session_id, repo_full_name=repo_full_name,
            pr_number=pr_number, head_sha=head_sha,
        )
        time_kw = dict(started_at=started_at, started_at_iso=started_at_iso, started_ts=started_ts)
        ri = retry_info(retry_ctx)

        try:
            maybe_stop(self.session_controller, self.logger, "start",
                       {"run_id": run_id, "repo": repo_full_name, "pr_number": pr_number, "head_sha": head_sha})

            # 1. Clone / update
            clone_or_update_repo(
                repo_full_name=repo_full_name, pr_number=pr_number,
                head_sha=head_sha, target_dir=project_path,
            )
            maybe_stop(self.session_controller, self.logger, "after_clone", {"project_path": str(project_path)})

            # 2. Initial tests
            ok, output = run_tests(project_path, retry_context=retry_ctx)
            maybe_stop(self.session_controller, self.logger, "after_initial_tests", {"test_ok": ok})

            if ok:
                return self._finalize(
                    status="no_issues", summary="Tests already passing. No self-healing needed.",
                    details={"initial_test_output": output, **ri}, **fk, **time_kw,
                )

            # 3. Analyze failures
            stack_files = extract_candidate_files(output)
            changed_files = get_changed_files(project_path, base_ref=None, head_ref=None)

            relevant_files = collect_relevant_files(
                project_path=project_path, error_log=output,
                changed_files=changed_files, stacktrace_files=stack_files,
            )

            # 4. Generate patch
            if self.debugger_agent is None:
                self.logger.warning("DebuggerAgent is not provided. Skipping patch generation.")
                return self._finalize(
                    status="not_fixed", summary="DebuggerAgent not configured. Could not generate patch.",
                    details={"initial_test_output": output, "stacktrace_files": stack_files,
                             "changed_files": changed_files, **ri},
                    **fk, **time_kw,
                )

            debug_result = generate_patch_via_debugger(
                self.debugger_agent, output, relevant_files, project_path,
            )
            patch_text = debug_result.get("patch", "") if isinstance(debug_result, dict) else ""

            if not patch_text.strip():
                return self._finalize(
                    status="not_fixed", summary="DebuggerAgent did not produce a patch.",
                    details={"initial_test_output": output, "stacktrace_files": stack_files,
                             "changed_files": changed_files, "debug_result": debug_result, **ri},
                    **fk, **time_kw,
                )

            maybe_stop(self.session_controller, self.logger, "after_patch_generated", {})

            # 5. Validation gates
            base_ctx = {
                "initial_test_output": output, "stacktrace_files": stack_files,
                "changed_files": changed_files, "debug_result": debug_result,
            }

            blocked, gate_result = validate_test_modification(patch_text, self.config, base_ctx.copy())
            if blocked:
                return self._finalize(**gate_result, **fk, **time_kw)

            blocked, gate_result = validate_guardian_review(
                patch_text, repo_full_name, getattr(self, "_guardian_agent", None), base_ctx,
            )
            if blocked:
                return self._finalize(**gate_result, **fk, **time_kw)
            guardian_review_result = base_ctx.pop("guardian_review_result", None)

            blocked, gate_result = validate_dry_run(
                patch_text, str(project_path), self.patch_applier, self.config, base_ctx,
            )
            if blocked:
                return self._finalize(**gate_result, **fk, **time_kw)
            dry_result = base_ctx.pop("dry_result", None)

            # 6. Apply patch
            allow_del = self.config.allow_deletions if self.config else False
            apply_result = self.patch_applier.apply_patch(
                patch_text=patch_text, project_path=str(project_path),
                dry_run=False, allow_deletions=allow_del,
            )
            maybe_stop(self.session_controller, self.logger, "after_patch_apply", {"apply_result": apply_result})

            # 7. Semantic diff
            guardian_agent = getattr(self, "_guardian_agent", None)
            diff_summary = generate_diff_summary(patch_text, project_path, guardian_agent)

            # 8. Re-run tests
            ok2, output2 = run_tests(project_path, retry_context=retry_ctx)
            maybe_stop(self.session_controller, self.logger, "after_rerun_tests", {"test_ok_after": ok2})

            status = "fixed" if ok2 else "not_fixed"
            summary = "Self-healing patch applied and tests are now passing." if ok2 else "Patch applied but tests are still failing."

            finished_ts = time.monotonic()
            duration_seconds = round(finished_ts - started_ts, 2) if started_ts else None
            execution_ms = int(duration_seconds * 1000) if duration_seconds else None

            patch_changed_files = summarize_diff_files(patch_text)

            details: dict[str, Any] = {
                "initial_test_output": output, "rerun_test_output": output2,
                "stacktrace_files": stack_files, "changed_files": changed_files,
                "debug_result": debug_result, "dry_run_result": dry_result,
                "apply_result": apply_result,
                "patch_preview": wrap_diff_as_markdown(patch_text),
                "patch_changed_files": patch_changed_files,
                "execution_ms": execution_ms,
                "files_changed": len(patch_changed_files),
                **ri,
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
                status=status, summary=summary, details=details,
                **fk, started_at=started_at,
            )

        except RuntimeError as e:
            if str(e) == "SessionStopped":
                return self._finalize(
                    status="error", summary="Self-healing run was stopped by user request.",
                    details={}, **fk, **time_kw,
                )
            raise

    # ------------------------------------------------------------------
    # Internal — delegates to _finalize module
    # ------------------------------------------------------------------
    def _finalize(self, *, status, summary, details, run_id, session_id,
                  repo_full_name, pr_number, head_sha, started_at,
                  started_at_iso=None, started_ts=None) -> dict[str, Any]:
        return finalize_run(
            logger=self.logger,
            history_logger=self.history_logger,
            project_root=self.project_root,
            run_id=run_id, session_id=session_id,
            repo_full_name=repo_full_name, pr_number=pr_number, head_sha=head_sha,
            status=status, summary=summary, details=details,
            started_at=started_at, started_at_iso=started_at_iso, started_ts=started_ts,
        )

    def _maybe_stop(self, phase: str, meta: dict[str, Any] | None = None) -> None:
        maybe_stop(self.session_controller, self.logger, phase, meta)

    def _inject_retry_context(self, retry_context: Any | None) -> None:
        inject_retry_context(self.debugger_agent, getattr(self, "_guardian_agent", None), retry_context)

    def _retry_info(self, retry_context: Any | None) -> dict[str, Any]:
        return retry_info(retry_context)
