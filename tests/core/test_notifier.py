"""notifier.py のテスト"""

import os
from unittest.mock import MagicMock, patch

from nexuscore.core.notifier import SlackNotifier, get_notifier


def test_slack_notifier_initialization_with_webhook():
    """Webhook URLを指定した場合の初期化テスト"""
    notifier = SlackNotifier(webhook_url="https://hooks.slack.com/services/test/webhook")

    assert notifier.webhook_url == "https://hooks.slack.com/services/test/webhook"
    assert notifier.enabled == (hasattr(notifier, "_has_requests") or True)  # requestsの有無に依存


def test_slack_notifier_initialization_from_env(monkeypatch):
    """環境変数からWebhook URLを取得するテスト"""
    monkeypatch.setenv("NEXUS_SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/env/webhook")

    notifier = SlackNotifier()

    assert notifier.webhook_url == "https://hooks.slack.com/services/env/webhook"


def test_slack_notifier_initialization_no_webhook():
    """Webhook URLがない場合の初期化テスト"""
    with patch.dict(os.environ, {}, clear=True):
        notifier = SlackNotifier()

        assert notifier.webhook_url is None
        assert notifier.enabled is False


@patch("nexuscore.core.notifier.requests")
def test_slack_notifier_send_success(mock_requests):
    """通知送信が成功する場合のテスト"""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_requests.post.return_value = mock_response

    notifier = SlackNotifier(webhook_url="https://hooks.slack.com/services/test/webhook")

    result = notifier.send(
        title="テストタイトル",
        message="テストメッセージ",
        status="success",
    )

    assert result is True
    mock_requests.post.assert_called_once()
    call_args = mock_requests.post.call_args
    assert call_args[0][0] == "https://hooks.slack.com/services/test/webhook"
    assert "text" in call_args[1]["json"]
    assert "attachments" in call_args[1]["json"]
    # 日本語化の確認
    payload = call_args[1]["json"]
    fields = payload["attachments"][0]["fields"]
    status_field = next((f for f in fields if f.get("title") == "ステータス"), None)
    assert status_field is not None
    assert status_field["value"] == "成功"


@patch("nexuscore.core.notifier.requests")
def test_slack_notifier_send_failure(mock_requests):
    """通知送信が失敗する場合のテスト"""
    mock_requests.post.side_effect = Exception("Network error")

    notifier = SlackNotifier(webhook_url="https://hooks.slack.com/services/test/webhook")

    result = notifier.send(
        title="Test Title",
        message="Test Message",
        status="error",
    )

    assert result is False


def test_slack_notifier_send_disabled():
    """通知が無効な場合のテスト"""
    notifier = SlackNotifier(webhook_url=None)

    result = notifier.send(
        title="Test Title",
        message="Test Message",
    )

    assert result is False


@patch("nexuscore.core.notifier.requests")
def test_slack_notifier_send_with_details(mock_requests):
    """詳細情報を含む通知のテスト"""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_requests.post.return_value = mock_response

    notifier = SlackNotifier(webhook_url="https://hooks.slack.com/services/test/webhook")

    result = notifier.send(
        title="Test Title",
        message="Test Message",
        status="info",
        details={"key1": "value1", "key2": "value2"},
    )

    assert result is True
    call_args = mock_requests.post.call_args
    payload = call_args[1]["json"]
    assert "attachments" in payload
    # Detailsフィールドが含まれることを確認
    fields = payload["attachments"][0]["fields"]
    detail_field = next((f for f in fields if f.get("title") == "Details"), None)
    assert detail_field is not None


@patch("nexuscore.core.notifier.requests")
def test_slack_notifier_notify_self_healing_complete_fixed(mock_requests):
    """Self-Healing完了通知（fixed）のテスト"""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_requests.post.return_value = mock_response

    notifier = SlackNotifier(webhook_url="https://hooks.slack.com/services/test/webhook")

    result = notifier.notify_self_healing_complete(
        repo_full_name="owner/repo",
        pr_number=123,
        status="fixed",
        summary="テストが通過しました",
        run_id="sh-1234567890-123-abc123",
    )

    assert result is True
    call_args = mock_requests.post.call_args
    payload = call_args[1]["json"]
    assert "Self-Healing 完了" in payload["text"]
    assert "✅" in payload["text"]
    assert "owner/repo" in payload["text"]
    assert "PR #123" in payload["text"]
    # 日本語化の確認
    fields = payload["attachments"][0]["fields"]
    detail_field = next((f for f in fields if f.get("title") == "詳細"), None)
    if detail_field:
        assert "リポジトリ" in detail_field["value"] or "修復成功" in detail_field["value"]


@patch("nexuscore.core.notifier.requests")
def test_slack_notifier_notify_self_healing_complete_error(mock_requests):
    """Self-Healing完了通知（error）のテスト"""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_requests.post.return_value = mock_response

    notifier = SlackNotifier(webhook_url="https://hooks.slack.com/services/test/webhook")

    result = notifier.notify_self_healing_complete(
        repo_full_name="owner/repo",
        pr_number=123,
        status="error",
        summary="An error occurred",
        run_id="sh-1234567890-123-abc123",
    )

    assert result is True
    call_args = mock_requests.post.call_args
    payload = call_args[1]["json"]
    assert "❌" in payload["text"]


@patch("nexuscore.core.notifier.requests")
def test_slack_notifier_notify_orchestrator_complete(mock_requests):
    """Orchestrator完了通知のテスト"""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_requests.post.return_value = mock_response

    notifier = SlackNotifier(webhook_url="https://hooks.slack.com/services/test/webhook")

    result = notifier.notify_orchestrator_complete(
        project_path="/path/to/project",
        requirement="Implement feature X",
        status="success",
        session_id="session-123",
    )

    assert result is True
    call_args = mock_requests.post.call_args
    payload = call_args[1]["json"]
    assert "Orchestrator Complete" in payload["text"]
    assert "✅" in payload["text"]


def test_get_notifier_with_webhook(monkeypatch):
    """Webhook URLが設定されている場合のget_notifierテスト"""
    monkeypatch.setenv("NEXUS_SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/test/webhook")

    notifier = get_notifier()

    assert notifier is not None
    assert isinstance(notifier, SlackNotifier)


def test_get_notifier_without_webhook(monkeypatch):
    """Webhook URLが設定されていない場合のget_notifierテスト"""
    monkeypatch.delenv("NEXUS_SLACK_WEBHOOK_URL", raising=False)

    notifier = get_notifier()

    assert notifier is None


@patch("nexuscore.core.notifier.requests")
def test_slack_notifier_color_mapping(mock_requests):
    """ステータスに応じたカラーマッピングのテスト"""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_requests.post.return_value = mock_response

    notifier = SlackNotifier(webhook_url="https://hooks.slack.com/services/test/webhook")

    # success -> 緑
    notifier.send(title="Success", message="Test", status="success")
    call_args = mock_requests.post.call_args
    assert call_args[1]["json"]["attachments"][0]["color"] == "#36a64f"

    # error -> 赤
    notifier.send(title="Error", message="Test", status="error")
    call_args = mock_requests.post.call_args
    assert call_args[1]["json"]["attachments"][0]["color"] == "#ff0000"

    # warning -> オレンジ
    notifier.send(title="Warning", message="Test", status="warning")
    call_args = mock_requests.post.call_args
    assert call_args[1]["json"]["attachments"][0]["color"] == "#ffaa00"


@patch("nexuscore.core.notifier.requests")
def test_slack_notifier_custom_color(mock_requests):
    """カスタムカラーの指定テスト"""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_requests.post.return_value = mock_response

    notifier = SlackNotifier(webhook_url="https://hooks.slack.com/services/test/webhook")

    result = notifier.send(
        title="Custom",
        message="Test",
        status="info",
        color="#123456",
    )

    assert result is True
    call_args = mock_requests.post.call_args
    assert call_args[1]["json"]["attachments"][0]["color"] == "#123456"
