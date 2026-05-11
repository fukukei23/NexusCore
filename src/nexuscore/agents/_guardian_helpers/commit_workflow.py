"""
Commit execution workflow extracted from GuardianAgent.review_and_commit().

Handles branch preparation, commit message generation, and the actual commit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .git_operations import generate_commit_message, prepare_branch

if TYPE_CHECKING:
    from nexuscore.utils.vcs import GitController


def execute_commit_workflow(
    review_data: dict[str, Any],
    changed_files: list[str],
    vcs: GitController | None,
    model: str = "",
    debug_info: dict[str, Any] | None = None,
    branch_name: str | None = None,
) -> dict[str, Any]:
    """Execute the commit workflow after review approval.

    Mutates ``review_data`` in-place, adding a ``"commit"`` key with the
    commit hash or an explanatory message.

    Args:
        review_data: Review result dictionary (must contain ``"decision"``).
        changed_files: Files to include in the commit.
        vcs: GitController instance — ``None`` disables commits.
        model: Model name used in commit message metadata.
        debug_info: Optional self-healing debug context.
        branch_name: Optional target branch (created/switched via ``-B``).

    Returns:
        The mutated ``review_data`` dict.
    """
    if review_data.get("decision") != "APPROVE":
        return review_data

    if not vcs:
        review_data["commit"] = "Git repository not available."
        return review_data

    try:
        if branch_name:
            prepare_branch(branch_name)
    except Exception as e:
        review_data["commit"] = f"Failed to prepare branch '{branch_name}': {e}"
        return review_data

    commit_msg = generate_commit_message(review_data, changed_files, model, debug_info)
    commit_hash = vcs.commit_changes(changed_files, commit_msg)
    review_data["commit"] = commit_hash or "Commit failed or no changes detected."
    return review_data
