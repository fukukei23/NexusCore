"""
Tests for nexuscore.api.routes.github_webhook module.
"""

import hashlib
import hmac
import json
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from nexuscore.api.fastapi_app import app


@pytest.fixture
def client():
    return TestClient(app)


def _make_signature(payload: bytes, secret: str) -> str:
    mac = hmac.new(secret.encode(), payload, hashlib.sha256)
    return f"sha256={mac.hexdigest()}"


def _valid_payload():
    return {
        "action": "opened",
        "repository": {"full_name": "owner/repo"},
        "pull_request": {
            "number": 123,
            "head": {"sha": "abc123"},
            "base": {"ref": "main"},
        },
    }


class TestVerifyGitHubSignature:
    """verify_github_signature 関数のテスト"""

    def test_no_secret_skips_verification(self):
        from nexuscore.api.routes.github_webhook import verify_github_signature

        assert verify_github_signature(b"body", "sha256=abc", None) is True

    def test_no_signature_header_returns_false(self):
        from nexuscore.api.routes.github_webhook import verify_github_signature

        assert verify_github_signature(b"body", None, "secret") is False

    def test_invalid_format_returns_false(self):
        from nexuscore.api.routes.github_webhook import verify_github_signature

        assert verify_github_signature(b"body", "invalid", "secret") is False

    def test_valid_signature(self):
        from nexuscore.api.routes.github_webhook import verify_github_signature

        payload = b'{"action":"opened"}'
        secret = "mysecret"
        sig = _make_signature(payload, secret)
        assert verify_github_signature(payload, sig, secret) is True

    def test_invalid_signature(self):
        from nexuscore.api.routes.github_webhook import verify_github_signature

        assert verify_github_signature(b"body", "sha256=wrong", "secret") is False


class TestGitHubWebhookEndpoint:
    """POST /api/v1/github/webhook エンドポイントのテスト"""

    def test_non_pull_request_event_ignored(self, client):
        with patch.dict(os.environ, {}, clear=False):
            response = client.post(
                "/api/v1/github/webhook",
                json=_valid_payload(),
                headers={"X-GitHub-Event": "push"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["accepted"] is False

    def test_pull_request_empty_body(self, client):
        with patch.dict(os.environ, {}, clear=False):
            response = client.post(
                "/api/v1/github/webhook",
                content=b"",
                headers={"X-GitHub-Event": "pull_request"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["accepted"] is False

    def test_pull_request_invalid_json(self, client):
        with patch.dict(os.environ, {}, clear=False):
            response = client.post(
                "/api/v1/github/webhook",
                content=b"not json",
                headers={
                    "X-GitHub-Event": "pull_request",
                    "Content-Type": "application/json",
                },
            )
        assert response.status_code == 200
        data = response.json()
        assert data["accepted"] is False

    def test_pull_request_invalid_payload_schema(self, client):
        """Pydantic バリデーション失敗（pull_request.number なし）"""
        bad_payload = {"action": "opened", "repository": {"full_name": "o/r"}}
        with patch.dict(os.environ, {}, clear=False):
            response = client.post(
                "/api/v1/github/webhook",
                json=bad_payload,
                headers={"X-GitHub-Event": "pull_request"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["accepted"] is False

    def test_pull_request_valid_no_secret(self, client):
        payload = _valid_payload()
        with patch.dict(os.environ, {}, clear=False):
            with patch(
                "nexuscore.api.github_self_healing_webhook.github_webhook",
                return_value={"status": "fixed", "summary": "Done"},
            ) as mock_handler:
                with patch(
                    "nexuscore.api.routes.github_webhook._post_pr_comment_if_configured"
                ):
                    with patch(
                        "nexuscore.api.routes.github_webhook._send_slack_notification_if_configured"
                    ):
                        response = client.post(
                            "/api/v1/github/webhook",
                            json=payload,
                            headers={"X-GitHub-Event": "pull_request"},
                        )

        assert response.status_code == 200
        data = response.json()
        assert data["accepted"] is True
        mock_handler.assert_called_once()

    def test_pull_request_valid_with_secret(self, client):
        secret = "webhook_secret"
        payload = _valid_payload()
        payload_bytes = json.dumps(payload).encode()
        sig = _make_signature(payload_bytes, secret)

        with patch.dict(os.environ, {"GITHUB_WEBHOOK_SECRET": secret}, clear=False):
            with patch(
                "nexuscore.api.github_self_healing_webhook.github_webhook",
                return_value={"status": "fixed", "summary": "Done"},
            ):
                with patch(
                    "nexuscore.api.routes.github_webhook._post_pr_comment_if_configured"
                ):
                    with patch(
                        "nexuscore.api.routes.github_webhook._send_slack_notification_if_configured"
                    ):
                        response = client.post(
                            "/api/v1/github/webhook",
                            content=payload_bytes,
                            headers={
                                "X-GitHub-Event": "pull_request",
                                "X-Hub-Signature-256": sig,
                                "Content-Type": "application/json",
                            },
                        )

        assert response.status_code == 200
        data = response.json()
        assert data["accepted"] is True

    def test_pull_request_invalid_signature(self, client):
        payload = _valid_payload()
        with patch.dict(
            os.environ, {"GITHUB_WEBHOOK_SECRET": "correct_secret"}, clear=False
        ):
            response = client.post(
                "/api/v1/github/webhook",
                json=payload,
                headers={
                    "X-GitHub-Event": "pull_request",
                    "X-Hub-Signature-256": "sha256=invalidsig",
                },
            )
        assert response.status_code == 401

    def test_handler_import_error(self, client):
        payload = _valid_payload()
        with patch.dict(os.environ, {}, clear=False):
            with patch.dict(
                "sys.modules", {"nexuscore.api.github_self_healing_webhook": None}
            ):
                response = client.post(
                    "/api/v1/github/webhook",
                    json=payload,
                    headers={"X-GitHub-Event": "pull_request"},
                )
        assert response.status_code == 500

    def test_handler_exception(self, client):
        payload = _valid_payload()
        with patch.dict(os.environ, {}, clear=False):
            with patch(
                "nexuscore.api.github_self_healing_webhook.github_webhook",
                side_effect=Exception("boom"),
            ):
                with patch(
                    "nexuscore.api.routes.github_webhook._post_pr_comment_if_configured"
                ):
                    with patch(
                        "nexuscore.api.routes.github_webhook._send_slack_notification_if_configured"
                    ):
                        response = client.post(
                            "/api/v1/github/webhook",
                            json=payload,
                            headers={"X-GitHub-Event": "pull_request"},
                        )

        assert response.status_code == 200
        data = response.json()
        assert data["accepted"] is False
        assert data["error"] is not None


class TestPostPRComment:
    """_post_pr_comment_if_configured のテスト"""

    def test_no_token_skips(self):
        from nexuscore.api.routes.github_webhook import _post_pr_comment_if_configured

        with patch.dict(os.environ, {}, clear=True):
            # 戻り値なしで例外も発生しない
            _post_pr_comment_if_configured({}, {})

    def test_missing_repo_info_skips(self):
        from nexuscore.api.routes.github_webhook import _post_pr_comment_if_configured

        with patch.dict(
            os.environ, {"GITHUB_SELF_HEALING_TOKEN": "token"}, clear=True
        ):
            with patch(
                "nexuscore.api.github_self_healing_webhook.format_pr_comment",
                return_value="comment",
            ):
                # payload に repository/full_name がない
                _post_pr_comment_if_configured({}, {"pull_request": {"number": 1}})

    def test_post_success(self):
        from nexuscore.api.routes.github_webhook import _post_pr_comment_if_configured

        with patch.dict(
            os.environ, {"GITHUB_SELF_HEALING_TOKEN": "token"}, clear=True
        ):
            with patch(
                "nexuscore.api.github_self_healing_webhook.format_pr_comment",
                return_value="comment body",
            ) as mock_format:
                with patch("requests.post") as mock_post:
                    mock_post.return_value = MagicMock(status_code=201)
                    mock_post.return_value.raise_for_status = MagicMock()

                    payload = {
                        "repository": {"full_name": "owner/repo"},
                        "pull_request": {"number": 42, "head": {"sha": "abc"}},
                    }
                    _post_pr_comment_if_configured({}, payload)

                    mock_format.assert_called_once()
                    mock_post.assert_called_once()
                    url = mock_post.call_args[0][0]
                    assert "owner/repo" in url
                    assert "42" in url

    def test_post_failure_logs_only(self):
        from nexuscore.api.routes.github_webhook import _post_pr_comment_if_configured

        with patch.dict(
            os.environ, {"GITHUB_SELF_HEALING_TOKEN": "token"}, clear=True
        ):
            with patch(
                "nexuscore.api.github_self_healing_webhook.format_pr_comment",
                return_value="comment",
            ):
                with patch("requests.post", side_effect=Exception("Network error")):
                    # 例外が伝播しない
                    _post_pr_comment_if_configured(
                        {},
                        {
                            "repository": {"full_name": "o/r"},
                            "pull_request": {"number": 1, "head": {"sha": "a"}},
                        },
                    )


class TestSendSlackNotification:
    """_send_slack_notification_if_configured のテスト"""

    def test_no_webhook_url_skips(self):
        from nexuscore.api.routes.github_webhook import (
            _send_slack_notification_if_configured,
        )

        with patch.dict(os.environ, {}, clear=True):
            _send_slack_notification_if_configured({}, {})

    def test_missing_repo_info_skips(self):
        from nexuscore.api.routes.github_webhook import (
            _send_slack_notification_if_configured,
        )

        with patch.dict(
            os.environ, {"NEXUS_SLACK_WEBHOOK_URL": "https://hooks.slack.com/x"},
            clear=True,
        ):
            # payload に repository/full_name がない
            _send_slack_notification_if_configured({}, {})

    def test_notification_success(self):
        from nexuscore.api.routes.github_webhook import (
            _send_slack_notification_if_configured,
        )

        with patch.dict(
            os.environ, {"NEXUS_SLACK_WEBHOOK_URL": "https://hooks.slack.com/x"},
            clear=True,
        ):
            with patch("nexuscore.core.notifier.SlackNotifier") as MockNotifier:
                mock_instance = MagicMock()
                mock_instance.notify_self_healing_complete.return_value = True
                MockNotifier.return_value = mock_instance

                result = {"status": "fixed", "summary": "Done"}
                payload = {
                    "repository": {"full_name": "owner/repo"},
                    "pull_request": {"number": 42},
                }
                _send_slack_notification_if_configured(result, payload)

                MockNotifier.assert_called_once()
                mock_instance.notify_self_healing_complete.assert_called_once()

    def test_notification_failure_logs_only(self):
        from nexuscore.api.routes.github_webhook import (
            _send_slack_notification_if_configured,
        )

        with patch.dict(
            os.environ, {"NEXUS_SLACK_WEBHOOK_URL": "https://hooks.slack.com/x"},
            clear=True,
        ):
            with patch(
                "nexuscore.core.notifier.SlackNotifier",
                side_effect=Exception("Slack error"),
            ):
                # 例外が伝播しない
                _send_slack_notification_if_configured(
                    {"status": "fixed"},
                    {
                        "repository": {"full_name": "o/r"},
                        "pull_request": {"number": 1},
                    },
                )
