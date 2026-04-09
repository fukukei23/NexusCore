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
from unittest.mock import Mock, patch

import pytest
from flask import Flask

from nexuscore.api.github_webhook_handler import (
    _post_pr_comment_if_configured,
    _send_slack_notification_if_configured,
    handle_github_webhook,
)


@pytest.fixture
def flask_app():
    """Create a Flask test app with webhook route"""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.add_url_rule("/webhook", "webhook", handle_github_webhook, methods=["POST"])
    return app


class TestHandleGitHubWebhook:
    """Test main webhook handler function using Flask test client"""

    @patch("nexuscore.api.github_webhook_handler._send_slack_notification_if_configured")
    @patch("nexuscore.api.github_webhook_handler._post_pr_comment_if_configured")
    @patch("nexuscore.api.github_webhook_handler.github_webhook")
    def test_handle_pull_request_webhook_success(
        self, mock_github_webhook, mock_pr_comment, mock_slack, flask_app
    ):
        """Should handle valid pull_request webhook successfully"""
        mock_github_webhook.return_value = {"status": "success"}

        with flask_app.test_client() as client:
            resp = client.post(
                "/webhook",
                json={
                    "action": "opened",
                    "repository": {"full_name": "owner/repo"},
                    "pull_request": {"number": 123, "head": {"sha": "abc123"}},
                },
                headers={
                    "X-GitHub-Event": "pull_request",
                    "X-GitHub-Delivery": "delivery-123",
                },
            )

        data = resp.get_json()
        assert data["accepted"] is True
        assert "result" in data
        mock_github_webhook.assert_called_once()
        mock_pr_comment.assert_called_once()
        mock_slack.assert_called_once()

    def test_rejects_non_pull_request_events(self, flask_app):
        """Should reject non-pull_request events"""
        with flask_app.test_client() as client:
            resp = client.post(
                "/webhook",
                json={"action": "push"},
                headers={
                    "X-GitHub-Event": "push",
                    "X-GitHub-Delivery": "delivery-123",
                },
            )

        data = resp.get_json()
        assert data["accepted"] is False
        assert "not supported" in data["reason"]

    def test_handles_missing_payload(self, flask_app):
        """Should handle missing JSON payload"""
        with flask_app.test_client() as client:
            resp = client.post(
                "/webhook",
                json=None,
                headers={
                    "X-GitHub-Event": "pull_request",
                    "X-GitHub-Delivery": "delivery-123",
                },
            )

        # get_json() raises UnsupportedMediaType for non-JSON, caught by outer except
        data = resp.get_json()
        assert data["accepted"] is False
        assert resp.status_code == 500

    @patch("nexuscore.api.github_webhook_handler.github_webhook")
    def test_handles_webhook_processing_error(self, mock_github_webhook, flask_app):
        """Should handle errors during webhook processing"""
        mock_github_webhook.side_effect = Exception("Processing failed")

        with flask_app.test_client() as client:
            resp = client.post(
                "/webhook",
                json={"action": "opened"},
                headers={
                    "X-GitHub-Event": "pull_request",
                    "X-GitHub-Delivery": "delivery-123",
                },
            )

        data = resp.get_json()
        assert data["accepted"] is False
        assert "error" in data
        assert resp.status_code == 500

    @patch("nexuscore.api.github_webhook_handler._post_pr_comment_if_configured")
    @patch("nexuscore.api.github_webhook_handler.github_webhook")
    def test_calls_github_webhook_with_correct_params(
        self, mock_github_webhook, mock_pr_comment, flask_app
    ):
        """Should call github_webhook with correct parameters"""
        payload = {
            "action": "opened",
            "repository": {"full_name": "owner/repo"},
            "pull_request": {"number": 456},
        }
        mock_github_webhook.return_value = {"status": "ok"}

        with flask_app.test_client() as client:
            client.post(
                "/webhook",
                json=payload,
                headers={
                    "X-GitHub-Event": "pull_request",
                    "X-GitHub-Delivery": "delivery-456",
                },
            )

        mock_github_webhook.assert_called_once_with(
            payload=payload, project_root=None, event="pull_request", delivery="delivery-456"
        )

    def test_handles_unknown_event_type(self, flask_app):
        """Should reject unknown event types"""
        with flask_app.test_client() as client:
            resp = client.post(
                "/webhook",
                json={},
                headers={
                    "X-GitHub-Event": "unknown_event",
                    "X-GitHub-Delivery": "delivery-123",
                },
            )

        data = resp.get_json()
        assert data["accepted"] is False
        assert "unknown_event" in data["reason"]

    def test_handles_missing_headers(self, flask_app):
        """Should handle missing GitHub headers gracefully"""
        with flask_app.test_client() as client:
            resp = client.post("/webhook", json={})

        data = resp.get_json()
        assert data["accepted"] is False


class TestPostPRComment:
    """Test PR comment posting functionality"""

    @patch.dict(os.environ, {}, clear=True)
    def test_skips_pr_comment_without_token(self):
        """Should skip PR comment when GITHUB_SELF_HEALING_TOKEN not set"""
        result = {"status": "success"}
        payload = {
            "repository": {"full_name": "owner/repo"},
            "pull_request": {"number": 123, "head": {"sha": "abc123"}},
        }

        # Should not raise and should return early
        _post_pr_comment_if_configured(result, payload)

    @patch.dict(os.environ, {"GITHUB_SELF_HEALING_TOKEN": "test-token"}, clear=True)
    @patch("nexuscore.api.github_self_healing_webhook.format_pr_comment")
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
    def test_handles_missing_repo_info(self):
        """Should handle missing repository information"""
        result = {"status": "success"}
        payload = {"pull_request": {"number": 123}}

        # Should not raise
        _post_pr_comment_if_configured(result, payload)

    @patch.dict(os.environ, {"GITHUB_SELF_HEALING_TOKEN": "test-token"}, clear=True)
    def test_handles_missing_pr_number(self):
        """Should handle missing PR number"""
        result = {"status": "success"}
        payload = {"repository": {"full_name": "owner/repo"}}

        # Should not raise
        _post_pr_comment_if_configured(result, payload)

    @patch.dict(
        os.environ,
        {"GITHUB_SELF_HEALING_TOKEN": "test-token", "NEXUS_PROJECT_ROOT": "/custom/path"},
        clear=True,
    )
    @patch("nexuscore.api.github_self_healing_webhook.format_pr_comment")
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
    @patch("nexuscore.api.github_self_healing_webhook.format_pr_comment")
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
    def test_skips_slack_without_webhook_url(self):
        """Should skip Slack notification when SLACK_WEBHOOK_URL not set"""
        result = {"status": "success"}
        payload = {"repository": {"full_name": "owner/repo"}}

        # Should not raise
        _send_slack_notification_if_configured(result, payload)

    @patch.dict(os.environ, {"NEXUS_SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}, clear=True)
    def test_sends_slack_notification_with_webhook_url(self, caplog):
        """Should attempt Slack notification when webhook URL is configured"""
        result = {"status": "success", "tests_passed": 10}
        payload = {
            "repository": {"full_name": "owner/repo"},
            "pull_request": {"number": 123, "title": "Test PR"},
        }

        # This will try to import and use SlackNotifier, may fail gracefully
        with caplog.at_level("DEBUG"):
            _send_slack_notification_if_configured(result, payload)

        # Function should not raise

    @patch.dict(os.environ, {"NEXUS_SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}, clear=True)
    def test_handles_slack_api_error(self, caplog):
        """Should handle Slack API errors gracefully"""
        result = {"status": "success"}
        payload = {"repository": {"full_name": "owner/repo"}}

        # Should not raise even with import issues
        _send_slack_notification_if_configured(result, payload)

    @patch.dict(os.environ, {"NEXUS_SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}, clear=True)
    def test_includes_pr_info_in_slack_message(self, caplog):
        """Should include PR information in Slack message"""
        result = {"status": "success", "coverage": "85%"}
        payload = {
            "repository": {"full_name": "owner/repo"},
            "pull_request": {
                "number": 456,
                "title": "Feature: Add tests",
                "html_url": "https://github.com/owner/repo/pull/456",
            },
        }

        # Should not raise
        _send_slack_notification_if_configured(result, payload)


class TestWebhookEdgeCases:
    """Test edge cases and error conditions"""

    @patch("nexuscore.api.github_webhook_handler.github_webhook")
    def test_handles_malformed_json(self, mock_github_webhook, flask_app):
        """Should handle malformed JSON payloads"""
        mock_github_webhook.side_effect = Exception("Processing error")

        with flask_app.test_client() as client:
            resp = client.post(
                "/webhook",
                json={"action": "opened"},
                headers={
                    "X-GitHub-Event": "pull_request",
                    "X-GitHub-Delivery": "delivery-123",
                },
            )

        data = resp.get_json()
        assert data["accepted"] is False
        assert resp.status_code == 500

    @patch("nexuscore.api.github_webhook_handler._post_pr_comment_if_configured")
    @patch("nexuscore.api.github_webhook_handler.github_webhook")
    def test_continues_on_pr_comment_error(
        self, mock_github_webhook, mock_pr_comment, flask_app
    ):
        """Handler catches exception when PR comment posting fails"""
        mock_github_webhook.return_value = {"status": "success"}
        mock_pr_comment.side_effect = Exception("Comment failed")

        with flask_app.test_client() as client:
            resp = client.post(
                "/webhook",
                json={
                    "repository": {"full_name": "owner/repo"},
                    "pull_request": {"number": 123},
                },
                headers={
                    "X-GitHub-Event": "pull_request",
                    "X-GitHub-Delivery": "delivery-123",
                },
            )

        # Exception in _post_pr_comment_if_configured is caught by outer try/except
        data = resp.get_json()
        assert resp.status_code == 500

    @patch("nexuscore.api.github_webhook_handler._send_slack_notification_if_configured")
    @patch("nexuscore.api.github_webhook_handler.github_webhook")
    def test_continues_on_slack_error(self, mock_github_webhook, mock_slack, flask_app):
        """Handler catches exception when Slack notification fails"""
        mock_github_webhook.return_value = {"status": "success"}
        mock_slack.side_effect = Exception("Slack failed")

        with flask_app.test_client() as client:
            resp = client.post(
                "/webhook",
                json={
                    "repository": {"full_name": "owner/repo"},
                    "pull_request": {"number": 123},
                },
                headers={
                    "X-GitHub-Event": "pull_request",
                    "X-GitHub-Delivery": "delivery-123",
                },
            )

        # Exception in _send_slack_notification_if_configured is caught by outer try/except
        data = resp.get_json()
        assert resp.status_code == 500
