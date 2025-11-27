"""github_self_healing_webhook.py のテスト"""
from unittest.mock import MagicMock

import pytest

from nexuscore.api.github_self_healing_webhook import (
    format_pr_comment,
    parse_pull_request_event,
)
from nexuscore.config.self_healing_config import SelfHealingConfig


def test_parse_pull_request_event_with_label():
    """self-healing ラベルが付いた PR を正しくパースするテスト"""
    config = SelfHealingConfig(label="self-healing")
    payload = {
        "action": "opened",
        "repository": {
            "full_name": "owner/repo",
        },
        "pull_request": {
            "number": 123,
            "draft": False,
            "labels": [
                {"name": "self-healing"},
                {"name": "bug"},
            ],
            "head": {
                "sha": "abc123def456",
            },
            "base": {
                "ref": "main",
            },
        },
    }

    result = parse_pull_request_event(payload, config)

    assert result is not None
    repo_full_name, pr_number, head_sha = result
    assert repo_full_name == "owner/repo"
    assert pr_number == 123
    assert head_sha == "abc123def456"


def test_parse_pull_request_event_without_label():
    """self-healing ラベルがない PR は None を返すテスト"""
    config = SelfHealingConfig(label="self-healing")
    payload = {
        "action": "opened",
        "repository": {
            "full_name": "owner/repo",
        },
        "pull_request": {
            "number": 123,
            "draft": False,
            "labels": [
                {"name": "bug"},
            ],
            "head": {
                "sha": "abc123def456",
            },
            "base": {
                "ref": "main",
            },
        },
    }

    result = parse_pull_request_event(payload, config)

    assert result is None


def test_parse_pull_request_event_draft_pr():
    """draft PR は None を返すテスト"""
    config = SelfHealingConfig(label="self-healing")
    payload = {
        "action": "opened",
        "repository": {
            "full_name": "owner/repo",
        },
        "pull_request": {
            "number": 123,
            "draft": True,
            "labels": [
                {"name": "self-healing"},
            ],
            "head": {
                "sha": "abc123def456",
            },
            "base": {
                "ref": "main",
            },
        },
    }

    result = parse_pull_request_event(payload, config)

    assert result is None


def test_parse_pull_request_event_ignored_action():
    """対象外のアクションは None を返すテスト"""
    config = SelfHealingConfig(label="self-healing")
    payload = {
        "action": "closed",
        "repository": {
            "full_name": "owner/repo",
        },
        "pull_request": {
            "number": 123,
            "draft": False,
            "labels": [
                {"name": "self-healing"},
            ],
            "head": {
                "sha": "abc123def456",
            },
            "base": {
                "ref": "main",
            },
        },
    }

    result = parse_pull_request_event(payload, config)

    assert result is None


def test_parse_pull_request_event_branch_filter():
    """allowed_target_branches でブランチフィルタリングするテスト"""
    config = SelfHealingConfig(
        label="self-healing",
        allowed_target_branches=["main", "develop"],
    )

    # main ブランチへの PR → 許可
    payload_main = {
        "action": "opened",
        "repository": {"full_name": "owner/repo"},
        "pull_request": {
            "number": 123,
            "draft": False,
            "labels": [{"name": "self-healing"}],
            "head": {"sha": "abc123"},
            "base": {"ref": "main"},
        },
    }
    result = parse_pull_request_event(payload_main, config)
    assert result is not None

    # feature ブランチへの PR → 拒否
    payload_feature = {
        "action": "opened",
        "repository": {"full_name": "owner/repo"},
        "pull_request": {
            "number": 124,
            "draft": False,
            "labels": [{"name": "self-healing"}],
            "head": {"sha": "def456"},
            "base": {"ref": "feature"},
        },
    }
    result = parse_pull_request_event(payload_feature, config)
    assert result is None


def test_parse_pull_request_event_no_branch_filter():
    """allowed_target_branches が None の場合は全ブランチ許可のテスト"""
    config = SelfHealingConfig(
        label="self-healing",
        allowed_target_branches=None,
    )

    payload = {
        "action": "opened",
        "repository": {"full_name": "owner/repo"},
        "pull_request": {
            "number": 123,
            "draft": False,
            "labels": [{"name": "self-healing"}],
            "head": {"sha": "abc123"},
            "base": {"ref": "any-branch"},
        },
    }
    result = parse_pull_request_event(payload, config)
    assert result is not None


def test_format_pr_comment_with_guardian():
    """Guardian レビューを含む PR コメントのテスト"""
    result = {
        "status": "fixed",
        "summary": "Tests are now passing",
        "run_id": "sh-123",
        "session_id": "session-456",
        "details": {
            "guardian_status": "approved",
            "guardian_comment": "パッチは妥当です。",
            "patch_preview": "```diff\n--- a/file.py\n+++ b/file.py\n```",
        },
    }

    comment = format_pr_comment(result)

    assert "Self-Healing Result" in comment
    assert "fixed" in comment
    assert "Guardian Review" in comment
    assert "approved" in comment
    assert "パッチは妥当です。" in comment
    assert "Patch Preview" in comment


def test_format_pr_comment_with_blocked_tests():
    """ブロックされたテストファイルを含む PR コメントのテスト"""
    result = {
        "status": "not_fixed",
        "summary": "Patch was blocked",
        "run_id": "sh-123",
        "session_id": "session-456",
        "details": {
            "blocked_test_paths": ["tests/test_file.py", "test_helper.py"],
        },
    }

    comment = format_pr_comment(result)

    assert "Blocked Test Files" in comment
    assert "tests/test_file.py" in comment
    assert "test_helper.py" in comment


def test_parse_pull_request_event_custom_label():
    """カスタムラベル名でパースするテスト"""
    config = SelfHealingConfig(label="auto-fix")
    payload = {
        "action": "opened",
        "repository": {"full_name": "owner/repo"},
        "pull_request": {
            "number": 123,
            "draft": False,
            "labels": [{"name": "auto-fix"}],
            "head": {"sha": "abc123"},
            "base": {"ref": "main"},
        },
    }
    result = parse_pull_request_event(payload, config)
    assert result is not None

