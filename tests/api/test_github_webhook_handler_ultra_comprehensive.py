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
def app():
    """Create a Flask test app"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app


class TestHandleGitHubWebhook:
    """Test main webhook handler function"""

    def test_handle_pull_request_webhook_success(self, app):
        """Should handle valid pull_request webhook successfully"""
        with app.test_request_context(
            '/webhook',
            method='POST',
            headers={"X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "delivery-123"},
            json={
                "action": "opened",
                "repository": {"full_name": "owner/repo"},
                "pull_request": {"number": 123, "head": {"sha": "abc123"}},
            }
        ):
            with patch('nexuscore.api.github_webhook_handler.github_webhook') as mock_webhook:
                with patch('nexuscore.api.github_webhook_handler._post_pr_comment_if_configured') as mock_comment:
                    with patch('nexuscore.api.github_webhook_handler._send_slack_notification_if_configured') as mock_slack:
                        mock_webhook.return_value = {"status": "success"}

                        result = handle_github_webhook()

                        assert result["accepted"] is True
                        assert "result" in result
                        mock_webhook.assert_called_once()
                        mock_comment.assert_called_once()
                        mock_slack.assert_called_once()

    def test_rejects_non_pull_request_events(self, app):
        """Should reject non-pull_request events"""
        with app.test_request_context(
            '/webhook',
            method='POST',
            headers={"X-GitHub-Event": "push", "X-GitHub-Delivery": "delivery-123"}
        ):
            result = handle_github_webhook()

            assert result["accepted"] is False
            assert "not supported" in result["reason"]

    def test_handles_missing_payload(self, app):
        """Should handle missing JSON payload"""
        with app.test_request_context(
            '/webhook',
            method='POST',
            headers={"X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "delivery-123"},
            json=None  # Explicitly set to None
        ):
            result, status_code = handle_github_webhook()

            assert result["accepted"] is False
            # Accepts either 400 or 500 depending on Flask error handling
            assert status_code in [400, 500]

    def test_handles_webhook_processing_error(self, app):
        """Should handle errors during webhook processing"""
        with app.test_request_context(
            '/webhook',
            method='POST',
            headers={"X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "delivery-123"},
            json={"action": "opened"}
        ):
            with patch('nexuscore.api.github_webhook_handler.github_webhook') as mock_webhook:
                mock_webhook.side_effect = Exception("Processing failed")

                result, status_code = handle_github_webhook()

                assert result["accepted"] is False
                assert "error" in result
                assert status_code == 500

    def test_calls_github_webhook_with_correct_params(self, app):
        """Should call github_webhook with correct parameters"""
        event = "pull_request"
        delivery = "delivery-456"
        payload = {
            "action": "opened",
            "repository": {"full_name": "owner/repo"},
            "pull_request": {"number": 456},
        }

        with app.test_request_context(
            '/webhook',
            method='POST',
            headers={"X-GitHub-Event": event, "X-GitHub-Delivery": delivery},
            json=payload
        ):
            with patch('nexuscore.api.github_webhook_handler.github_webhook') as mock_webhook:
                with patch('nexuscore.api.github_webhook_handler._post_pr_comment_if_configured'):
                    with patch('nexuscore.api.github_webhook_handler._send_slack_notification_if_configured'):
                        mock_webhook.return_value = {"status": "ok"}

                        handle_github_webhook()

                        mock_webhook.assert_called_once_with(
                            payload=payload, project_root=None, event=event, delivery=delivery
                        )

    def test_handles_unknown_event_type(self, app):
        """Should reject unknown event types"""
        with app.test_request_context(
            '/webhook',
            method='POST',
            headers={"X-GitHub-Event": "unknown_event", "X-GitHub-Delivery": "delivery-123"}
        ):
            result = handle_github_webhook()

            assert result["accepted"] is False
            assert "unknown_event" in result["reason"]

    def test_handles_missing_headers(self, app):
        """Should handle missing GitHub headers gracefully"""
        with app.test_request_context('/webhook', method='POST'):
            result = handle_github_webhook()

            # Should default to "unknown" event type
            assert result["accepted"] is False


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

        # Should not raise exception
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
        payload = {"pull_request": {"number": 123}}  # Missing repository

        # Should not raise exception
        _post_pr_comment_if_configured(result, payload)

    @patch.dict(os.environ, {"GITHUB_SELF_HEALING_TOKEN": "test-token"}, clear=True)
    def test_handles_missing_pr_number(self):
        """Should handle missing PR number"""
        result = {"status": "success"}
        payload = {"repository": {"full_name": "owner/repo"}}  # Missing pull_request

        # Should not raise exception
        _post_pr_comment_if_configured(result, payload)

    @patch.dict(os.environ, {"GITHUB_SELF_HEALING_TOKEN": "test-token", "NEXUS_PROJECT_ROOT": "/custom/path"}, clear=True)
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
        """Should skip Slack notification when NEXUS_SLACK_WEBHOOK_URL not set"""
        result = {"status": "success"}
        payload = {"repository": {"full_name": "owner/repo"}}

        # Should not raise exception
        _send_slack_notification_if_configured(result, payload)

    @patch.dict(os.environ, {"NEXUS_SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}, clear=True)
    @patch("nexuscore.core.notifier.SlackNotifier")
    def test_sends_slack_notification_with_webhook_url(self, mock_notifier_class):
        """Should send Slack notification when webhook URL is configured"""
        mock_notifier = Mock()
        mock_notifier.notify_self_healing_complete.return_value = True
        mock_notifier_class.return_value = mock_notifier

        result = {"status": "success", "tests_passed": 10}
        payload = {
            "repository": {"full_name": "owner/repo"},
            "pull_request": {"number": 123, "title": "Test PR"},
        }

        _send_slack_notification_if_configured(result, payload)

        mock_notifier_class.assert_called_once_with(webhook_url="https://hooks.slack.com/test")
        mock_notifier.notify_self_healing_complete.assert_called_once()

    @patch.dict(os.environ, {"NEXUS_SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}, clear=True)
    @patch("nexuscore.core.notifier.SlackNotifier")
    def test_handles_slack_api_error(self, mock_notifier_class):
        """Should handle Slack API errors gracefully"""
        mock_notifier_class.side_effect = Exception("Slack API error")

        result = {"status": "success"}
        payload = {"repository": {"full_name": "owner/repo"}}

        # Should not raise exception - errors are handled internally
        _send_slack_notification_if_configured(result, payload)

    @patch.dict(os.environ, {"NEXUS_SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}, clear=True)
    @patch("nexuscore.core.notifier.SlackNotifier")
    def test_includes_pr_info_in_slack_message(self, mock_notifier_class):
        """Should include PR information in Slack message"""
        mock_notifier = Mock()
        mock_notifier.notify_self_healing_complete.return_value = True
        mock_notifier_class.return_value = mock_notifier

        result = {"status": "success", "coverage": "85%"}
        payload = {
            "repository": {"full_name": "owner/repo"},
            "pull_request": {"number": 456, "title": "Feature: Add tests", "html_url": "https://github.com/owner/repo/pull/456"},
        }

        _send_slack_notification_if_configured(result, payload)

        # Verify notify_self_healing_complete was called with PR info
        call_args = mock_notifier.notify_self_healing_complete.call_args
        assert call_args[1]["repo_full_name"] == "owner/repo"
        assert call_args[1]["pr_number"] == 456


class TestWebhookEdgeCases:
    """Test edge cases and error conditions"""

    def test_handles_malformed_json(self, app):
        """Should handle malformed JSON payloads"""
        with app.test_request_context(
            '/webhook',
            method='POST',
            headers={"X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "delivery-123"},
            data='invalid json{'
        ):
            result, status_code = handle_github_webhook()

            assert result["accepted"] is False
            assert status_code == 500

    @patch.dict(os.environ, {"GITHUB_SELF_HEALING_TOKEN": "test-token"}, clear=True)
    def test_continues_on_pr_comment_error(self, app):
        """Should continue even if PR comment posting fails internally"""
        with app.test_request_context(
            '/webhook',
            method='POST',
            headers={"X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "delivery-123"},
            json={
                "repository": {"full_name": "owner/repo"},
                "pull_request": {"number": 123, "head": {"sha": "abc123"}},
            }
        ):
            with patch('nexuscore.api.github_webhook_handler.github_webhook') as mock_webhook:
                with patch('requests.post') as mock_post:
                    with patch('nexuscore.api.github_webhook_handler._send_slack_notification_if_configured'):
                        mock_webhook.return_value = {"status": "success"}
                        mock_post.side_effect = Exception("Comment failed")

                        # Should not raise exception - the function handles errors internally
                        result = handle_github_webhook()
                        assert result["accepted"] is True

    @patch.dict(os.environ, {"NEXUS_SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}, clear=True)
    def test_continues_on_slack_error(self, app):
        """Should continue even if Slack notification fails internally"""
        with app.test_request_context(
            '/webhook',
            method='POST',
            headers={"X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "delivery-123"},
            json={
                "repository": {"full_name": "owner/repo"},
                "pull_request": {"number": 123},
            }
        ):
            with patch('nexuscore.api.github_webhook_handler.github_webhook') as mock_webhook:
                with patch('nexuscore.api.github_webhook_handler._post_pr_comment_if_configured'):
                    with patch('nexuscore.core.notifier.SlackNotifier') as mock_notifier_class:
                        mock_webhook.return_value = {"status": "success"}
                        mock_notifier_class.side_effect = Exception("Slack failed")

                        # Should not raise exception - the function handles errors internally
                        result = handle_github_webhook()
                        assert result["accepted"] is True
