"""
self_healing_service.py

Self-Healing Code Review MVP の本体サービス。

想定フロー:
  1. GitHub PR イベントから repo_full_name / pr_number / head_sha を受け取る
  2. リポジトリを sandbox ディレクトリに checkout
  3. 既存テストを実行
  4. 失敗していれば:
       - error_log から stacktrace 上のファイルを抽出
       - PR の変更ファイルと組み合わせて「関連度の高いファイル集合」を作る
       - DebuggerAgent に error_log + files を渡して patch を生成
       - PatchApplier (dry-run) で危険度チェック
       - 問題なければ patch を実適用して再テスト
  5. 結果を RunHistoryLogger に記録し、呼び出し元に dict で返す
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from nexuscore.core.session_control import SessionController
from nexuscore.core.run_history import RunHistoryLogger
from nexuscore.core.diff_preview import wrap_diff_as_markdown, summarize_diff_files
from nexuscore.core.stacktrace_mapper import extract_candidate_files
from nexuscore.agents.patch_applier import PatchApplier
from nexuscore.config.self_healing_config import SelfHealingConfig

# 4.4: Retry と例外分類
try:
    from nexuscore.core.retry_utils import RetryContext
    from nexuscore.core.errors import (
        SandboxExecutionError,
        convert_http_error_to_nexus_error,
    )
    from nexuscore.core.sandbox_executor import run_in_sandbox, SandboxResult
    HAS_RETRY = True
except ImportError:
    HAS_RETRY = False
    RetryContext = None  # type: ignore
    SandboxExecutionError = Exception  # type: ignore
    convert_http_error_to_nexus_error = None  # type: ignore
    run_in_sandbox = None  # type: ignore
    SandboxResult = None  # type: ignore


logger = logging.getLogger(__name__)


class SelfHealingService:
    """
    GitHub PR を入力として Self-Healing コードレビューを実行するサービス。
    """

    def __init__(
        self,
        project_root: str,
        session_controller: Optional[SessionController] = None,
        debugger_agent: Any = None,
        patch_applier: Optional[PatchApplier] = None,
        history_logger: Optional[RunHistoryLogger] = None,
        config: Optional[SelfHealingConfig] = None,
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
    # 公開 API
    # ------------------------------------------------------------------
    def run_for_pull_request(
        self,
        *,
        repo_full_name: str,
        pr_number: int,
        head_sha: str,
    ) -> Dict[str, Any]:
        """
        指定された PR に対して Self-Healing コードレビューを 1 回実行する。

        戻り値:
            {
                "status": "fixed" | "not_fixed" | "no_issues" | "error",
                "summary": str,
                "details": {...},
                "run_id": str,
                "session_id": str,
                "started_at": float,
                "finished_at": float,
            }
        """
        # 実行時間の記録開始
        import time
        from datetime import datetime, timezone

        run_id = f"sh-{int(time.time())}-{pr_number}-{head_sha[:7]}"
        session_id = self.session_controller.session_id

        started_ts = time.monotonic()
        started_at_iso = datetime.now(timezone.utc).isoformat()
        started_at = time.time()

        # 4.4: Retry コンテキストを初期化（全ステップで共有）
        retry_context = RetryContext() if HAS_RETRY and RetryContext else None

        # 4.4: エージェントに retry_context を設定
        if retry_context:
            if self.debugger_agent and hasattr(self.debugger_agent, "retry_context"):
                self.debugger_agent.retry_context = retry_context
            if hasattr(self, "_guardian_agent") and self._guardian_agent and hasattr(self._guardian_agent, "retry_context"):
                self._guardian_agent.retry_context = retry_context

        repo_slug = repo_full_name.replace("/", "_")
        sandbox_root = self.project_root / ".nexus" / "self_healing_sandbox"
        sandbox_root.mkdir(parents=True, exist_ok=True)
        project_path = sandbox_root / f"{repo_slug}_pr_{pr_number}"

        try:
            self._maybe_stop(
                "start",
                {
                    "run_id": run_id,
                    "repo": repo_full_name,
                    "pr_number": pr_number,
                    "head_sha": head_sha,
                },
            )

            # 1. リポジトリ checkout / update
            self._clone_or_update_repo(
                repo_full_name=repo_full_name,
                pr_number=pr_number,
                head_sha=head_sha,
                target_dir=project_path,
            )
            self._maybe_stop("after_clone", {"project_path": str(project_path)})

            # 2. 既存テスト実行（4.4: Retry 対応）
            ok, output = self._run_tests(project_path, retry_context=retry_context)
            self._maybe_stop("after_initial_tests", {"test_ok": ok})

            if ok:
                status = "no_issues"
                summary = "Tests already passing. No self-healing needed."
                # 4.4: RetryContext から情報を取得
                retry_count = 0
                last_error_class = None
                if retry_context:
                    retry_info = retry_context.to_dict()
                    retry_count = retry_info.get("retry_count", 0)
                    last_error_class = retry_info.get("last_error_class")
                details = {
                    "initial_test_output": output,
                    "retry_count": retry_count,
                    "last_error_class": last_error_class,
                }
                return self._finalize(
                    run_id=run_id,
                    session_id=session_id,
                    repo_full_name=repo_full_name,
                    pr_number=pr_number,
                    head_sha=head_sha,
                    status=status,
                    summary=summary,
                    details=details,
                    started_at=started_at,
                    started_at_iso=started_at_iso,
                    started_ts=started_ts,
                )

            # 3. 失敗ログから関連ファイル候補を抽出
            stack_files = extract_candidate_files(output)

            # PR で変更されたファイル一覧（TODO: 実際は GitHub API / git 連携で実装）
            changed_files = self._get_changed_files(project_path, base_ref=None, head_ref=None)

            # 4. DebuggerAgent に渡すファイル集合を決定
            relevant_files = self._collect_relevant_files(
                project_path=project_path,
                error_log=output,
                changed_files=changed_files,
                stacktrace_files=stack_files,
            )

            # 5. DebuggerAgent で patch を生成
            if self.debugger_agent is None:
                self.logger.warning("DebuggerAgent is not provided. Skipping patch generation.")
                status = "not_fixed"
                summary = "DebuggerAgent not configured. Could not generate patch."
                # 4.4: RetryContext から情報を取得
                retry_count = 0
                last_error_class = None
                if retry_context:
                    retry_info = retry_context.to_dict()
                    retry_count = retry_info.get("retry_count", 0)
                    last_error_class = retry_info.get("last_error_class")
                details = {
                    "initial_test_output": output,
                    "stacktrace_files": stack_files,
                    "changed_files": changed_files,
                    "retry_count": retry_count,
                    "last_error_class": last_error_class,
                }
                return self._finalize(
                    run_id=run_id,
                    session_id=session_id,
                    repo_full_name=repo_full_name,
                    pr_number=pr_number,
                    head_sha=head_sha,
                    status=status,
                    summary=summary,
                    details=details,
                    started_at=started_at,
                    started_at_iso=started_at_iso,
                    started_ts=started_ts,
                )

            # ★ project_path を渡すように変更
            debug_result = self._generate_patch_via_debugger(
                error_log=output,
                files=relevant_files,
                project_path=project_path,
            )
            patch_text = debug_result.get("patch", "") if isinstance(debug_result, dict) else ""

            if not patch_text.strip():
                status = "not_fixed"
                summary = "DebuggerAgent did not produce a patch."
                # 4.4: RetryContext から情報を取得
                retry_count = 0
                last_error_class = None
                if retry_context:
                    retry_info = retry_context.to_dict()
                    retry_count = retry_info.get("retry_count", 0)
                    last_error_class = retry_info.get("last_error_class")
                details = {
                    "initial_test_output": output,
                    "stacktrace_files": stack_files,
                    "changed_files": changed_files,
                    "debug_result": debug_result,
                    "retry_count": retry_count,
                    "last_error_class": last_error_class,
                }
                return self._finalize(
                    run_id=run_id,
                    session_id=session_id,
                    repo_full_name=repo_full_name,
                    pr_number=pr_number,
                    head_sha=head_sha,
                    status=status,
                    summary=summary,
                    details=details,
                    started_at=started_at,
                    started_at_iso=started_at_iso,
                    started_ts=started_ts,
                )

            self._maybe_stop("after_patch_generated", {})

            # ▼ 6-A. tests/ への変更が含まれていないかチェック
            patch_changed_files = summarize_diff_files(patch_text)

            def _is_test_path(path: str) -> bool:
                # シンプルな基準: tests/ 配下、または test_*.py
                norm = path.replace("\\", "/")
                if norm.startswith("tests/") or "/tests/" in norm:
                    return True
                base = norm.rsplit("/", 1)[-1]
                if base.startswith("test_") and base.endswith(".py"):
                    return True
                return False

            touched_tests = [p for p in patch_changed_files if _is_test_path(p)]

            if touched_tests and not (self.config and self.config.allow_test_modification):
                # tests/ に触るパッチは Danger Guard とは別レイヤーでブロック
                status = "not_fixed"
                summary = (
                    "Patch was blocked because it modifies test files. "
                    "Modifying tests is not allowed by current self-healing policy."
                )
                details = {
                    "initial_test_output": output,
                    "stacktrace_files": stack_files,
                    "changed_files": changed_files,
                    "debug_result": debug_result,
                    "patch_preview": wrap_diff_as_markdown(patch_text),
                    "patch_changed_files": patch_changed_files,
                    "blocked_test_paths": touched_tests,
                }
                return self._finalize(
                    run_id=run_id,
                    session_id=session_id,
                    repo_full_name=repo_full_name,
                    pr_number=pr_number,
                    head_sha=head_sha,
                    status=status,
                    summary=summary,
                    details=details,
                    started_at=started_at,
                    started_at_iso=started_at_iso,
                    started_ts=started_ts,
                )

            # ▼ 6-B. GuardianAgent による自動レビュー（パッチ生成後、適用前）
            guardian_review_result = None
            if hasattr(self, "_guardian_agent") and self._guardian_agent is not None:
                try:
                    # project_name を決定（repo_full_name から推測、またはデフォルト）
                    project_name = "nexuscore"
                    if "atelier" in repo_full_name.lower() or "buyma" in repo_full_name.lower():
                        project_name = "atelier-kyo-manager"

                    guardian_review_result = self._guardian_agent.review_unified_diff(
                        diff_text=patch_text,
                        project_name=project_name,
                    )
                    self.logger.info(
                        f"GuardianAgent auto-review: decision={guardian_review_result.get('decision')}"
                    )
                except Exception as e:
                    self.logger.warning(f"GuardianAgent review failed: {e}", exc_info=True)

            # Guardian が REJECT した場合は適用をブロック
            if guardian_review_result and guardian_review_result.get("decision") == "REJECT":
                status = "not_fixed"
                summary = (
                    "Patch was rejected by GuardianAgent auto-review. "
                    f"Reason: {guardian_review_result.get('reason', 'N/A')}"
                )
                details = {
                    "initial_test_output": output,
                    "stacktrace_files": stack_files,
                    "changed_files": changed_files,
                    "debug_result": debug_result,
                    "patch_preview": wrap_diff_as_markdown(patch_text),
                    "patch_changed_files": patch_changed_files,
                    "guardian_review": guardian_review_result,
                }
                return self._finalize(
                    run_id=run_id,
                    session_id=session_id,
                    repo_full_name=repo_full_name,
                    pr_number=pr_number,
                    head_sha=head_sha,
                    status=status,
                    summary=summary,
                    details=details,
                    started_at=started_at,
                    started_at_iso=started_at_iso,
                    started_ts=started_ts,
                )

            # ▼ 6-C. ここから従来の Dry-Run 安全性チェックに続く
            allow_del = self.config.allow_deletions if self.config else False

            dry_result = self.patch_applier.apply_patch(
                patch_text=patch_text,
                project_path=str(project_path),
                dry_run=True,
                allow_deletions=allow_del,
            )
            dangerous = bool(dry_result.get("dangerous", False))
            delete_lines = int(dry_result.get("delete_lines", 0))

            if dangerous and not allow_del:
                status = "not_fixed"
                summary = (
                    f"Patch contains {delete_lines} deleted lines and was blocked by "
                    f"Danger Guard (allow_deletions={allow_del})."
                )
                details = {
                    "initial_test_output": output,
                    "stacktrace_files": stack_files,
                    "changed_files": changed_files,
                    "debug_result": debug_result,
                    "dry_run_result": dry_result,
                    "patch_preview": wrap_diff_as_markdown(patch_text),
                }
                return self._finalize(
                    run_id=run_id,
                    session_id=session_id,
                    repo_full_name=repo_full_name,
                    pr_number=pr_number,
                    head_sha=head_sha,
                    status=status,
                    summary=summary,
                    details=details,
                    started_at=started_at,
                    started_at_iso=started_at_iso,
                    started_ts=started_ts,
                )

            # 7. 実際に Patch を適用
            # E-5: パッチ適用前に、変更されるすべてのファイルの before を取得
            before_code_by_file: Dict[str, str] = {}
            patch_changed_files = summarize_diff_files(patch_text)
            for file_path in patch_changed_files:  # E-5: すべてのファイルを取得
                full_path = project_path / file_path
                if full_path.exists():
                    try:
                        before_code_by_file[file_path] = full_path.read_text(encoding="utf-8")
                    except Exception as e:
                        self.logger.warning(f"Failed to read before code for {file_path}: {e}")

            apply_result = self.patch_applier.apply_patch(
                patch_text=patch_text,
                project_path=str(project_path),
                dry_run=False,
                allow_deletions=allow_del,
            )
            self._maybe_stop("after_patch_apply", {"apply_result": apply_result})

            # E-5: パッチ適用後に、変更されたすべてのファイルの after を取得し、差分サマリーを生成
            diff_summary = None
            if before_code_by_file and hasattr(self, "_guardian_agent") and self._guardian_agent is not None:
                try:
                    # すべてのファイルの before/after を dict に格納
                    file_diffs: Dict[str, Dict[str, str]] = {}
                    for file_path, before_code in before_code_by_file.items():
                        full_path = project_path / file_path
                        if full_path.exists():
                            after_code = full_path.read_text(encoding="utf-8")
                            file_diffs[file_path] = {
                                "before": before_code,
                                "after": after_code,
                            }

                    # GuardianAgent で複数ファイルの差分サマリーを生成
                    if file_diffs:
                        diff_summary = self._guardian_agent.generate_diff_summary(
                            file_diffs=file_diffs,
                            model="gpt-4.1",
                        )
                        self.logger.info(f"Generated diff summary for {len(file_diffs)} files via GuardianAgent")
                except Exception as e:
                    self.logger.warning(f"Failed to generate diff summary: {e}", exc_info=True)

            # 8. 再テスト（4.4: Retry 対応）
            ok2, output2 = self._run_tests(project_path, retry_context=retry_context)
            self._maybe_stop("after_rerun_tests", {"test_ok_after": ok2})

            if ok2:
                status = "fixed"
                summary = "Self-healing patch applied and tests are now passing."
            else:
                status = "not_fixed"
                summary = "Patch applied but tests are still failing."

            # E-5: 実行時間を計算（_finalize() の前に計算）
            finished_ts = time.monotonic()
            duration_seconds = round(finished_ts - started_ts, 2) if started_ts else None
            execution_ms = int(duration_seconds * 1000) if duration_seconds else None

            patch_changed_files = summarize_diff_files(patch_text)
            files_changed = len(patch_changed_files)

            # 4.4: RetryContext から retry_count と error_class を取得
            retry_count = 0
            last_error_class = None
            error_summary = None
            if retry_context:
                retry_info = retry_context.to_dict()
                retry_count = retry_info.get("retry_count", 0)
                last_error_class = retry_info.get("last_error_class")
                error_summary = retry_info.get("error_summary")

            details = {
                "initial_test_output": output,
                "rerun_test_output": output2,
                "stacktrace_files": stack_files,
                "changed_files": changed_files,
                "debug_result": debug_result,
                "dry_run_result": dry_result,
                "apply_result": apply_result,
                "patch_preview": wrap_diff_as_markdown(patch_text),
                "patch_changed_files": patch_changed_files,
                # E-5: 実行メトリクス
                "execution_ms": execution_ms,
                "retry_count": retry_count,  # 4.4: 実際の retry_count
                "files_changed": files_changed,
                # 4.4: エラー分類
                "last_error_class": last_error_class,
                "error_summary": error_summary,
            }

            # E-4/E-5: 差分サマリーを追加
            if diff_summary:
                details["diff_summary"] = diff_summary

            # E-5: モデル名とコスト情報を追加（guardian_agent から取得可能な場合）
            if hasattr(self, "_guardian_agent") and self._guardian_agent is not None:
                if hasattr(self._guardian_agent, "model") and self._guardian_agent.model:
                    details["model"] = self._guardian_agent.model

            # Guardian レビュー結果があれば追加
            if guardian_review_result:
                details["guardian_review"] = guardian_review_result
                # PR コメント用に guardian_status / guardian_comment を設定
                details["guardian_status"] = guardian_review_result.get("decision", "unknown")
                auto_review = guardian_review_result.get("auto_review")
                if auto_review:
                    details["guardian_comment"] = auto_review.get("summary", "")
                elif guardian_review_result.get("reason"):
                    details["guardian_comment"] = guardian_review_result.get("reason")

            return self._finalize(
                run_id=run_id,
                session_id=session_id,
                repo_full_name=repo_full_name,
                pr_number=pr_number,
                head_sha=head_sha,
                status=status,
                summary=summary,
                details=details,
                started_at=started_at,
            )

        except RuntimeError as e:
            # SessionController による中断
            if str(e) == "SessionStopped":
                status = "error"
                summary = "Self-healing run was stopped by user request."
                details = {}
                return self._finalize(
                    run_id=run_id,
                    session_id=session_id,
                    repo_full_name=repo_full_name,
                    pr_number=pr_number,
                    head_sha=head_sha,
                    status=status,
                    summary=summary,
                    details=details,
                    started_at=started_at,
                    started_at_iso=started_at_iso,
                    started_ts=started_ts,
                )
            raise

    # ------------------------------------------------------------------
    # 内部ユーティリティ
    # ------------------------------------------------------------------
    def _maybe_stop(self, phase: str, meta: Optional[Dict[str, Any]] = None) -> None:
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
            # 既存のローカル clone を利用するパターン
            from_repo = Path(base_dir) / repo_full_name
            if from_repo.exists():
                self.logger.info(
                    f"Copying existing repo from {from_repo} to sandbox {target_dir}"
                )
                shutil.copytree(from_repo, target_dir)
            else:
                self.logger.warning(
                    f"NEXUS_REPO_BASE_DIR is set but repo {from_repo} does not exist. "
                    f"Falling back to direct clone."
                )

        # base_dir からコピーできなかった場合、直接 clone する
        if not target_dir.exists():
            # clone URL を決定
            template = os.getenv("NEXUS_GITHUB_CLONE_URL_TEMPLATE")
            if template:
                # 例: "https://x-access-token:{TOKEN}@github.com/{repo_full_name}.git"
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

        # 指定の head_sha を checkout
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

    def _run_tests(self, project_path: Path, retry_context: Optional[RetryContext] = None) -> Tuple[bool, str]:
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

        # 4.4: sandbox_executor を使用（Retry 対応）
        if HAS_RETRY and run_in_sandbox:
            try:
                # コマンドをリストに変換
                cmd_list = cmd_str.split()
                if not cmd_list:
                    cmd_list = ["pytest", "-q"]

                # タイムアウト設定（環境変数から取得、デフォルト 300秒）
                timeout_sec = int(os.getenv("NEXUS_SANDBOX_TIMEOUT_SEC", "300"))

                # sandbox_executor で実行
                result: SandboxResult = run_in_sandbox(
                    cmd=cmd_list,
                    timeout_sec=timeout_sec,
                    cwd=str(project_path),
                    retry_on_errors=True,
                )

                # RetryContext に記録
                if retry_context and result.exception_type:
                    from nexuscore.core.errors import SandboxExecutionError, classify_error
                    error = SandboxExecutionError(f"Sandbox execution failed: {result.stderr}")
                    retry_context.record_attempt(
                        attempt=0,  # sandbox_executor 内部で retry 済み
                        error=error if result.returncode != 0 else None,
                    )

                success = result.returncode == 0 and not result.timed_out
                output = result.stdout + result.stderr if result.stderr else result.stdout
                return success, output

            except Exception as e:
                msg = f"Exception while running tests: {e}"
                self.logger.error(msg, exc_info=True)
                # RetryContext に記録
                if retry_context:
                    retry_context.record_attempt(attempt=0, error=e)
                return False, msg
        else:
            # フォールバック: 従来の subprocess.run
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
        base_ref: Optional[str],
        head_ref: Optional[str],
    ) -> List[str]:
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
                # 最低限のフォールバック: 直前コミットとの差分
                cmd = ["git", "-C", str(project_path), "diff", "--name-only", "HEAD~1..HEAD"]

            self.logger.info(f"Running git diff to get changed files: {' '.join(cmd)}")
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            if proc.returncode != 0:
                self.logger.warning(
                    f"git diff failed (code={proc.returncode}): {proc.stderr}"
                )
                return []

            files: List[str] = []
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
        changed_files: List[str],
        stacktrace_files: List[str],
    ) -> Dict[str, str]:
        """
        DebuggerAgent に渡す対象ファイルの内容を集める。

        優先度:
          1. stacktrace_files
          2. changed_files
        """
        candidates: List[str] = []
        for path in stacktrace_files:
            if path not in candidates:
                candidates.append(path)
        for path in changed_files:
            if path not in candidates:
                candidates.append(path)

        # パスが絶対 / 相対の両方あり得るので、少しだけ頑張る
        files_dict: Dict[str, str] = {}

        for p in candidates:
            abs_path = Path(p)
            if not abs_path.is_absolute():
                abs_path = project_path / p
            if not abs_path.exists():
                # プロジェクトルート相対で再トライ
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

        # あまりに何もない場合は、プロジェクト直下の .py を少しだけ拾う
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
        files: Dict[str, str],
        project_path: Path,
    ) -> Dict[str, Any]:
        """
        DebuggerAgent にエラーとファイル情報を渡して patch を生成させる。

        優先的に DebuggerAgent.debug_and_patch(...) を呼び、
        それが無い場合のみ generate_patch(...) にフォールバックする。
        """
        if not self.debugger_agent:
            self.logger.warning("DebuggerAgent is not configured.")
            return {}

        try:
            # 最優先: debug_and_patch(error_log, files_content, project_path)
            if hasattr(self.debugger_agent, "debug_and_patch"):
                return self.debugger_agent.debug_and_patch(
                    error_log=error_log,
                    files_content=files,
                    project_path=str(project_path),
                )

            # 互換: generate_patch(error_log, files) がある場合
            if hasattr(self.debugger_agent, "generate_patch"):
                return self.debugger_agent.generate_patch(
                    error_log=error_log,
                    files=files,
                )

            self.logger.warning(
                "DebuggerAgent has neither 'debug_and_patch' nor 'generate_patch'."
            )
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
        details: Dict[str, Any],
        started_at: float,
        started_at_iso: Optional[str] = None,
        started_ts: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        RunHistoryLogger への記録と戻り値 dict の生成をまとめる。
        """
        from datetime import datetime, timezone

        finished_at = time.time()
        finished_at_iso = datetime.now(timezone.utc).isoformat()

        # 所要時間の計算
        if started_ts is not None:
            finished_ts = time.monotonic()
            duration_seconds = round(finished_ts - started_ts, 2)
        else:
            duration_seconds = round(finished_at - started_at, 2)

        # ISO8601形式の開始時刻が未指定の場合は生成
        if started_at_iso is None:
            started_at_iso = datetime.fromtimestamp(started_at, tz=timezone.utc).isoformat()

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
            # ログ書き込み失敗は致命的ではない
            self.logger.exception("Failed to log self-healing run history.")

        # E-5: Run レポートの自動生成（webapp が利用可能な場合）
        try:
            from nexuscore.integration.run_report_generator import write_run_report_file
            from nexuscore.webapp.models import Run
            from nexuscore.webapp import db

            # run_id で Run を検索
            run = Run.query.filter_by(run_id=run_id).first()  # type: ignore
            if run and hasattr(run, "id"):
                report_path = write_run_report_file(run.id, base_dir=self.project_root)
                self.logger.info(f"Run report generated: {report_path}")
        except ImportError:
            # webapp が利用できない場合はスキップ
            pass
        except Exception as e:
            # レポート生成失敗は致命的ではない
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


