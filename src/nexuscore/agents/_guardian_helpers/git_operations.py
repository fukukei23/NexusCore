"""
Git branch preparation and commit message helpers for GuardianAgent.
"""

from __future__ import annotations

import os
from typing import Any

import git


def prepare_branch(branch_name: str) -> None:
    """
    GitPython を使って <branch_name> に -B 相当で移動。
    """
    try:
        repo = git.Repo(os.getcwd())
    except Exception as e:
        raise RuntimeError(f"Git repo not found: {e}") from e
    repo.git.checkout("-B", branch_name)


def generate_commit_message(
    review_data: dict[str, Any],
    changed_files: list[str],
    model_name: str = "",
    debug_info: dict[str, Any] | None = None,
) -> str:
    """
    レビュー結果からコミットメッセージを生成する。

    Args:
        review_data: レビュー結果辞書
        changed_files: 変更ファイルリスト
        model_name: 使用モデル名
        debug_info: デバッグ情報（自己修復時）
    """
    scope = "auto"
    body = f"Reviewed by: GuardianAgent (Model: {model_name})\n"
    body += f"Reason for approval: {review_data.get('reason', 'N/A')}\n"

    if debug_info:
        commit_type = "fix"
        header = f"{commit_type}({scope}): Self-healed by DebuggerAgent"
        body += "\n[DEBUGGER ACTIVITY]\n"
        body += f"Error Signature: {debug_info.get('error_signature', 'N/A')}\n"
        solution_type = debug_info.get("solution_pattern", {}).get("type", "N/A")
        body += f"Applied Solution Type: {solution_type}\n"
    else:
        commit_type = "feat"
        header = f"{commit_type}({scope}): Implemented new functionality via CoderAgent"

    return f"{header}\n\n{body}"
