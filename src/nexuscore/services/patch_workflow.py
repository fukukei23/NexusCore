"""
patch_workflow.py

Self-Healing Service 用のパッチ生成・検証ワークフロー。
ファイル収集、パッチ生成、テスト変更ガード、Guardian review、
dry-run チェック、semantic diff 生成を担当。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from nexuscore.config.self_healing_config import SelfHealingConfig
from nexuscore.core.diff_preview import summarize_diff_files, wrap_diff_as_markdown
from nexuscore.core.stacktrace_mapper import extract_candidate_files
from nexuscore.diff.semantic_diff import compute_semantic_diff

logger = logging.getLogger(__name__)


def collect_relevant_files(
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


def generate_patch_via_debugger(
    debugger_agent: Any,
    error_log: str,
    files: dict[str, str],
    project_path: Path,
) -> dict[str, Any]:
    """
    DebuggerAgent にエラーとファイル情報を渡して patch を生成させる。

    優先的に DebuggerAgent.debug_and_patch(...) を呼び、
    それが無い場合のみ generate_patch(...) にフォールバックする。
    """
    if not debugger_agent:
        logger.warning("DebuggerAgent is not configured.")
        return {}

    try:
        if hasattr(debugger_agent, "debug_and_patch"):
            return debugger_agent.debug_and_patch(
                error_log=error_log,
                files_content=files,
                project_path=str(project_path),
            )

        if hasattr(debugger_agent, "generate_patch"):
            return debugger_agent.generate_patch(
                error_log=error_log,
                files=files,
            )

        logger.warning("DebuggerAgent has neither 'debug_and_patch' nor 'generate_patch'.")
        return {}
    except Exception as e:
        logger.error(f"DebuggerAgent call failed: {e}", exc_info=True)
        return {}


def check_test_modification(
    patch_text: str,
    config: SelfHealingConfig | None,
) -> tuple[bool, str, list[str]]:
    """
    パッチがテストファイルを変更していないかチェックする。

    Returns:
        (blocked, summary, touched_test_paths)
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

    if touched_tests and not (config and config.allow_test_modification):
        return True, (
            "Patch was blocked because it modifies test files. "
            "Modifying tests is not allowed by current self-healing policy."
        ), touched_tests

    return False, "", touched_tests


def run_guardian_review(
    patch_text: str,
    repo_full_name: str,
    guardian_agent: Any,
) -> dict[str, Any] | None:
    """
    GuardianAgent でパッチの自動レビューを実行する。
    """
    if guardian_agent is None:
        return None

    try:
        project_name = "nexuscore"
        if "atelier" in repo_full_name.lower() or "buyma" in repo_full_name.lower():
            project_name = "atelier-kyo-manager"

        result = guardian_agent.review_unified_diff(
            diff_text=patch_text,
            project_name=project_name,
        )
        logger.info(f"GuardianAgent auto-review: decision={result.get('decision')}")
        return result
    except Exception as e:
        logger.warning(f"GuardianAgent review failed: {e}", exc_info=True)
        return None


def check_dry_run(
    patch_text: str,
    project_path: str,
    patch_applier: Any,
    config: SelfHealingConfig | None,
) -> tuple[bool, str, dict[str, Any]]:
    """
    dry-run でパッチの安全性をチェックする。

    Returns:
        (blocked, summary, dry_run_result)
    """
    allow_del = config.allow_deletions if config else False

    dry_result = patch_applier.apply_patch(
        patch_text=patch_text,
        project_path=project_path,
        dry_run=True,
        allow_deletions=allow_del,
    )
    dangerous = bool(dry_result.get("dangerous", False))
    delete_lines = int(dry_result.get("delete_lines", 0))

    if dangerous and not allow_del:
        return True, (
            f"Patch contains {delete_lines} deleted lines and was blocked by "
            f"Danger Guard (allow_deletions={allow_del})."
        ), dry_result

    return False, "", dry_result


def generate_diff_summary(
    patch_text: str,
    project_path: Path,
    guardian_agent: Any,
) -> dict[str, Any] | None:
    """
    パッチ適用前後のファイルの semantic diff を生成し、
    GuardianAgent で差分サマリーを生成する。
    """
    patch_changed_files = summarize_diff_files(patch_text)

    before_code_by_file: dict[str, str] = {}
    for file_path in patch_changed_files:
        full_path = project_path / file_path
        if full_path.exists():
            try:
                before_code_by_file[file_path] = full_path.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning(f"Failed to read before code for {file_path}: {e}")

    if not before_code_by_file or guardian_agent is None:
        return None

    try:
        file_diffs: dict[str, dict[str, str]] = {}
        for file_path, before_code in before_code_by_file.items():
            full_path = project_path / file_path
            if full_path.exists():
                after_code = full_path.read_text(encoding="utf-8")
                file_diffs[file_path] = {
                    "before": before_code,
                    "after": after_code,
                }

        semantic_diffs: dict[str, dict[str, object]] = {}
        for rel_path, contents in file_diffs.items():
            before = contents.get("before") or ""
            after = contents.get("after") or ""
            try:
                result = compute_semantic_diff(
                    file_path=project_path / rel_path,
                    before_code=before,
                    after_code=after,
                    language="python",
                )
                semantic_diffs[rel_path] = result.to_dict()
            except Exception as exc:
                logger.warning(f"Failed to compute semantic diff for {rel_path}: {exc}", exc_info=True)

        if file_diffs:
            diff_summary = guardian_agent.generate_diff_summary(
                file_diffs=file_diffs,
                semantic_diffs=semantic_diffs if semantic_diffs else None,
                model="glm-4-plus",
            )
            logger.info(f"Generated diff summary for {len(file_diffs)} files via GuardianAgent")
            return diff_summary
    except Exception as e:
        logger.warning(f"Failed to generate diff summary: {e}", exc_info=True)

    return None
