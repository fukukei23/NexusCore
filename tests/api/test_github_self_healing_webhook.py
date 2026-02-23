"""github_self_healing_webhook.py のテスト"""



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


def test_build_pr_comment_does_not_include_self_healing_result_header():
    """build_pr_comment() が Self-Healing Result ヘッダーを返さないことを検証"""
    from nexuscore.integration.github_pr_comment import PRCommentContext, build_pr_comment

    ctx = PRCommentContext(
        project=None,
        run=None,
        guardian_review_markdown="_(no review content)_",
        repo_full_name=None,
        pr_number=None,
        commit_sha=None,
        change_summary=None,
        diff_summary=None,
        markdown_report=None,
        details=None,
        semantic_diffs=None,
    )

    result = build_pr_comment(ctx)

    # build_pr_comment() は Self-Healing Result ヘッダーを含まない
    assert "## Self-Healing Result" not in result


def test_format_pr_comment_includes_self_healing_result_header_once():
    """format_pr_comment() が Self-Healing Result ヘッダーを1回だけ含むことを検証"""
    # CR-NEXUS-039 Follow-up-2: import 依存を排除するため、テスト関数内で明示的に import
    from nexuscore.api.github_self_healing_webhook import format_pr_comment

    result = {
        "status": "fixed",
        "summary": "Tests are now passing",
        "run_id": "sh-123",
        "session_id": "session-456",
        "details": {},
    }

    comment = format_pr_comment(result)

    # Self-Healing Result ヘッダーが1回だけ含まれる
    assert comment.count("## Self-Healing Result") == 1
    assert "## Self-Healing Result" in comment
