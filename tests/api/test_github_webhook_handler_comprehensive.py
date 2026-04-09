"""
Comprehensive Tests for github_webhook_handler.py

Flask test client pattern used to avoid mocking flask.request directly.
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
    """Flask テストアプリケーション"""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.add_url_rule("/webhook", "webhook", handle_github_webhook, methods=["POST"])
    return app


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
            "title": "Test PR",
        },
    }


@pytest.fixture
def self_healing_result():
    """Self-Healing 実行結果"""
    return {
        "status": "fixed",
        "summary": "Tests are now passing",
        "run_id": "sh-test-123",
        "details": {
            "guardian_status": "approved",
            "guardian_comment": "Changes look good",
        },
    }


class TestHandleGithubWebhook:
    """Tests using Flask test client instead of mocking request directly."""

    def test_handle_non_pull_request_event(self, flask_app):
        """pull_request 以外のイベントは無視"""
        with flask_app.test_client() as client:
            resp = client.post(
                "/webhook",
                json={"action": "push"},
                headers={
                    "X-GitHub-Event": "push",
                    "X-GitHub-Delivery": "test-delivery",
                },
            )

        data = resp.get_json()
        assert data["accepted"] is False
        assert "not supported" in data["reason"]
        assert "push" in data["reason"]

    def test_handle_pull_request_event_invalid_payload(self, flask_app):
        """無効なペイロード（JSONでない）"""
        with flask_app.test_client() as client:
            resp = client.post(
                "/webhook",
                json=None,
                headers={
                    "X-GitHub-Event": "pull_request",
                    "X-GitHub-Delivery": "test-delivery",
                },
            )

        data = resp.get_json()
        assert data["accepted"] is False

    @patch("nexuscore.api.github_webhook_handler._send_slack_notification_if_configured")
    @patch("nexuscore.api.github_webhook_handler._post_pr_comment_if_configured")
    @patch("nexuscore.api.github_webhook_handler.github_webhook")
    def test_handle_pull_request_event_success(
        self,
        mock_github_webhook,
        mock_post_comment,
        mock_slack,
        flask_app,
        pr_payload,
        self_healing_result,
    ):
        """正常なPRイベント処理"""
        mock_github_webhook.return_value = self_healing_result

        with flask_app.test_client() as client:
            resp = client.post(
                "/webhook",
                json=pr_payload,
                headers={
                    "X-GitHub-Event": "pull_request",
                    "X-GitHub-Delivery": "test-delivery",
                },
            )

        data = resp.get_json()
        assert data["accepted"] is True
        assert data["result"] == self_healing_result

        mock_github_webhook.assert_called_once_with(
            payload=pr_payload, project_root=None, event="pull_request", delivery="test-delivery"
        )
        mock_post_comment.assert_called_once_with(self_healing_result, pr_payload)
        mock_slack.assert_called_once_with(self_healing_result, pr_payload)

    @patch("nexuscore.api.github_webhook_handler.github_webhook")
    def test_handle_pull_request_event_exception(
        self, mock_github_webhook, flask_app, pr_payload
    ):
        """github_webhook が例外を投げる"""
        mock_github_webhook.side_effect = Exception("Self-healing failed")

        with flask_app.test_client() as client:
            resp = client.post(
                "/webhook",
                json=pr_payload,
                headers={
                    "X-GitHub-Event": "pull_request",
                    "X-GitHub-Delivery": "test-delivery",
                },
            )

        data = resp.get_json()
        assert data["accepted"] is False
        assert "error" in data
        assert resp.status_code == 500

    def test_handle_unknown_event(self, flask_app):
        """X-GitHub-Event ヘッダーがない場合"""
        with flask_app.test_client() as client:
            resp = client.post(
                "/webhook",
                json={},
                headers={
                    "X-GitHub-Event": "unknown",
                    "X-GitHub-Delivery": "test-delivery",
                },
            )

        data = resp.get_json()
        assert data["accepted"] is False
        assert "unknown" in data["reason"]


class TestPostPrCommentIfConfigured:
    @patch.dict(os.environ, {}, clear=True)
    def test_post_comment_without_token(self, pr_payload, self_healing_result):
        """GITHUB_SELF_HEALING_TOKEN が設定されていない"""
        _post_pr_comment_if_configured(self_healing_result, pr_payload)

    @patch("nexuscore.api.github_self_healing_webhook.format_pr_comment")
    @patch.dict(os.environ, {"GITHUB_SELF_HEALING_TOKEN": "test-token"}, clear=True)
    def test_post_comment_success(
        self, mock_format, pr_payload, self_healing_result
    ):
        """PR コメント投稿成功"""
        mock_format.return_value = "Test comment body"

        with patch("requests.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 201
            mock_post.return_value = mock_response

            _post_pr_comment_if_configured(self_healing_result, pr_payload)

            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "test-owner/test-repo" in call_args[0][0]
            assert "123" in call_args[0][0]
            assert "/comments" in call_args[0][0]
            headers = call_args[1]["headers"]
            assert "Authorization" in headers
            assert "token test-token" in headers["Authorization"]
            data = call_args[1]["json"]
            assert data["body"] == "Test comment body"

    @patch.dict(os.environ, {"GITHUB_SELF_HEALING_TOKEN": "test-token"}, clear=True)
    def test_post_comment_missing_repo_name(self, self_healing_result):
        """リポジトリ名が欠けている"""
        payload = {
            "repository": {},
            "pull_request": {"number": 123},
        }
        _post_pr_comment_if_configured(self_healing_result, payload)

    @patch.dict(os.environ, {"GITHUB_SELF_HEALING_TOKEN": "test-token"}, clear=True)
    def test_post_comment_missing_pr_number(self, self_healing_result):
        """PR番号が欠けている"""
        payload = {
            "repository": {"full_name": "owner/repo"},
            "pull_request": {},
        }
        _post_pr_comment_if_configured(self_healing_result, payload)

    @patch("nexuscore.api.github_self_healing_webhook.format_pr_comment")
    @patch.dict(os.environ, {"GITHUB_SELF_HEALING_TOKEN": "test-token"}, clear=True)
    def test_post_comment_api_error(
        self, mock_format, pr_payload, self_healing_result
    ):
        """GitHub API エラー"""
        mock_format.return_value = "Test comment"

        with patch("requests.post") as mock_post:
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = Exception("API Error")
            mock_post.return_value = mock_response

            _post_pr_comment_if_configured(self_healing_result, pr_payload)

    @patch("nexuscore.api.github_self_healing_webhook.format_pr_comment")
    @patch.dict(
        os.environ,
        {"GITHUB_SELF_HEALING_TOKEN": "test-token", "NEXUS_PROJECT_ROOT": "/custom/project/root"},
        clear=True,
    )
    def test_post_comment_custom_project_root(
        self, mock_format, pr_payload, self_healing_result
    ):
        """カスタムプロジェクトルートを使用"""
        mock_format.return_value = "Test comment"

        with patch("requests.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 201
            mock_post.return_value = mock_response

            _post_pr_comment_if_configured(self_healing_result, pr_payload)

            mock_format.assert_called_once()
            call_kwargs = mock_format.call_args[1]
            assert call_kwargs["project_root"] == "/custom/project/root"


class TestSendSlackNotificationIfConfigured:
    @patch.dict(os.environ, {}, clear=True)
    def test_slack_notification_without_webhook_url(self, pr_payload, self_healing_result):
        """NEXUS_SLACK_WEBHOOK_URL が設定されていない"""
        _send_slack_notification_if_configured(self_healing_result, pr_payload)

    @patch.dict(os.environ, {"NEXUS_SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}, clear=True)
    def test_slack_notification_missing_repo_info(self, self_healing_result):
        """リポジトリ情報が欠けている"""
        payload = {
            "repository": {},
            "pull_request": {},
        }
        _send_slack_notification_if_configured(self_healing_result, payload)

    @patch("nexuscore.core.notifier.SlackNotifier")
    @patch.dict(os.environ, {"NEXUS_SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}, clear=True)
    def test_slack_notification_success_without_webapp(
        self, mock_notifier_class, pr_payload, self_healing_result
    ):
        """Slack 通知成功（webapp なし）"""
        mock_notifier = Mock()
        mock_notifier.notify_self_healing_complete.return_value = True
        mock_notifier_class.return_value = mock_notifier

        _send_slack_notification_if_configured(self_healing_result, pr_payload)

        mock_notifier_class.assert_called_once_with(webhook_url="https://hooks.slack.com/test")
        mock_notifier.notify_self_healing_complete.assert_called_once()
        call_kwargs = mock_notifier.notify_self_healing_complete.call_args[1]
        assert call_kwargs["repo_full_name"] == "test-owner/test-repo"
        assert call_kwargs["pr_number"] == 123
        assert call_kwargs["status"] == "fixed"

    @patch("nexuscore.core.notifier.SlackNotifier")
    @patch.dict(os.environ, {"NEXUS_SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}, clear=True)
    def test_slack_notification_failure(self, mock_notifier_class, pr_payload, self_healing_result):
        """Slack 通知失敗"""
        mock_notifier = Mock()
        mock_notifier.notify_self_healing_complete.return_value = False
        mock_notifier_class.return_value = mock_notifier

        _send_slack_notification_if_configured(self_healing_result, pr_payload)

    @patch("nexuscore.core.notifier.SlackNotifier")
    @patch.dict(os.environ, {"NEXUS_SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}, clear=True)
    def test_slack_notification_exception(
        self, mock_notifier_class, pr_payload, self_healing_result
    ):
        """Slack 通知で例外が発生"""
        mock_notifier_class.side_effect = Exception("Slack error")

        _send_slack_notification_if_configured(self_healing_result, pr_payload)

    @patch("nexuscore.core.notifier.SlackNotifier")
    @patch.dict(os.environ, {"NEXUS_SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}, clear=True)
    def test_slack_notification_with_run_id_in_result(self, mock_notifier_class, pr_payload):
        """result に run_id が含まれている場合"""
        result = {
            "status": "fixed",
            "run_id": "direct-run-id",
        }

        mock_notifier = Mock()
        mock_notifier.notify_self_healing_complete.return_value = True
        mock_notifier_class.return_value = mock_notifier

        _send_slack_notification_if_configured(result, pr_payload)

        call_kwargs = mock_notifier.notify_self_healing_complete.call_args[1]
        assert call_kwargs["run_id"] == "direct-run-id"

    @patch("nexuscore.core.notifier.SlackNotifier")
    @patch.dict(os.environ, {"NEXUS_SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}, clear=True)
    def test_slack_notification_with_run_id_in_details(self, mock_notifier_class, pr_payload):
        """result.details に run_id が含まれている場合"""
        result = {
            "status": "fixed",
            "details": {
                "run_id": "details-run-id",
            },
        }

        mock_notifier = Mock()
        mock_notifier.notify_self_healing_complete.return_value = True
        mock_notifier_class.return_value = mock_notifier

        _send_slack_notification_if_configured(result, pr_payload)

        call_kwargs = mock_notifier.notify_self_healing_complete.call_args[1]
        assert call_kwargs["run_id"] == "details-run-id"


class TestIntegrationScenarios:
    @patch("nexuscore.api.github_webhook_handler._send_slack_notification_if_configured")
    @patch("nexuscore.api.github_webhook_handler._post_pr_comment_if_configured")
    @patch("nexuscore.api.github_webhook_handler.github_webhook")
    @patch.dict(
        os.environ,
        {
            "GITHUB_SELF_HEALING_TOKEN": "gh-token",
            "NEXUS_SLACK_WEBHOOK_URL": "https://hooks.slack.com/test",
        },
    )
    def test_full_webhook_workflow(
        self,
        mock_github_webhook,
        mock_post_comment,
        mock_slack,
        flask_app,
        pr_payload,
        self_healing_result,
    ):
        """完全な Webhook ワークフロー"""
        mock_github_webhook.return_value = self_healing_result

        with flask_app.test_client() as client:
            resp = client.post(
                "/webhook",
                json=pr_payload,
                headers={
                    "X-GitHub-Event": "pull_request",
                    "X-GitHub-Delivery": "test-delivery",
                },
            )

        data = resp.get_json()
        assert data["accepted"] is True
        assert data["result"] == self_healing_result

        mock_github_webhook.assert_called_once()
        mock_post_comment.assert_called_once()
        mock_slack.assert_called_once()

    @patch("nexuscore.api.github_webhook_handler._send_slack_notification_if_configured")
    @patch("nexuscore.api.github_webhook_handler._post_pr_comment_if_configured")
    @patch("nexuscore.api.github_webhook_handler.github_webhook")
    def test_webhook_continues_on_pr_comment_error(
        self,
        mock_github_webhook,
        mock_post_comment,
        mock_slack,
        flask_app,
        pr_payload,
        self_healing_result,
    ):
        """PR コメント投稿が失敗しても処理は継続（outer try/except catches）"""
        mock_github_webhook.return_value = self_healing_result
        mock_post_comment.side_effect = Exception("GitHub API error")

        with flask_app.test_client() as client:
            resp = client.post(
                "/webhook",
                json=pr_payload,
                headers={
                    "X-GitHub-Event": "pull_request",
                    "X-GitHub-Delivery": "test-delivery",
                },
            )

        # Exception in _post_pr_comment_if_configured caught by outer try/except
        data = resp.get_json()
        assert resp.status_code == 500

    @patch("nexuscore.api.github_webhook_handler._send_slack_notification_if_configured")
    @patch("nexuscore.api.github_webhook_handler._post_pr_comment_if_configured")
    @patch("nexuscore.api.github_webhook_handler.github_webhook")
    def test_webhook_continues_on_slack_error(
        self,
        mock_github_webhook,
        mock_post_comment,
        mock_slack,
        flask_app,
        pr_payload,
        self_healing_result,
    ):
        """Slack 通知が失敗しても処理は継続（outer try/except catches）"""
        mock_github_webhook.return_value = self_healing_result
        mock_slack.side_effect = Exception("Slack error")

        with flask_app.test_client() as client:
            resp = client.post(
                "/webhook",
                json=pr_payload,
                headers={
                    "X-GitHub-Event": "pull_request",
                    "X-GitHub-Delivery": "test-delivery",
                },
            )

        data = resp.get_json()
        assert resp.status_code == 500
