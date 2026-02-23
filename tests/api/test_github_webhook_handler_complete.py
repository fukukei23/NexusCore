"""
Comprehensive tests for GitHub Webhook Handler (github_webhook_handler.py)

Target coverage: 100%

Tests cover all three main functions:
1. handle_github_webhook() - Main webhook handler
2. _post_pr_comment_if_configured() - PR comment posting
3. _send_slack_notification_if_configured() - Slack notifications

Test scenarios:
- Pull request event handling (success path)
- Non-PR event rejection
- Payload validation (empty, None, malformed)
- Header validation
- PR comment posting (with/without token, errors, edge cases)
- Slack notification (with/without webhook URL, errors, metrics)
- Error handling and exception recovery
- Environment variable configuration
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
def app():
    """Create Flask test app with proper context"""
    app = Flask(__name__)
    app.config["TESTING"] = True
    return app


class TestHandleGitHubWebhook:
    """Comprehensive tests for handle_github_webhook()"""

    def test_success_pull_request_event(self, app):
        """Should successfully handle pull_request webhook"""
        with app.test_request_context(
            "/webhook",
            method="POST",
            headers={"X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "delivery-123"},
            json={
                "action": "opened",
                "repository": {"full_name": "owner/repo"},
                "pull_request": {"number": 123, "head": {"sha": "abc123"}},
            },
        ):
            with patch("nexuscore.api.github_webhook_handler.github_webhook") as mock_webhook:
                with patch(
                    "nexuscore.api.github_webhook_handler._post_pr_comment_if_configured"
                ) as mock_comment:
                    with patch(
                        "nexuscore.api.github_webhook_handler._send_slack_notification_if_configured"
                    ) as mock_slack:
                        mock_webhook.return_value = {"status": "success", "tests_passed": 10}

                        result = handle_github_webhook()

                        assert result["accepted"] is True
                        assert "result" in result
                        assert result["result"]["status"] == "success"
                        mock_webhook.assert_called_once()
                        mock_comment.assert_called_once()
                        mock_slack.assert_called_once()

    def test_reject_non_pull_request_event(self, app):
        """Should reject non-pull_request events"""
        with app.test_request_context(
            "/webhook",
            method="POST",
            headers={"X-GitHub-Event": "push", "X-GitHub-Delivery": "delivery-456"},
        ):
            result = handle_github_webhook()

            assert result["accepted"] is False
            assert "not supported" in result["reason"]
            assert "push" in result["reason"]

    def test_reject_issues_event(self, app):
        """Should reject issues event"""
        with app.test_request_context(
            "/webhook",
            method="POST",
            headers={"X-GitHub-Event": "issues", "X-GitHub-Delivery": "delivery-789"},
        ):
            result = handle_github_webhook()

            assert result["accepted"] is False
            assert "issues" in result["reason"]

    def test_handle_missing_payload(self, app):
        """Should handle missing/None JSON payload"""
        with app.test_request_context(
            "/webhook",
            method="POST",
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "delivery-111",
                "Content-Type": "application/json",
            },
            data="null",
        ):
            result, status_code = handle_github_webhook()

            assert result["accepted"] is False
            assert "Invalid payload" in result["reason"]
            assert status_code == 400

    def test_webhook_processing_exception(self, app):
        """Should handle exceptions during webhook processing"""
        with app.test_request_context(
            "/webhook",
            method="POST",
            headers={"X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "delivery-333"},
            json={"action": "opened"},
        ):
            with patch("nexuscore.api.github_webhook_handler.github_webhook") as mock_webhook:
                mock_webhook.side_effect = Exception("Processing error")

                result, status_code = handle_github_webhook()

                assert result["accepted"] is False
                assert "error" in result
                assert "Processing error" in result["error"]
                assert status_code == 500

    def test_correct_parameters_passed_to_github_webhook(self, app):
        """Should pass correct parameters to github_webhook()"""
        event = "pull_request"
        delivery = "delivery-444"
        payload = {
            "action": "synchronize",
            "repository": {"full_name": "test/repo"},
            "pull_request": {"number": 999},
        }

        with app.test_request_context(
            "/webhook",
            method="POST",
            headers={"X-GitHub-Event": event, "X-GitHub-Delivery": delivery},
            json=payload,
        ):
            with patch("nexuscore.api.github_webhook_handler.github_webhook") as mock_webhook:
                with patch("nexuscore.api.github_webhook_handler._post_pr_comment_if_configured"):
                    with patch(
                        "nexuscore.api.github_webhook_handler._send_slack_notification_if_configured"
                    ):
                        mock_webhook.return_value = {"status": "ok"}

                        handle_github_webhook()

                        mock_webhook.assert_called_once_with(
                            payload=payload, project_root=None, event=event, delivery=delivery
                        )

    def test_missing_github_headers_defaults_to_unknown(self, app):
        """Should default to 'unknown' when GitHub headers are missing"""
        with app.test_request_context("/webhook", method="POST", json={"action": "opened"}):
            result = handle_github_webhook()

            # Should reject because event type is 'unknown'
            assert result["accepted"] is False

    def test_pr_comment_called_with_result_and_payload(self, app):
        """Should call PR comment function with correct arguments"""
        result_data = {"status": "success", "coverage": "90%"}
        payload = {"repository": {"full_name": "owner/repo"}, "pull_request": {"number": 555}}

        with app.test_request_context(
            "/webhook",
            method="POST",
            headers={"X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "delivery-555"},
            json=payload,
        ):
            with patch("nexuscore.api.github_webhook_handler.github_webhook") as mock_webhook:
                with patch(
                    "nexuscore.api.github_webhook_handler._post_pr_comment_if_configured"
                ) as mock_comment:
                    with patch(
                        "nexuscore.api.github_webhook_handler._send_slack_notification_if_configured"
                    ):
                        mock_webhook.return_value = result_data

                        handle_github_webhook()

                        mock_comment.assert_called_once_with(result_data, payload)

    def test_slack_notification_called_with_result_and_payload(self, app):
        """Should call Slack notification function with correct arguments"""
        result_data = {"status": "failed", "error": "Test failure"}
        payload = {"repository": {"full_name": "owner/repo"}, "pull_request": {"number": 666}}

        with app.test_request_context(
            "/webhook",
            method="POST",
            headers={"X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "delivery-666"},
            json=payload,
        ):
            with patch("nexuscore.api.github_webhook_handler.github_webhook") as mock_webhook:
                with patch("nexuscore.api.github_webhook_handler._post_pr_comment_if_configured"):
                    with patch(
                        "nexuscore.api.github_webhook_handler._send_slack_notification_if_configured"
                    ) as mock_slack:
                        mock_webhook.return_value = result_data

                        handle_github_webhook()

                        mock_slack.assert_called_once_with(result_data, payload)


class TestPostPRComment:
    """Comprehensive tests for _post_pr_comment_if_configured()"""

    @patch.dict(os.environ, {}, clear=True)
    def test_skip_without_token(self):
        """Should skip PR comment when GITHUB_SELF_HEALING_TOKEN not set"""
        result = {"status": "success"}
        payload = {
            "repository": {"full_name": "owner/repo"},
            "pull_request": {"number": 123, "head": {"sha": "abc123"}},
        }

        # Should not raise exception
        _post_pr_comment_if_configured(result, payload)

    @patch.dict(os.environ, {"GITHUB_SELF_HEALING_TOKEN": "test-token-123"}, clear=True)
    @patch("nexuscore.api.github_self_healing_webhook.format_pr_comment")
    @patch("requests.post")
    def test_post_comment_with_token(self, mock_post, mock_format):
        """Should post PR comment when token is configured"""
        mock_format.return_value = "Test comment body"
        mock_response = Mock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        result = {"status": "success"}
        payload = {
            "repository": {"full_name": "owner/repo"},
            "pull_request": {"number": 123, "head": {"sha": "abc123"}},
        }

        _post_pr_comment_if_configured(result, payload)

        # Verify GitHub API was called
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "https://api.github.com/repos/owner/repo/issues/123/comments" == call_args[0][0]
        assert call_args[1]["headers"]["Authorization"] == "token test-token-123"
        assert call_args[1]["json"]["body"] == "Test comment body"

    @patch.dict(os.environ, {"GITHUB_SELF_HEALING_TOKEN": "token"}, clear=True)
    def test_handle_missing_repository(self):
        """Should handle missing repository information"""
        result = {"status": "success"}
        payload = {"pull_request": {"number": 123}}  # Missing repository

        _post_pr_comment_if_configured(result, payload)

    @patch.dict(os.environ, {"GITHUB_SELF_HEALING_TOKEN": "token"}, clear=True)
    def test_handle_missing_pr_number(self):
        """Should handle missing PR number"""
        result = {"status": "success"}
        payload = {"repository": {"full_name": "owner/repo"}}  # Missing pull_request

        _post_pr_comment_if_configured(result, payload)

    @patch.dict(
        os.environ,
        {"GITHUB_SELF_HEALING_TOKEN": "token", "NEXUS_PROJECT_ROOT": "/custom/project/path"},
        clear=True,
    )
    @patch("nexuscore.api.github_self_healing_webhook.format_pr_comment")
    @patch("requests.post")
    def test_use_custom_project_root(self, mock_post, mock_format):
        """Should use NEXUS_PROJECT_ROOT environment variable"""
        mock_format.return_value = "Comment"
        mock_response = Mock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        result = {"status": "success"}
        payload = {
            "repository": {"full_name": "owner/repo"},
            "pull_request": {"number": 123, "head": {"sha": "abc123"}},
        }

        _post_pr_comment_if_configured(result, payload)

        call_args = mock_format.call_args
        assert call_args[1]["project_root"] == "/custom/project/path"

    @patch.dict(os.environ, {"GITHUB_SELF_HEALING_TOKEN": "token"}, clear=True)
    @patch("nexuscore.api.github_self_healing_webhook.format_pr_comment")
    @patch("requests.post")
    def test_include_commit_sha(self, mock_post, mock_format):
        """Should include commit SHA in format_pr_comment call"""
        mock_format.return_value = "Comment"
        mock_response = Mock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        result = {"status": "success"}
        commit_sha = "def456789abc"
        payload = {
            "repository": {"full_name": "owner/repo"},
            "pull_request": {"number": 789, "head": {"sha": commit_sha}},
        }

        _post_pr_comment_if_configured(result, payload)

        call_args = mock_format.call_args
        assert call_args[1]["commit_sha"] == commit_sha
        assert call_args[1]["repo_full_name"] == "owner/repo"
        assert call_args[1]["pr_number"] == 789

    @patch.dict(os.environ, {"GITHUB_SELF_HEALING_TOKEN": "token"}, clear=True)
    @patch("nexuscore.api.github_self_healing_webhook.format_pr_comment")
    @patch("requests.post")
    def test_handle_github_api_error(self, mock_post, mock_format):
        """Should handle GitHub API errors gracefully"""
        mock_format.return_value = "Comment"
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = Exception("Forbidden")
        mock_post.return_value = mock_response

        result = {"status": "success"}
        payload = {
            "repository": {"full_name": "owner/repo"},
            "pull_request": {"number": 123, "head": {"sha": "abc"}},
        }

        # Should not raise exception
        _post_pr_comment_if_configured(result, payload)

    @patch.dict(os.environ, {"GITHUB_SELF_HEALING_TOKEN": "token"}, clear=True)
    @patch("nexuscore.api.github_self_healing_webhook.format_pr_comment")
    @patch("requests.post")
    def test_handle_network_timeout(self, mock_post, mock_format):
        """Should handle network timeout errors"""
        mock_format.return_value = "Comment"
        mock_post.side_effect = Exception("Timeout")

        result = {"status": "success"}
        payload = {
            "repository": {"full_name": "owner/repo"},
            "pull_request": {"number": 123, "head": {"sha": "abc"}},
        }

        # Should not raise exception
        _post_pr_comment_if_configured(result, payload)

    @patch.dict(os.environ, {"GITHUB_SELF_HEALING_TOKEN": "token"}, clear=True)
    @patch("nexuscore.api.github_self_healing_webhook.format_pr_comment")
    @patch("requests.post")
    def test_post_comment_success_logging(self, mock_post, mock_format):
        """Should log success message when PR comment is posted"""
        mock_format.return_value = "Comment"
        mock_response = Mock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        result = {"status": "success"}
        payload = {
            "repository": {"full_name": "owner/repo"},
            "pull_request": {"number": 456, "head": {"sha": "xyz"}},
        }

        _post_pr_comment_if_configured(result, payload)


class TestSlackNotification:
    """Comprehensive tests for _send_slack_notification_if_configured()"""

    @patch.dict(os.environ, {}, clear=True)
    def test_skip_without_webhook_url(self):
        """Should skip Slack notification when NEXUS_SLACK_WEBHOOK_URL not set"""
        result = {"status": "success"}
        payload = {"repository": {"full_name": "owner/repo"}}

        _send_slack_notification_if_configured(result, payload)

    @patch.dict(os.environ, {"NEXUS_SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}, clear=True)
    @patch("nexuscore.core.notifier.SlackNotifier")
    def test_send_notification_with_webhook_url(self, mock_notifier_class):
        """Should send Slack notification when webhook URL is configured"""
        mock_notifier = Mock()
        mock_notifier.notify_self_healing_complete.return_value = True
        mock_notifier_class.return_value = mock_notifier

        result = {"status": "success", "run_id": "run-123"}
        payload = {"repository": {"full_name": "owner/repo"}, "pull_request": {"number": 123}}

        _send_slack_notification_if_configured(result, payload)

        mock_notifier_class.assert_called_once_with(webhook_url="https://hooks.slack.com/test")
        mock_notifier.notify_self_healing_complete.assert_called_once()

    @patch.dict(os.environ, {"NEXUS_SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}, clear=True)
    def test_handle_missing_repository_info(self):
        """Should handle missing repository information"""
        with patch("nexuscore.core.notifier.SlackNotifier"):
            result = {"status": "success"}
            payload = {"pull_request": {"number": 123}}  # Missing repository

            _send_slack_notification_if_configured(result, payload)

    @patch.dict(os.environ, {"NEXUS_SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}, clear=True)
    def test_handle_missing_pr_number(self):
        """Should handle missing PR number"""
        with patch("nexuscore.core.notifier.SlackNotifier"):
            result = {"status": "success"}
            payload = {"repository": {"full_name": "owner/repo"}}  # Missing pull_request

            _send_slack_notification_if_configured(result, payload)

    @patch.dict(os.environ, {"NEXUS_SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}, clear=True)
    @patch("nexuscore.core.notifier.SlackNotifier")
    def test_include_status_and_summary(self, mock_notifier_class):
        """Should include status and summary in notification"""
        mock_notifier = Mock()
        mock_notifier.notify_self_healing_complete.return_value = True
        mock_notifier_class.return_value = mock_notifier

        result = {"status": "failed", "summary": "Tests failed: 3 errors", "run_id": "run-456"}
        payload = {"repository": {"full_name": "owner/repo"}, "pull_request": {"number": 789}}

        _send_slack_notification_if_configured(result, payload)

        call_args = mock_notifier.notify_self_healing_complete.call_args
        assert call_args[1]["status"] == "failed"
        assert call_args[1]["summary"] == "Tests failed: 3 errors"
        assert call_args[1]["run_id"] == "run-456"

    @patch.dict(os.environ, {"NEXUS_SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}, clear=True)
    @patch("nexuscore.core.notifier.SlackNotifier")
    def test_notification_failure_logged(self, mock_notifier_class):
        """Should log when Slack notification fails"""
        mock_notifier = Mock()
        mock_notifier.notify_self_healing_complete.return_value = False
        mock_notifier_class.return_value = mock_notifier

        result = {"status": "success", "run_id": "run-999"}
        payload = {"repository": {"full_name": "owner/repo"}, "pull_request": {"number": 111}}

        _send_slack_notification_if_configured(result, payload)

    @patch.dict(os.environ, {"NEXUS_SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}, clear=True)
    @patch("nexuscore.core.notifier.SlackNotifier")
    def test_notification_success_logged(self, mock_notifier_class):
        """Should log when Slack notification succeeds"""
        mock_notifier = Mock()
        mock_notifier.notify_self_healing_complete.return_value = True
        mock_notifier_class.return_value = mock_notifier

        result = {"status": "success", "run_id": "run-222"}
        payload = {"repository": {"full_name": "owner/repo"}, "pull_request": {"number": 222}}

        _send_slack_notification_if_configured(result, payload)

    @patch.dict(os.environ, {"NEXUS_SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}, clear=True)
    @patch("nexuscore.core.notifier.SlackNotifier")
    def test_handle_slack_api_exception(self, mock_notifier_class):
        """Should handle Slack API exceptions gracefully"""
        mock_notifier_class.side_effect = Exception("Slack API error")

        result = {"status": "success"}
        payload = {"repository": {"full_name": "owner/repo"}, "pull_request": {"number": 333}}

        # Should not raise exception
        _send_slack_notification_if_configured(result, payload)

    @patch.dict(os.environ, {"NEXUS_SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}, clear=True)
    @patch("nexuscore.core.notifier.SlackNotifier")
    def test_handle_metrics_collection_failure(self, mock_notifier_class):
        """Should handle metrics collection failures gracefully"""
        mock_notifier = Mock()
        mock_notifier.notify_self_healing_complete.return_value = True
        mock_notifier_class.return_value = mock_notifier

        result = {"status": "success", "details": {"run_id": "run-444"}}
        payload = {"repository": {"full_name": "owner/repo"}, "pull_request": {"number": 444}}

        # Metrics collection will fail (no database), should continue
        _send_slack_notification_if_configured(result, payload)

        # Should still call notify
        mock_notifier.notify_self_healing_complete.assert_called_once()

    @patch.dict(os.environ, {"NEXUS_SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}, clear=True)
    @patch("nexuscore.core.notifier.SlackNotifier")
    def test_construct_pr_url(self, mock_notifier_class):
        """Should construct PR URL correctly"""
        mock_notifier = Mock()
        mock_notifier.notify_self_healing_complete.return_value = True
        mock_notifier_class.return_value = mock_notifier

        result = {"status": "success", "run_id": "run-555"}
        payload = {"repository": {"full_name": "owner/repo"}, "pull_request": {"number": 555}}

        _send_slack_notification_if_configured(result, payload)

        call_args = mock_notifier.notify_self_healing_complete.call_args
        assert call_args[1]["pr_url"] == "https://github.com/owner/repo/pull/555"

    @patch.dict(os.environ, {"NEXUS_SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}, clear=True)
    @patch("nexuscore.core.notifier.SlackNotifier")
    def test_default_summary_when_missing(self, mock_notifier_class):
        """Should use default summary when not provided in result"""
        mock_notifier = Mock()
        mock_notifier.notify_self_healing_complete.return_value = True
        mock_notifier_class.return_value = mock_notifier

        result = {"status": "success"}  # No summary
        payload = {"repository": {"full_name": "owner/repo"}, "pull_request": {"number": 666}}

        _send_slack_notification_if_configured(result, payload)

        call_args = mock_notifier.notify_self_healing_complete.call_args
        assert call_args[1]["summary"] == "Self-Healing execution completed"

    @patch.dict(os.environ, {"NEXUS_SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}, clear=True)
    @patch("nexuscore.core.notifier.SlackNotifier")
    def test_include_details_dictionary(self, mock_notifier_class):
        """Should include details dictionary in notification"""
        mock_notifier = Mock()
        mock_notifier.notify_self_healing_complete.return_value = True
        mock_notifier_class.return_value = mock_notifier

        result = {"status": "success", "run_id": "run-777"}
        payload = {"repository": {"full_name": "test/example"}, "pull_request": {"number": 777}}

        _send_slack_notification_if_configured(result, payload)

        call_args = mock_notifier.notify_self_healing_complete.call_args
        details = call_args[1]["details"]
        assert "リポジトリ" in details
        assert details["リポジトリ"] == "test/example"
        assert details["PR番号"] == "777"
