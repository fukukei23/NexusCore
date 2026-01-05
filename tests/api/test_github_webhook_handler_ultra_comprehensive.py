"""
Ultra-comprehensive tests for GitHub Webhook Handler

Tests cover:
- Pull request event handling
- Non-PR event rejection
- Payload validation
- PR comment posting
- Slack notifications
- Error handling
- Header validation
"""
import os
import pytest
from unittest.mock import Mock, MagicMock, patch, call
from flask import Flask
from nexuscore.api.github_webhook_handler import (
    handle_github_webhook,
    _post_pr_comment_if_configured,
    _send_slack_notification_if_configured,
)


@pytest.fixture
def flask_app():
    """Create a Flask test app"""
    app = Flask(__name__)
    return app


@pytest.fixture
def mock_request():
    """Create a mock Flask request"""
    mock = Mock()
    mock.headers = {"X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "test-delivery-123"}
    mock.get_json.return_value = {
        "action": "opened",
        "repository": {"full_name": "owner/repo"},
        "pull_request": {
            "number": 123,
            "head": {"sha": "abc123def456"},
            "title": "Test PR",
        },
    }
    return mock


class TestHandleGitHubWebhook:
    """Test main webhook handler function"""

    @patch("nexuscore.api.github_webhook_handler.request")
    @patch("nexuscore.api.github_webhook_handler.github_webhook")
    @patch("nexuscore.api.github_webhook_handler._post_pr_comment_if_configured")
    @patch("nexuscore.api.github_webhook_handler._send_slack_notification_if_configured")
    def test_handle_pull_request_webhook_success(
        self, mock_slack, mock_pr_comment, mock_github_webhook, mock_request_patch
    ):
        """Should handle valid pull_request webhook successfully"""
        mock_request_patch.headers = {"X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "delivery-123"}
        mock_request_patch.get_json.return_value = {
            "action": "opened",
            "repository": {"full_name": "owner/repo"},
            "pull_request": {"number": 123, "head": {"sha": "abc123"}},
        }
        mock_github_webhook.return_value = {"status": "success"}

        result = handle_github_webhook()

        assert result["accepted"] is True
        assert "result" in result
        mock_github_webhook.assert_called_once()
        mock_pr_comment.assert_called_once()
        mock_slack.assert_called_once()

    @patch("nexuscore.api.github_webhook_handler.request")
    def test_rejects_non_pull_request_events(self, mock_request_patch):
        """Should reject non-pull_request events"""
        mock_request_patch.headers = {"X-GitHub-Event": "push", "X-GitHub-Delivery": "delivery-123"}

        result = handle_github_webhook()

        assert result["accepted"] is False
        assert "not supported" in result["reason"]

    @patch("nexuscore.api.github_webhook_handler.request")
    def test_handles_missing_payload(self, mock_request_patch):
        """Should handle missing JSON payload"""
        mock_request_patch.headers = {"X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "delivery-123"}
        mock_request_patch.get_json.return_value = None

        result, status_code = handle_github_webhook()

        assert result["accepted"] is False
        assert "Invalid payload" in result["reason"]
        assert status_code == 400

    @patch("nexuscore.api.github_webhook_handler.request")
    @patch("nexuscore.api.github_webhook_handler.github_webhook")
    def test_handles_webhook_processing_error(self, mock_github_webhook, mock_request_patch):
        """Should handle errors during webhook processing"""
        mock_request_patch.headers = {"X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "delivery-123"}
        mock_request_patch.get_json.return_value = {"action": "opened"}
        mock_github_webhook.side_effect = Exception("Processing failed")

        result, status_code = handle_github_webhook()

        assert result["accepted"] is False
        assert "error" in result
        assert status_code == 500

    @patch("nexuscore.api.github_webhook_handler.request")
    @patch("nexuscore.api.github_webhook_handler.github_webhook")
    @patch("nexuscore.api.github_webhook_handler._post_pr_comment_if_configured")
    def test_calls_github_webhook_with_correct_params(
        self, mock_pr_comment, mock_github_webhook, mock_request_patch
    ):
        """Should call github_webhook with correct parameters"""
        event = "pull_request"
        delivery = "delivery-456"
        payload = {
            "action": "opened",
            "repository": {"full_name": "owner/repo"},
            "pull_request": {"number": 456},
        }

        mock_request_patch.headers = {"X-GitHub-Event": event, "X-GitHub-Delivery": delivery}
        mock_request_patch.get_json.return_value = payload
        mock_github_webhook.return_value = {"status": "ok"}

        handle_github_webhook()

        mock_github_webhook.assert_called_once_with(
            payload=payload, project_root=None, event=event, delivery=delivery
        )

    @patch("nexuscore.api.github_webhook_handler.request")
    def test_handles_unknown_event_type(self, mock_request_patch):
        """Should reject unknown event types"""
        mock_request_patch.headers = {"X-GitHub-Event": "unknown_event", "X-GitHub-Delivery": "delivery-123"}

        result = handle_github_webhook()

        assert result["accepted"] is False
        assert "unknown_event" in result["reason"]

    @patch("nexuscore.api.github_webhook_handler.request")
    def test_handles_missing_headers(self, mock_request_patch):
        """Should handle missing GitHub headers gracefully"""
        mock_request_patch.headers = {}
        mock_request_patch.headers.get = Mock(return_value="unknown")

        result = handle_github_webhook()

        # Should default to "unknown" event type
        assert result["accepted"] is False


class TestPostPRComment:
    """Test PR comment posting functionality"""

    @patch.dict(os.environ, {}, clear=True)
    def test_skips_pr_comment_without_token(self, caplog):
        """Should skip PR comment when GITHUB_SELF_HEALING_TOKEN not set"""
        result = {"status": "success"}
        payload = {
            "repository": {"full_name": "owner/repo"},
            "pull_request": {"number": 123, "head": {"sha": "abc123"}},
        }

        _post_pr_comment_if_configured(result, payload)

        assert "GITHUB_SELF_HEALING_TOKEN not set" in caplog.text

    @patch.dict(os.environ, {"GITHUB_SELF_HEALING_TOKEN": "test-token"}, clear=True)
    @patch("nexuscore.api.github_webhook_handler.format_pr_comment")
    @patch("requests.post")
    def test_posts_pr_comment_with_token(self, mock_post, mock_format_comment):
        """Should post PR comment when token is configured"""
        mock_format_comment.return_value = "Test comment"
        mock_response = Mock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        result = {"status": "success"}
        payload = {
            "repository": {"full_name": "owner/repo"},
            "pull_request": {"number": 123, "head": {"sha": "abc123"}},
        }

        _post_pr_comment_if_configured(result, payload)

        mock_format_comment.assert_called_once()

    @patch.dict(os.environ, {"GITHUB_SELF_HEALING_TOKEN": "test-token"}, clear=True)
    def test_handles_missing_repo_info(self, caplog):
        """Should handle missing repository information"""
        result = {"status": "success"}
        payload = {"pull_request": {"number": 123}}  # Missing repository

        _post_pr_comment_if_configured(result, payload)

        assert "Cannot post PR comment" in caplog.text

    @patch.dict(os.environ, {"GITHUB_SELF_HEALING_TOKEN": "test-token"}, clear=True)
    def test_handles_missing_pr_number(self, caplog):
        """Should handle missing PR number"""
        result = {"status": "success"}
        payload = {"repository": {"full_name": "owner/repo"}}  # Missing pull_request

        _post_pr_comment_if_configured(result, payload)

        assert "Cannot post PR comment" in caplog.text

    @patch.dict(os.environ, {"GITHUB_SELF_HEALING_TOKEN": "test-token", "NEXUS_PROJECT_ROOT": "/custom/path"}, clear=True)
    @patch("nexuscore.api.github_webhook_handler.format_pr_comment")
    @patch("requests.post")
    def test_uses_custom_project_root(self, mock_post, mock_format_comment):
        """Should use NEXUS_PROJECT_ROOT environment variable"""
        mock_format_comment.return_value = "Test comment"
        mock_response = Mock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        result = {"status": "success"}
        payload = {
            "repository": {"full_name": "owner/repo"},
            "pull_request": {"number": 123, "head": {"sha": "abc123"}},
        }

        _post_pr_comment_if_configured(result, payload)

        call_args = mock_format_comment.call_args
        assert call_args[1]["project_root"] == "/custom/path"

    @patch.dict(os.environ, {"GITHUB_SELF_HEALING_TOKEN": "test-token"}, clear=True)
    @patch("nexuscore.api.github_webhook_handler.format_pr_comment")
    @patch("requests.post")
    def test_includes_commit_sha_in_comment(self, mock_post, mock_format_comment):
        """Should include commit SHA in PR comment"""
        mock_format_comment.return_value = "Test comment"
        mock_response = Mock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        result = {"status": "success"}
        commit_sha = "abc123def456"
        payload = {
            "repository": {"full_name": "owner/repo"},
            "pull_request": {"number": 123, "head": {"sha": commit_sha}},
        }

        _post_pr_comment_if_configured(result, payload)

        call_args = mock_format_comment.call_args
        assert call_args[1]["commit_sha"] == commit_sha


class TestSlackNotification:
    """Test Slack notification functionality"""

    @patch.dict(os.environ, {}, clear=True)
    def test_skips_slack_without_webhook_url(self, caplog):
        """Should skip Slack notification when SLACK_WEBHOOK_URL not set"""
        result = {"status": "success"}
        payload = {"repository": {"full_name": "owner/repo"}}

        _send_slack_notification_if_configured(result, payload)

        assert "SLACK_WEBHOOK_URL not set" in caplog.text

    @patch.dict(os.environ, {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}, clear=True)
    @patch("requests.post")
    def test_sends_slack_notification_with_webhook_url(self, mock_post):
        """Should send Slack notification when webhook URL is configured"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = {"status": "success", "tests_passed": 10}
        payload = {
            "repository": {"full_name": "owner/repo"},
            "pull_request": {"number": 123, "title": "Test PR"},
        }

        _send_slack_notification_if_configured(result, payload)

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://hooks.slack.com/test"

    @patch.dict(os.environ, {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}, clear=True)
    @patch("requests.post")
    def test_handles_slack_api_error(self, mock_post, caplog):
        """Should handle Slack API errors gracefully"""
        mock_post.side_effect = Exception("Slack API error")

        result = {"status": "success"}
        payload = {"repository": {"full_name": "owner/repo"}}

        _send_slack_notification_if_configured(result, payload)

        # Should log error but not raise
        assert "Failed to send Slack notification" in caplog.text

    @patch.dict(os.environ, {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}, clear=True)
    @patch("requests.post")
    def test_includes_pr_info_in_slack_message(self, mock_post):
        """Should include PR information in Slack message"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = {"status": "success", "coverage": "85%"}
        payload = {
            "repository": {"full_name": "owner/repo"},
            "pull_request": {"number": 456, "title": "Feature: Add tests", "html_url": "https://github.com/owner/repo/pull/456"},
        }

        _send_slack_notification_if_configured(result, payload)

        call_args = mock_post.call_args
        posted_data = call_args[1]["json"]

        # Verify message includes PR details
        assert "456" in str(posted_data) or "Feature: Add tests" in str(posted_data)


class TestWebhookEdgeCases:
    """Test edge cases and error conditions"""

    @patch("nexuscore.api.github_webhook_handler.request")
    @patch("nexuscore.api.github_webhook_handler.github_webhook")
    def test_handles_malformed_json(self, mock_github_webhook, mock_request_patch):
        """Should handle malformed JSON payloads"""
        mock_request_patch.headers = {"X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "delivery-123"}
        mock_request_patch.get_json.side_effect = ValueError("Invalid JSON")

        result, status_code = handle_github_webhook()

        assert result["accepted"] is False
        assert status_code == 500

    @patch("nexuscore.api.github_webhook_handler.request")
    @patch("nexuscore.api.github_webhook_handler.github_webhook")
    @patch("nexuscore.api.github_webhook_handler._post_pr_comment_if_configured")
    def test_continues_on_pr_comment_error(
        self, mock_pr_comment, mock_github_webhook, mock_request_patch
    ):
        """Should continue even if PR comment posting fails"""
        mock_request_patch.headers = {"X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "delivery-123"}
        mock_request_patch.get_json.return_value = {
            "repository": {"full_name": "owner/repo"},
            "pull_request": {"number": 123},
        }
        mock_github_webhook.return_value = {"status": "success"}
        mock_pr_comment.side_effect = Exception("Comment failed")

        # Should not raise exception
        result = handle_github_webhook()
        assert result["accepted"] is True

    @patch("nexuscore.api.github_webhook_handler.request")
    @patch("nexuscore.api.github_webhook_handler.github_webhook")
    @patch("nexuscore.api.github_webhook_handler._send_slack_notification_if_configured")
    def test_continues_on_slack_error(
        self, mock_slack, mock_github_webhook, mock_request_patch
    ):
        """Should continue even if Slack notification fails"""
        mock_request_patch.headers = {"X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "delivery-123"}
        mock_request_patch.get_json.return_value = {
            "repository": {"full_name": "owner/repo"},
            "pull_request": {"number": 123},
        }
        mock_github_webhook.return_value = {"status": "success"}
        mock_slack.side_effect = Exception("Slack failed")

        # Should not raise exception
        result = handle_github_webhook()
        assert result["accepted"] is True
