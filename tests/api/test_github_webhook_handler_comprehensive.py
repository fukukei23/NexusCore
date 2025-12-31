"""
============================================================================
Comprehensive Tests for github_webhook_handler.py
============================================================================
高品質テストの原則:
- 外部依存（Flask request、GitHub API、Slack）のみモック
- 実際のWebhookハンドリングロジックをテスト
- エッジケースとエラー条件をカバー
============================================================================
"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock, call
from flask import Flask

from nexuscore.api.github_webhook_handler import (
    handle_github_webhook,
    _post_pr_comment_if_configured,
    _send_slack_notification_if_configured,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def app():
    """Flask テストアプリケーション"""
    app = Flask(__name__)
    app.config['TESTING'] = True
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


# ============================================================================
# Tests: handle_github_webhook
# ============================================================================


class TestHandleGithubWebhook:
    @patch('nexuscore.api.github_webhook_handler.request')
    def test_handle_non_pull_request_event(self, mock_request):
        """pull_request 以外のイベントは無視"""
        mock_request.headers.get.side_effect = lambda key, default=None: {
            'X-GitHub-Event': 'push',
            'X-GitHub-Delivery': 'test-delivery',
        }.get(key, default)

        result = handle_github_webhook()

        assert result['accepted'] is False
        assert 'not supported' in result['reason']
        assert 'push' in result['reason']

    @patch('nexuscore.api.github_webhook_handler.request')
    def test_handle_pull_request_event_invalid_payload(self, mock_request):
        """無効なペイロード（JSONでない）"""
        mock_request.headers.get.side_effect = lambda key, default=None: {
            'X-GitHub-Event': 'pull_request',
        }.get(key, default)
        mock_request.get_json.return_value = None

        result = handle_github_webhook()

        assert isinstance(result, tuple)
        assert result[1] == 400
        assert result[0]['accepted'] is False
        assert 'Invalid payload' in result[0]['reason']

    @patch('nexuscore.api.github_webhook_handler._send_slack_notification_if_configured')
    @patch('nexuscore.api.github_webhook_handler._post_pr_comment_if_configured')
    @patch('nexuscore.api.github_webhook_handler.github_webhook')
    @patch('nexuscore.api.github_webhook_handler.request')
    def test_handle_pull_request_event_success(
        self, mock_request, mock_github_webhook,
        mock_post_comment, mock_slack, pr_payload, self_healing_result
    ):
        """正常なPRイベント処理"""
        mock_request.headers.get.side_effect = lambda key, default=None: {
            'X-GitHub-Event': 'pull_request',
            'X-GitHub-Delivery': 'test-delivery',
        }.get(key, default)
        mock_request.get_json.return_value = pr_payload
        mock_github_webhook.return_value = self_healing_result

        result = handle_github_webhook()

        assert result['accepted'] is True
        assert result['result'] == self_healing_result

        # github_webhook が呼ばれる
        mock_github_webhook.assert_called_once_with(
            payload=pr_payload,
            project_root=None,
            event='pull_request',
            delivery='test-delivery'
        )

        # PR コメントと Slack 通知が試みられる
        mock_post_comment.assert_called_once_with(self_healing_result, pr_payload)
        mock_slack.assert_called_once_with(self_healing_result, pr_payload)

    @patch('nexuscore.api.github_webhook_handler.github_webhook')
    @patch('nexuscore.api.github_webhook_handler.request')
    def test_handle_pull_request_event_exception(
        self, mock_request, mock_github_webhook, pr_payload
    ):
        """github_webhook が例外を投げる"""
        mock_request.headers.get.side_effect = lambda key, default=None: {
            'X-GitHub-Event': 'pull_request',
        }.get(key, default)
        mock_request.get_json.return_value = pr_payload
        mock_github_webhook.side_effect = Exception("Self-healing failed")

        result = handle_github_webhook()

        assert isinstance(result, tuple)
        assert result[1] == 500
        assert result[0]['accepted'] is False
        assert 'error' in result[0]

    @patch('nexuscore.api.github_webhook_handler.request')
    def test_handle_unknown_event(self, mock_request):
        """X-GitHub-Event ヘッダーがない場合"""
        mock_request.headers.get.return_value = 'unknown'

        result = handle_github_webhook()

        assert result['accepted'] is False
        assert 'unknown' in result['reason']


# ============================================================================
# Tests: _post_pr_comment_if_configured
# ============================================================================


class TestPostPrCommentIfConfigured:
    @patch.dict(os.environ, {}, clear=True)
    def test_post_comment_without_token(self, pr_payload, self_healing_result):
        """GITHUB_SELF_HEALING_TOKEN が設定されていない"""
        # 例外が発生しないことを確認
        _post_pr_comment_if_configured(self_healing_result, pr_payload)

    @patch('nexuscore.api.github_webhook_handler.requests')
    @patch('nexuscore.api.github_webhook_handler.format_pr_comment')
    @patch.dict(os.environ, {'GITHUB_SELF_HEALING_TOKEN': 'test-token'})
    def test_post_comment_success(
        self, mock_format, mock_requests, pr_payload, self_healing_result
    ):
        """PR コメント投稿成功"""
        mock_format.return_value = "Test comment body"
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_requests.post.return_value = mock_response

        _post_pr_comment_if_configured(self_healing_result, pr_payload)

        # GitHub API が呼ばれる
        mock_requests.post.assert_called_once()
        call_args = mock_requests.post.call_args

        # URL が正しい
        assert 'test-owner/test-repo' in call_args[0][0]
        assert '123' in call_args[0][0]
        assert '/comments' in call_args[0][0]

        # ヘッダーにトークンが含まれる
        headers = call_args[1]['headers']
        assert 'Authorization' in headers
        assert 'token test-token' in headers['Authorization']

        # ボディにコメントが含まれる
        data = call_args[1]['json']
        assert data['body'] == "Test comment body"

    @patch('nexuscore.api.github_webhook_handler.format_pr_comment')
    @patch.dict(os.environ, {'GITHUB_SELF_HEALING_TOKEN': 'test-token'})
    def test_post_comment_missing_repo_name(self, mock_format, self_healing_result):
        """リポジトリ名が欠けている"""
        payload = {
            "repository": {},
            "pull_request": {"number": 123},
        }

        # 例外が発生しないことを確認
        _post_pr_comment_if_configured(self_healing_result, payload)

    @patch('nexuscore.api.github_webhook_handler.format_pr_comment')
    @patch.dict(os.environ, {'GITHUB_SELF_HEALING_TOKEN': 'test-token'})
    def test_post_comment_missing_pr_number(self, mock_format, self_healing_result):
        """PR番号が欠けている"""
        payload = {
            "repository": {"full_name": "owner/repo"},
            "pull_request": {},
        }

        # 例外が発生しないことを確認
        _post_pr_comment_if_configured(self_healing_result, payload)

    @patch('nexuscore.api.github_webhook_handler.requests')
    @patch('nexuscore.api.github_webhook_handler.format_pr_comment')
    @patch.dict(os.environ, {'GITHUB_SELF_HEALING_TOKEN': 'test-token'})
    def test_post_comment_api_error(
        self, mock_format, mock_requests, pr_payload, self_healing_result
    ):
        """GitHub API エラー"""
        mock_format.return_value = "Test comment"
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("API Error")
        mock_requests.post.return_value = mock_response

        # 例外が発生しないことを確認（エラーはログに記録される）
        _post_pr_comment_if_configured(self_healing_result, pr_payload)

    @patch('nexuscore.api.github_webhook_handler.requests')
    @patch('nexuscore.api.github_webhook_handler.format_pr_comment')
    @patch.dict(os.environ, {
        'GITHUB_SELF_HEALING_TOKEN': 'test-token',
        'NEXUS_PROJECT_ROOT': '/custom/project/root'
    })
    def test_post_comment_custom_project_root(
        self, mock_format, mock_requests, pr_payload, self_healing_result
    ):
        """カスタムプロジェクトルートを使用"""
        mock_format.return_value = "Test comment"
        mock_response = Mock()
        mock_requests.post.return_value = mock_response

        _post_pr_comment_if_configured(self_healing_result, pr_payload)

        # format_pr_comment が正しいパラメータで呼ばれる
        mock_format.assert_called_once()
        call_kwargs = mock_format.call_args[1]
        assert call_kwargs['project_root'] == '/custom/project/root'


# ============================================================================
# Tests: _send_slack_notification_if_configured
# ============================================================================


class TestSendSlackNotificationIfConfigured:
    @patch.dict(os.environ, {}, clear=True)
    def test_slack_notification_without_webhook_url(
        self, pr_payload, self_healing_result
    ):
        """NEXUS_SLACK_WEBHOOK_URL が設定されていない"""
        # 例外が発生しないことを確認
        _send_slack_notification_if_configured(self_healing_result, pr_payload)

    @patch('nexuscore.api.github_webhook_handler.SlackNotifier')
    @patch.dict(os.environ, {'NEXUS_SLACK_WEBHOOK_URL': 'https://hooks.slack.com/test'})
    def test_slack_notification_missing_repo_info(
        self, mock_notifier_class, self_healing_result
    ):
        """リポジトリ情報が欠けている"""
        payload = {
            "repository": {},
            "pull_request": {},
        }

        # 例外が発生しないことを確認
        _send_slack_notification_if_configured(self_healing_result, payload)

    @patch('nexuscore.api.github_webhook_handler.SlackNotifier')
    @patch.dict(os.environ, {'NEXUS_SLACK_WEBHOOK_URL': 'https://hooks.slack.com/test'})
    def test_slack_notification_success_without_webapp(
        self, mock_notifier_class, pr_payload, self_healing_result
    ):
        """Slack 通知成功（webapp なし）"""
        mock_notifier = Mock()
        mock_notifier.notify_self_healing_complete.return_value = True
        mock_notifier_class.return_value = mock_notifier

        _send_slack_notification_if_configured(self_healing_result, pr_payload)

        # SlackNotifier が初期化される
        mock_notifier_class.assert_called_once_with(
            webhook_url='https://hooks.slack.com/test'
        )

        # notify_self_healing_complete が呼ばれる
        mock_notifier.notify_self_healing_complete.assert_called_once()
        call_kwargs = mock_notifier.notify_self_healing_complete.call_args[1]

        assert call_kwargs['repo_full_name'] == 'test-owner/test-repo'
        assert call_kwargs['pr_number'] == 123
        assert call_kwargs['status'] == 'fixed'

    @patch('nexuscore.api.github_webhook_handler.SlackNotifier')
    @patch.dict(os.environ, {'NEXUS_SLACK_WEBHOOK_URL': 'https://hooks.slack.com/test'})
    def test_slack_notification_failure(
        self, mock_notifier_class, pr_payload, self_healing_result
    ):
        """Slack 通知失敗"""
        mock_notifier = Mock()
        mock_notifier.notify_self_healing_complete.return_value = False
        mock_notifier_class.return_value = mock_notifier

        # 例外が発生しないことを確認
        _send_slack_notification_if_configured(self_healing_result, pr_payload)

    @patch('nexuscore.api.github_webhook_handler.SlackNotifier')
    @patch.dict(os.environ, {'NEXUS_SLACK_WEBHOOK_URL': 'https://hooks.slack.com/test'})
    def test_slack_notification_exception(
        self, mock_notifier_class, pr_payload, self_healing_result
    ):
        """Slack 通知で例外が発生"""
        mock_notifier_class.side_effect = Exception("Slack error")

        # 例外が発生しないことを確認（エラーはログに記録される）
        _send_slack_notification_if_configured(self_healing_result, pr_payload)

    @patch('nexuscore.api.github_webhook_handler.SlackNotifier')
    @patch.dict(os.environ, {'NEXUS_SLACK_WEBHOOK_URL': 'https://hooks.slack.com/test'})
    def test_slack_notification_with_run_id_in_result(
        self, mock_notifier_class, pr_payload
    ):
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
        assert call_kwargs['run_id'] == 'direct-run-id'

    @patch('nexuscore.api.github_webhook_handler.SlackNotifier')
    @patch.dict(os.environ, {'NEXUS_SLACK_WEBHOOK_URL': 'https://hooks.slack.com/test'})
    def test_slack_notification_with_run_id_in_details(
        self, mock_notifier_class, pr_payload
    ):
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
        assert call_kwargs['run_id'] == 'details-run-id'


# ============================================================================
# Tests: Integration scenarios
# ============================================================================


class TestIntegrationScenarios:
    @patch('nexuscore.api.github_webhook_handler.requests')
    @patch('nexuscore.api.github_webhook_handler.SlackNotifier')
    @patch('nexuscore.api.github_webhook_handler.format_pr_comment')
    @patch('nexuscore.api.github_webhook_handler.github_webhook')
    @patch('nexuscore.api.github_webhook_handler.request')
    @patch.dict(os.environ, {
        'GITHUB_SELF_HEALING_TOKEN': 'gh-token',
        'NEXUS_SLACK_WEBHOOK_URL': 'https://hooks.slack.com/test'
    })
    def test_full_webhook_workflow(
        self, mock_request, mock_github_webhook, mock_format,
        mock_notifier_class, mock_requests_lib, pr_payload, self_healing_result
    ):
        """完全な Webhook ワークフロー"""
        # リクエストのセットアップ
        mock_request.headers.get.side_effect = lambda key, default=None: {
            'X-GitHub-Event': 'pull_request',
            'X-GitHub-Delivery': 'test-delivery',
        }.get(key, default)
        mock_request.get_json.return_value = pr_payload

        # github_webhook の実行結果
        mock_github_webhook.return_value = self_healing_result

        # PR コメントのフォーマット
        mock_format.return_value = "Formatted PR comment"

        # GitHub API のモック
        mock_gh_response = Mock()
        mock_requests_lib.post.return_value = mock_gh_response

        # Slack のモック
        mock_notifier = Mock()
        mock_notifier.notify_self_healing_complete.return_value = True
        mock_notifier_class.return_value = mock_notifier

        # Webhook を処理
        result = handle_github_webhook()

        # 結果の確認
        assert result['accepted'] is True
        assert result['result'] == self_healing_result

        # GitHub Webhook が処理された
        mock_github_webhook.assert_called_once()

        # PR コメントが投稿された
        mock_requests_lib.post.assert_called_once()
        assert 'test-owner/test-repo' in mock_requests_lib.post.call_args[0][0]

        # Slack 通知が送信された
        mock_notifier.notify_self_healing_complete.assert_called_once()

    @patch('nexuscore.api.github_webhook_handler._send_slack_notification_if_configured')
    @patch('nexuscore.api.github_webhook_handler._post_pr_comment_if_configured')
    @patch('nexuscore.api.github_webhook_handler.github_webhook')
    @patch('nexuscore.api.github_webhook_handler.request')
    def test_webhook_continues_on_pr_comment_error(
        self, mock_request, mock_github_webhook,
        mock_post_comment, mock_slack, pr_payload, self_healing_result
    ):
        """PR コメント投稿が失敗しても処理は継続"""
        mock_request.headers.get.side_effect = lambda key, default=None: {
            'X-GitHub-Event': 'pull_request',
        }.get(key, default)
        mock_request.get_json.return_value = pr_payload
        mock_github_webhook.return_value = self_healing_result

        # PR コメント投稿で例外
        mock_post_comment.side_effect = Exception("GitHub API error")

        # Webhook 処理は成功する
        result = handle_github_webhook()

        assert result['accepted'] is True

        # Slack 通知は試みられる
        mock_slack.assert_called_once()

    @patch('nexuscore.api.github_webhook_handler._send_slack_notification_if_configured')
    @patch('nexuscore.api.github_webhook_handler._post_pr_comment_if_configured')
    @patch('nexuscore.api.github_webhook_handler.github_webhook')
    @patch('nexuscore.api.github_webhook_handler.request')
    def test_webhook_continues_on_slack_error(
        self, mock_request, mock_github_webhook,
        mock_post_comment, mock_slack, pr_payload, self_healing_result
    ):
        """Slack 通知が失敗しても処理は継続"""
        mock_request.headers.get.side_effect = lambda key, default=None: {
            'X-GitHub-Event': 'pull_request',
        }.get(key, default)
        mock_request.get_json.return_value = pr_payload
        mock_github_webhook.return_value = self_healing_result

        # Slack 通知で例外
        mock_slack.side_effect = Exception("Slack error")

        # Webhook 処理は成功する
        result = handle_github_webhook()

        assert result['accepted'] is True

        # PR コメント投稿は試みられる
        mock_post_comment.assert_called_once()
