"""
============================================================================
Comprehensive Tests for github_self_healing_webhook.py
============================================================================
高品質テストの原則:
- 外部依存（SelfHealingService、各種エージェント）をモック
- 実際のWebhook処理ロジックをテスト
- エッジケースとエラー条件をカバー
============================================================================
"""

import os
import tempfile
from unittest.mock import Mock, patch

import pytest

from nexuscore.api.github_self_healing_webhook import (
    _init_self_healing_service,
    format_pr_comment,
    github_webhook,
    parse_pull_request_event,
)
from nexuscore.config.self_healing_config import SelfHealingConfig

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def config():
    """Self-Healing 設定"""
    return SelfHealingConfig(
        label="self-healing",
        allowed_target_branches=["main", "develop"],
    )


@pytest.fixture
def pr_payload():
    """GitHub PR Webhook ペイロード"""
    return {
        "action": "opened",
        "repository": {
            "full_name": "test-owner/test-repo",
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


@pytest.fixture
def self_healing_result():
    """Self-Healing 実行結果"""
    return {
        "status": "fixed",
        "summary": "Tests are now passing",
        "run_id": "sh-test-123",
        "session_id": "session-456",
        "details": {
            "guardian_status": "approved",
            "guardian_comment": "Changes look good",
            "patch_preview": "```diff\n--- a/file.py\n+++ b/file.py\n```",
        },
    }


# ============================================================================
# Tests: parse_pull_request_event
# ============================================================================


class TestParsePullRequestEvent:
    def test_parse_with_required_label(self, config, pr_payload):
        """必須ラベル付きPRをパース"""
        result = parse_pull_request_event(pr_payload, config)

        assert result is not None
        repo_full_name, pr_number, head_sha = result
        assert repo_full_name == "test-owner/test-repo"
        assert pr_number == 123
        assert head_sha == "abc123def456"

    def test_parse_without_required_label(self, config):
        """必須ラベルがないPRは None"""
        payload = {
            "action": "opened",
            "repository": {"full_name": "owner/repo"},
            "pull_request": {
                "number": 123,
                "draft": False,
                "labels": [{"name": "bug"}],
                "head": {"sha": "abc123"},
                "base": {"ref": "main"},
            },
        }

        result = parse_pull_request_event(payload, config)
        assert result is None

    def test_parse_draft_pr(self, config):
        """Draft PR は None"""
        payload = {
            "action": "opened",
            "repository": {"full_name": "owner/repo"},
            "pull_request": {
                "number": 123,
                "draft": True,
                "labels": [{"name": "self-healing"}],
                "head": {"sha": "abc123"},
                "base": {"ref": "main"},
            },
        }

        result = parse_pull_request_event(payload, config)
        assert result is None

    def test_parse_ignored_action(self, config):
        """対象外のアクションは None"""
        payload = {
            "action": "closed",
            "repository": {"full_name": "owner/repo"},
            "pull_request": {
                "number": 123,
                "draft": False,
                "labels": [{"name": "self-healing"}],
                "head": {"sha": "abc123"},
                "base": {"ref": "main"},
            },
        }

        result = parse_pull_request_event(payload, config)
        assert result is None

    def test_parse_allowed_actions(self, config, pr_payload):
        """許可されたアクション"""
        allowed_actions = ["opened", "reopened", "synchronize", "ready_for_review"]

        for action in allowed_actions:
            payload = pr_payload.copy()
            payload["action"] = action

            result = parse_pull_request_event(payload, config)
            assert result is not None

    def test_parse_branch_filter_allowed(self, config):
        """許可されたブランチへのPR"""
        payload = {
            "action": "opened",
            "repository": {"full_name": "owner/repo"},
            "pull_request": {
                "number": 123,
                "draft": False,
                "labels": [{"name": "self-healing"}],
                "head": {"sha": "abc123"},
                "base": {"ref": "develop"},  # allowed
            },
        }

        result = parse_pull_request_event(payload, config)
        assert result is not None

    def test_parse_branch_filter_rejected(self, config):
        """許可されていないブランチへのPRは None"""
        payload = {
            "action": "opened",
            "repository": {"full_name": "owner/repo"},
            "pull_request": {
                "number": 123,
                "draft": False,
                "labels": [{"name": "self-healing"}],
                "head": {"sha": "abc123"},
                "base": {"ref": "feature"},  # not allowed
            },
        }

        result = parse_pull_request_event(payload, config)
        assert result is None

    def test_parse_no_branch_filter(self):
        """ブランチフィルターなしの場合は全許可"""
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

    def test_parse_missing_required_fields(self, config):
        """必須フィールドが欠けている場合は None"""
        # リポジトリ名が欠けている
        payload1 = {
            "action": "opened",
            "repository": {},
            "pull_request": {
                "number": 123,
                "draft": False,
                "labels": [{"name": "self-healing"}],
                "head": {"sha": "abc123"},
                "base": {"ref": "main"},
            },
        }
        assert parse_pull_request_event(payload1, config) is None

        # PR番号が欠けている
        payload2 = {
            "action": "opened",
            "repository": {"full_name": "owner/repo"},
            "pull_request": {
                "draft": False,
                "labels": [{"name": "self-healing"}],
                "head": {"sha": "abc123"},
                "base": {"ref": "main"},
            },
        }
        assert parse_pull_request_event(payload2, config) is None

        # head SHA が欠けている
        payload3 = {
            "action": "opened",
            "repository": {"full_name": "owner/repo"},
            "pull_request": {
                "number": 123,
                "draft": False,
                "labels": [{"name": "self-healing"}],
                "head": {},
                "base": {"ref": "main"},
            },
        }
        assert parse_pull_request_event(payload3, config) is None

    def test_parse_custom_label(self):
        """カスタムラベル名でパース"""
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


# ============================================================================
# Tests: format_pr_comment
# ============================================================================


class TestFormatPrComment:
    @patch("nexuscore.integration.github_pr_comment.build_pr_comment")
    @patch("nexuscore.integration.github_pr_comment.PRCommentContext")
    def test_format_pr_comment_basic(self, mock_context_class, mock_build, self_healing_result):
        """基本的なPRコメントのフォーマット"""
        mock_build.return_value = "Formatted comment"

        comment = format_pr_comment(self_healing_result)

        assert "Formatted comment" in comment
        assert "## Self-Healing Result" in comment
        mock_build.assert_called_once()

    @patch("nexuscore.integration.github_pr_comment.build_pr_comment")
    @patch("nexuscore.integration.github_pr_comment.PRCommentContext")
    def test_format_pr_comment_with_guardian_review(
        self, mock_context_class, mock_build, self_healing_result
    ):
        """Guardian レビュー付きPRコメント"""
        mock_build.return_value = "Comment with guardian review"

        format_pr_comment(self_healing_result)

        # PRCommentContext が Guardian 情報を受け取る
        context_call = mock_context_class.call_args[1]
        assert "guardian_review_markdown" in context_call
        assert "approved" in context_call["guardian_review_markdown"]
        assert "Changes look good" in context_call["guardian_review_markdown"]

    @patch("nexuscore.integration.github_pr_comment.build_pr_comment")
    @patch("nexuscore.integration.github_pr_comment.PRCommentContext")
    def test_format_pr_comment_without_guardian_review(self, mock_context_class, mock_build):
        """Guardian レビューなしのPRコメント"""
        result = {
            "status": "fixed",
            "summary": "Tests passing",
            "run_id": "test-123",
            "details": {},
        }

        mock_build.return_value = "Comment without guardian"

        format_pr_comment(result)

        context_call = mock_context_class.call_args[1]
        assert "guardian_review_markdown" in context_call
        assert "no review content" in context_call["guardian_review_markdown"]

    @patch("nexuscore.integration.github_pr_comment.build_pr_comment")
    @patch("nexuscore.integration.github_pr_comment.PRCommentContext")
    def test_format_pr_comment_with_repo_and_pr_info(
        self, mock_context_class, mock_build, self_healing_result
    ):
        """リポジトリとPR情報付きでフォーマット"""
        mock_build.return_value = "Comment"

        format_pr_comment(
            self_healing_result,
            repo_full_name="owner/repo",
            pr_number=456,
        )

        context_call = mock_context_class.call_args[1]
        assert context_call["repo_full_name"] == "owner/repo"
        assert context_call["pr_number"] == 456

    @patch("nexuscore.integration.github_pr_comment.build_pr_comment")
    @patch("nexuscore.integration.github_pr_comment.PRCommentContext")
    def test_format_pr_comment_with_diff_summary(self, mock_context_class, mock_build):
        """差分サマリー付きPRコメント"""
        result = {
            "status": "fixed",
            "run_id": "test-123",
            "details": {
                "diff_summary": "Changed 3 files",
            },
        }

        mock_build.return_value = "Comment with diff"

        format_pr_comment(result)

        context_call = mock_context_class.call_args[1]
        assert context_call["diff_summary"] == "Changed 3 files"

    @patch("nexuscore.integration.github_pr_comment.build_pr_comment")
    @patch("nexuscore.integration.github_pr_comment.PRCommentContext")
    def test_format_pr_comment_with_semantic_diffs(self, mock_context_class, mock_build):
        """セマンティック差分付きPRコメント"""
        result = {
            "status": "fixed",
            "run_id": "test-123",
            "details": {
                "semantic_diffs": [{"file": "test.py", "changes": "Fixed bug"}],
            },
        }

        mock_build.return_value = "Comment with semantic diffs"

        format_pr_comment(result)

        context_call = mock_context_class.call_args[1]
        assert context_call["semantic_diffs"] is not None


# ============================================================================
# Tests: _init_self_healing_service
# ============================================================================


class TestInitSelfHealingService:
    @patch("nexuscore.api.github_self_healing_webhook.SelfHealingService")
    @patch("nexuscore.api.github_self_healing_webhook.GuardianAgent")
    @patch("nexuscore.api.github_self_healing_webhook.DebuggerAgent")
    def test_init_service_success(
        self, mock_debugger_class, mock_guardian_class, mock_service_class
    ):
        """SelfHealingService の正常初期化"""
        config = SelfHealingConfig(label="self-healing")

        with tempfile.TemporaryDirectory() as tmpdir:
            _init_self_healing_service(tmpdir, config)

            # SelfHealingService が初期化される
            mock_service_class.assert_called_once()

            # DebuggerAgent と GuardianAgent が初期化される
            mock_debugger_class.assert_called_once()
            mock_guardian_class.assert_called_once()

    @patch("nexuscore.api.github_self_healing_webhook.SelfHealingService")
    @patch("nexuscore.api.github_self_healing_webhook.GuardianAgent")
    @patch("nexuscore.api.github_self_healing_webhook.DebuggerAgent")
    def test_init_service_debugger_failure(
        self, mock_debugger_class, mock_guardian_class, mock_service_class
    ):
        """DebuggerAgent 初期化失敗でもサービスは起動"""
        mock_debugger_class.side_effect = Exception("Debugger init failed")
        config = SelfHealingConfig(label="self-healing")

        with tempfile.TemporaryDirectory() as tmpdir:
            _init_self_healing_service(tmpdir, config)

            # SelfHealingService は初期化される（debugger=None）
            mock_service_class.assert_called_once()

    @patch("nexuscore.api.github_self_healing_webhook.SelfHealingService")
    @patch("nexuscore.api.github_self_healing_webhook.GuardianAgent")
    @patch("nexuscore.api.github_self_healing_webhook.DebuggerAgent")
    def test_init_service_guardian_failure(
        self, mock_debugger_class, mock_guardian_class, mock_service_class
    ):
        """GuardianAgent 初期化失敗でもサービスは起動"""
        mock_guardian_class.side_effect = Exception("Guardian init failed")
        config = SelfHealingConfig(label="self-healing")

        with tempfile.TemporaryDirectory() as tmpdir:
            _init_self_healing_service(tmpdir, config)

            # SelfHealingService は初期化される（guardian=None）
            mock_service_class.assert_called_once()

    @patch("nexuscore.api.github_self_healing_webhook.SelfHealingService", None)
    def test_init_service_not_available(self):
        """SelfHealingService が利用できない場合"""
        config = SelfHealingConfig(label="self-healing")

        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ImportError):
                _init_self_healing_service(tmpdir, config)


# ============================================================================
# Tests: github_webhook
# ============================================================================


class TestGithubWebhook:
    @patch("nexuscore.api.github_self_healing_webhook._init_self_healing_service")
    @patch("nexuscore.api.github_self_healing_webhook.SelfHealingConfig")
    def test_github_webhook_skipped_without_label(
        self, mock_config_class, mock_init_service, pr_payload
    ):
        """ラベルがないPRはスキップ"""
        config = SelfHealingConfig(label="self-healing")
        mock_config_class.load.return_value = config

        # ラベルを削除
        payload = pr_payload.copy()
        payload["pull_request"]["labels"] = []

        result = github_webhook(payload)

        assert result["status"] == "skipped"
        assert "does not meet criteria" in result["summary"]

        # SelfHealingService は初期化されない
        mock_init_service.assert_not_called()

    @patch("nexuscore.api.github_self_healing_webhook._init_self_healing_service")
    @patch("nexuscore.api.github_self_healing_webhook.SelfHealingConfig")
    def test_github_webhook_success(self, mock_config_class, mock_init_service, pr_payload):
        """Self-Healing 成功"""
        config = SelfHealingConfig(label="self-healing")
        mock_config_class.load.return_value = config

        # SelfHealingService のモック
        mock_service = Mock()
        mock_service._guardian_agent = None  # guardian_agent 属性を明示的に None に
        mock_service.run_for_pull_request.return_value = {
            "status": "fixed",
            "summary": "Tests passing",
            "details": {},
        }
        mock_init_service.return_value = mock_service

        result = github_webhook(payload=pr_payload, event="pull_request")

        assert result["status"] == "fixed"
        assert result["summary"] == "Tests passing"

        # run_for_pull_request が呼ばれる
        mock_service.run_for_pull_request.assert_called_once_with(
            repo_full_name="test-owner/test-repo",
            pr_number=123,
            head_sha="abc123def456",
        )

    @patch("nexuscore.api.github_self_healing_webhook._init_self_healing_service")
    @patch("nexuscore.api.github_self_healing_webhook.SelfHealingConfig")
    def test_github_webhook_with_guardian_review(
        self, mock_config_class, mock_init_service, pr_payload
    ):
        """Guardian レビュー統合"""
        config = SelfHealingConfig(label="self-healing")
        mock_config_class.load.return_value = config

        # GuardianAgent のモック
        mock_guardian = Mock()
        mock_guardian.review_self_healing.return_value = {
            "status": "approved",
            "comment": "Looks good",
        }

        mock_service = Mock()
        mock_service._guardian_agent = mock_guardian
        mock_service.run_for_pull_request.return_value = {
            "status": "fixed",
            "details": {},
        }

        mock_init_service.return_value = mock_service

        result = github_webhook(payload=pr_payload)

        # Guardian レビューが統合される
        assert result["details"]["guardian_status"] == "approved"
        assert result["details"]["guardian_comment"] == "Looks good"

    @patch("nexuscore.api.github_self_healing_webhook._init_self_healing_service")
    @patch("nexuscore.api.github_self_healing_webhook.SelfHealingConfig")
    def test_github_webhook_guardian_override_status(
        self, mock_config_class, mock_init_service, pr_payload
    ):
        """Guardian が status を上書き"""
        config = SelfHealingConfig(label="self-healing")
        mock_config_class.load.return_value = config

        mock_guardian = Mock()
        mock_guardian.review_self_healing.return_value = {
            "status": "needs_review",
            "comment": "Manual review required",
            "override_status": "needs_manual_review",
        }

        mock_service = Mock()
        mock_service._guardian_agent = mock_guardian
        mock_service.run_for_pull_request.return_value = {
            "status": "fixed",
            "details": {},
        }

        mock_init_service.return_value = mock_service

        result = github_webhook(payload=pr_payload)

        # status が上書きされる
        assert result["status"] == "needs_manual_review"

    @patch("nexuscore.api.github_self_healing_webhook._init_self_healing_service")
    @patch("nexuscore.api.github_self_healing_webhook.SelfHealingConfig")
    def test_github_webhook_guardian_review_exception(
        self, mock_config_class, mock_init_service, pr_payload
    ):
        """Guardian レビュー失敗でも処理は継続"""
        config = SelfHealingConfig(label="self-healing")
        mock_config_class.load.return_value = config

        mock_guardian = Mock()
        mock_guardian.review_self_healing.side_effect = Exception("Review failed")

        mock_service = Mock()
        mock_service._guardian_agent = mock_guardian
        mock_service.run_for_pull_request.return_value = {
            "status": "fixed",
            "details": {},
        }

        mock_init_service.return_value = mock_service

        result = github_webhook(payload=pr_payload)

        # エラーでも結果は返される
        assert result["status"] == "fixed"

    @patch("nexuscore.api.github_self_healing_webhook._init_self_healing_service")
    @patch("nexuscore.api.github_self_healing_webhook.SelfHealingConfig")
    def test_github_webhook_service_exception(
        self, mock_config_class, mock_init_service, pr_payload
    ):
        """SelfHealingService 実行中の例外"""
        config = SelfHealingConfig(label="self-healing")
        mock_config_class.load.return_value = config

        mock_service = Mock()
        mock_service.run_for_pull_request.side_effect = Exception("Service failed")
        mock_init_service.return_value = mock_service

        result = github_webhook(payload=pr_payload)

        assert result["status"] == "error"
        assert "failed" in result["summary"]

    @patch("nexuscore.api.github_self_healing_webhook._init_self_healing_service")
    @patch("nexuscore.api.github_self_healing_webhook.SelfHealingConfig")
    @patch.dict(os.environ, {"NEXUS_PROJECT_ROOT": "/custom/project"})
    def test_github_webhook_custom_project_root(
        self, mock_config_class, mock_init_service, pr_payload
    ):
        """カスタムプロジェクトルート"""
        config = SelfHealingConfig(label="self-healing")
        mock_config_class.load.return_value = config

        mock_service = Mock()
        mock_service._guardian_agent = None
        mock_service.run_for_pull_request.return_value = {"status": "fixed", "details": {}}
        mock_init_service.return_value = mock_service

        github_webhook(payload=pr_payload)

        # カスタムパスで初期化される
        mock_config_class.load.assert_called_once_with("/custom/project")
        mock_init_service.assert_called_once()
        assert mock_init_service.call_args[1]["project_root"] == "/custom/project"

    @patch("nexuscore.api.github_self_healing_webhook._init_self_healing_service")
    @patch("nexuscore.api.github_self_healing_webhook.SelfHealingConfig")
    def test_github_webhook_with_model_name(self, mock_config_class, mock_init_service, pr_payload):
        """Guardian のモデル名が result に追加される"""
        config = SelfHealingConfig(label="self-healing")
        mock_config_class.load.return_value = config

        mock_guardian = Mock()
        mock_guardian.model = "gpt-4"

        mock_service = Mock()
        mock_service._guardian_agent = mock_guardian
        mock_service.run_for_pull_request.return_value = {
            "status": "fixed",
            "details": {},
        }

        mock_init_service.return_value = mock_service

        result = github_webhook(payload=pr_payload)

        assert result["details"]["model_name"] == "gpt-4"


# ============================================================================
# Tests: Integration scenarios
# ============================================================================


class TestIntegrationScenarios:
    @patch("nexuscore.api.github_self_healing_webhook._init_self_healing_service")
    @patch("nexuscore.api.github_self_healing_webhook.SelfHealingConfig")
    def test_full_self_healing_workflow(self, mock_config_class, mock_init_service, pr_payload):
        """完全な Self-Healing ワークフロー"""
        config = SelfHealingConfig(label="self-healing")
        mock_config_class.load.return_value = config

        # Guardian のモック
        mock_guardian = Mock()
        mock_guardian.model = "gpt-4"
        mock_guardian.review_self_healing.return_value = {
            "status": "approved",
            "comment": "All changes validated",
        }

        # SelfHealingService のモック
        mock_service = Mock()
        mock_service._guardian_agent = mock_guardian
        mock_service.run_for_pull_request.return_value = {
            "status": "fixed",
            "summary": "All tests passing",
            "run_id": "sh-workflow-123",
            "details": {
                "patch_preview": "diff content",
            },
        }

        mock_init_service.return_value = mock_service

        # Webhook を処理
        result = github_webhook(
            payload=pr_payload,
            project_root="/test/project",
            event="pull_request",
            delivery="test-delivery-id",
        )

        # 結果の検証
        assert result["status"] == "fixed"
        assert result["summary"] == "All tests passing"
        assert result["run_id"] == "sh-workflow-123"

        # Guardian レビューが統合されている
        assert result["details"]["guardian_status"] == "approved"
        assert result["details"]["guardian_comment"] == "All changes validated"
        assert result["details"]["model_name"] == "gpt-4"

        # PR コメントをフォーマットできる
        comment = format_pr_comment(
            result,
            repo_full_name="test-owner/test-repo",
            pr_number=123,
        )
        assert comment is not None
