from __future__ import annotations

from typing import Any

from nexuscore.core.diff_preview import summarize_diff_files, wrap_diff_as_markdown
from nexuscore.services.patch_workflow import (
    check_dry_run,
    check_test_modification,
    run_guardian_review,
)


def validate_test_modification(
    patch_text: str,
    config: Any,
    context: dict[str, Any],
) -> tuple[bool, dict[str, Any] | None]:
    """Check if patch modifies test files. Returns (blocked, finalize_kwargs)."""
    blocked, block_summary, touched_tests = check_test_modification(patch_text, config)
    if not blocked:
        return False, None

    details = {
        **context,
        "patch_preview": wrap_diff_as_markdown(patch_text),
        "patch_changed_files": summarize_diff_files(patch_text),
        "blocked_test_paths": touched_tests,
    }
    return True, {"status": "not_fixed", "summary": block_summary, "details": details}


def validate_guardian_review(
    patch_text: str,
    repo_full_name: str,
    guardian_agent: Any | None,
    context: dict[str, Any],
) -> tuple[bool, dict[str, Any] | None]:
    """Run Guardian review. Returns (blocked, finalize_kwargs)."""
    guardian_review_result = run_guardian_review(
        patch_text, repo_full_name, guardian_agent,
    )

    if not guardian_review_result or guardian_review_result.get("decision") != "REJECT":
        # Not blocked — store review result in context for later use
        context["guardian_review_result"] = guardian_review_result
        return False, None

    details = {
        **context,
        "patch_preview": wrap_diff_as_markdown(patch_text),
        "patch_changed_files": summarize_diff_files(patch_text),
        "guardian_review": guardian_review_result,
    }
    return True, {
        "status": "not_fixed",
        "summary": (
            f"Patch was rejected by GuardianAgent auto-review. "
            f"Reason: {guardian_review_result.get('reason', 'N/A')}"
        ),
        "details": details,
    }


def validate_dry_run(
    patch_text: str,
    project_path: str,
    patch_applier: Any,
    config: Any,
    context: dict[str, Any],
) -> tuple[bool, dict[str, Any] | None]:
    """Run dry-run safety check. Returns (blocked, finalize_kwargs)."""
    dry_blocked, dry_summary, dry_result = check_dry_run(
        patch_text, project_path, patch_applier, config,
    )
    if not dry_blocked:
        context["dry_result"] = dry_result
        return False, None

    details = {
        **context,
        "dry_run_result": dry_result,
        "patch_preview": wrap_diff_as_markdown(patch_text),
    }
    return True, {"status": "not_fixed", "summary": dry_summary, "details": details}
