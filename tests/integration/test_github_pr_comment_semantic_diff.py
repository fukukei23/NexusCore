"""
github_pr_comment の Semantic Diff 統合テスト

semantic_diffs に簡単な dict を渡して build_pr_comment() を呼び、
<summary>🧠 Semantic Diff: や 関数名が含まれることを確認する。
"""

from __future__ import annotations

import pytest

try:
    from nexuscore.integration.github_pr_comment import (
        PRCommentContext,
        build_pr_comment,
        format_semantic_diff_block,
    )
    HAS_GITHUB_PR_COMMENT = True
except ImportError:
    HAS_GITHUB_PR_COMMENT = False
    PRCommentContext = None  # type: ignore
    build_pr_comment = None  # type: ignore
    format_semantic_diff_block = None  # type: ignore


@pytest.mark.skipif(not HAS_GITHUB_PR_COMMENT, reason="github_pr_comment module not available")
def test_format_semantic_diff_block_basic() -> None:
    """format_semantic_diff_block が基本的に動作することを確認"""
    semantic_diffs = {
        "sample.py": {
            "functions": [
                {
                    "name": "foo",
                    "kind": "added",
                    "signature_before": None,
                    "signature_after": "foo(x: int) -> int",
                    "doc_before": None,
                    "doc_after": None,
                }
            ],
            "behavior_hints": [
                {
                    "description": "例外パスが追加されました（1箇所）",
                    "risk_level": "medium",
                }
            ],
        }
    }

    result = format_semantic_diff_block(semantic_diffs)

    assert "🧠 Semantic Diff" in result
    assert "sample.py" in result
    assert "foo" in result
    assert "added" in result
    assert "例外パスが追加されました" in result


@pytest.mark.skipif(not HAS_GITHUB_PR_COMMENT, reason="github_pr_comment module not available")
def test_format_semantic_diff_block_empty() -> None:
    """空の semantic_diffs を渡した場合、空文字列を返すことを確認"""
    result = format_semantic_diff_block(None)
    assert result == ""

    result = format_semantic_diff_block({})
    assert result == ""


@pytest.mark.skipif(not HAS_GITHUB_PR_COMMENT, reason="github_pr_comment module not available")
def test_build_pr_comment_includes_semantic_diff() -> None:
    """build_pr_comment に semantic_diffs を渡した場合、Semantic Diff セクションが含まれることを確認"""
    semantic_diffs = {
        "sample.py": {
            "functions": [
                {
                    "name": "bar",
                    "kind": "modified",
                    "signature_before": "bar(x: int)",
                    "signature_after": "bar(x: int, y: int = 0)",
                    "doc_before": None,
                    "doc_after": None,
                }
            ],
            "behavior_hints": [],
        }
    }

    ctx = PRCommentContext(
        guardian_review_markdown="Test review",
        semantic_diffs=semantic_diffs,
    )

    comment = build_pr_comment(ctx)

    assert "🧠 Semantic Diff" in comment
    assert "sample.py" in comment
    assert "bar" in comment
    assert "modified" in comment

