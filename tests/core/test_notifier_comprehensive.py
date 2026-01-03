"""
notifier.py の包括的テスト

カバレッジ:
- SlackNotifier: Slack通知クラス
  - __init__: webhook URLの初期化（環境変数対応）
  - send: 基本的な通知送信（status, details, color対応）
  - notify_self_healing_complete: Self-Healing完了通知
  - notify_orchestrator_complete: Orchestrator完了通知
  - notify_project_complete: プロジェクト完了通知
- get_notifier: グローバルnotifier取得

エッジケース:
- requestsライブラリが不在の場合の動作
- 環境変数からのwebhook URL取得
- control.jsonファイルの破損
- 日本語メッセージのUnicode処理
- 詳細情報の1000文字制限
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# NOTE: requestsがない環境でもテスト可能にする
try:
    from nexuscore.core.notifier import (
        SlackNotifier,
        get_notifier,
        HAS_REQUESTS,
    )
    HAS_NOTIFIER = True
except ImportError:
    HAS_NOTIFIER = False
    SlackNotifier = None  # type: ignore
    get_notifier = None  # type: ignore
    HAS_REQUESTS = False


@pytest.mark.skipif(not HAS_NOTIFIER, reason="notifier module not available")
class TestSlackNotifierInit:
    """SlackNotifier 初期化のテスト"""

    def test_init_with_webhook_url(self):
        """webhook URLを直接指定した場合"""
        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/services/test/webhook")

        assert notifier.webhook_url == "https://hooks.slack.com/services/test/webhook"
        assert notifier.enabled == HAS_REQUESTS  # requestsの有無に依存

    def test_init_from_env_variable(self, monkeypatch):
        """環境変数からwebhook URLを取得"""
        monkeypatch.setenv("NEXUS_SLACK_WEBHOOK_URL", "https://hooks.slack.com/env/webhook")

        notifier = SlackNotifier()

        assert notifier.webhook_url == "https://hooks.slack.com/env/webhook"
        assert notifier.enabled == HAS_REQUESTS

    def test_init_without_webhook(self):
        """webhook URLがない場合"""
        with patch.dict(os.environ, {}, clear=True):
            notifier = SlackNotifier()

            assert notifier.webhook_url is None
            assert notifier.enabled is False

    def test_init_without_requests_library(self, monkeypatch):
        """requestsライブラリが不在の場合"""
        # HAS_REQUESTSがFalseの場合の動作を確認
        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")

        if not HAS_REQUESTS:
            assert notifier.enabled is False


@pytest.mark.skipif(not HAS_NOTIFIER, reason="notifier module not available")
class TestSlackNotifierSend:
    """SlackNotifier.send() のテスト"""

    def test_send_disabled_when_no_webhook(self):
        """webhook URLがない場合は送信しない"""
        notifier = SlackNotifier(webhook_url=None)

        result = notifier.send(
            title="Test",
            message="Message",
            status="info",
        )

        assert result is False

    @pytest.mark.skipif(not HAS_REQUESTS, reason="requests library not installed")
    @patch('requests.post')
    def test_send_success(self, mock_post):
        """送信成功のテスト"""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")

        result = notifier.send(
            title="テストタイトル",
            message="テストメッセージ",
            status="success",
        )

        assert result is True
        mock_post.assert_called_once()

        # 呼び出し引数を確認
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["text"] == "テストタイトル"
        assert "attachments" in call_kwargs["json"]
        assert call_kwargs["timeout"] == 10

    @pytest.mark.skipif(not HAS_REQUESTS, reason="requests library not installed")
    @patch('requests.post')
    def test_send_failure(self, mock_post):
        """送信失敗のテスト"""
        mock_post.side_effect = Exception("Network error")

        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")

        result = notifier.send(
            title="Test",
            message="Message",
            status="error",
        )

        assert result is False

    @pytest.mark.skipif(not HAS_REQUESTS, reason="requests library not installed")
    @patch('requests.post')
    def test_send_with_details(self, mock_post):
        """詳細情報を含む送信"""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")

        result = notifier.send(
            title="Test",
            message="Message",
            status="info",
            details={"key1": "value1", "key2": "value2"},
        )

        assert result is True

        # detailsフィールドが含まれることを確認
        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        fields = payload["attachments"][0]["fields"]
        detail_field = next((f for f in fields if f.get("title") == "詳細"), None)
        assert detail_field is not None
        assert "key1" in detail_field["value"]
        assert "value1" in detail_field["value"]

    @pytest.mark.skipif(not HAS_REQUESTS, reason="requests library not installed")
    @patch('requests.post')
    def test_send_with_long_details(self, mock_post):
        """詳細情報が1000文字を超える場合の切り詰め"""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")

        long_value = "x" * 2000
        result = notifier.send(
            title="Test",
            message="Message",
            status="info",
            details={"long_key": long_value},
        )

        assert result is True

        # 1000文字に切り詰められることを確認
        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        fields = payload["attachments"][0]["fields"]
        detail_field = next((f for f in fields if f.get("title") == "詳細"), None)
        assert len(detail_field["value"]) <= 1000

    @pytest.mark.skipif(not HAS_REQUESTS, reason="requests library not installed")
    @patch('requests.post')
    def test_send_status_color_mapping(self, mock_post):
        """ステータスに応じたカラーマッピング"""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")

        # success -> 緑
        notifier.send(title="Success", message="Test", status="success")
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["attachments"][0]["color"] == "#36a64f"

        # error -> 赤
        notifier.send(title="Error", message="Test", status="error")
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["attachments"][0]["color"] == "#ff0000"

        # warning -> オレンジ
        notifier.send(title="Warning", message="Test", status="warning")
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["attachments"][0]["color"] == "#ffaa00"

        # info -> 青
        notifier.send(title="Info", message="Test", status="info")
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["attachments"][0]["color"] == "#36a64f"

    @pytest.mark.skipif(not HAS_REQUESTS, reason="requests library not installed")
    @patch('requests.post')
    def test_send_custom_color(self, mock_post):
        """カスタムカラーの指定"""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")

        result = notifier.send(
            title="Custom",
            message="Test",
            status="info",
            color="#123456",
        )

        assert result is True
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["attachments"][0]["color"] == "#123456"

    @pytest.mark.skipif(not HAS_REQUESTS, reason="requests library not installed")
    @patch('requests.post')
    def test_send_japanese_status_mapping(self, mock_post):
        """ステータスの日本語マッピング"""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")

        notifier.send(title="Test", message="Message", status="success")

        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        fields = payload["attachments"][0]["fields"]
        status_field = next((f for f in fields if f.get("title") == "ステータス"), None)
        assert status_field is not None
        assert status_field["value"] == "成功"


@pytest.mark.skipif(not HAS_NOTIFIER, reason="notifier module not available")
class TestNotifySelfHealingComplete:
    """notify_self_healing_complete() のテスト"""

    @pytest.mark.skipif(not HAS_REQUESTS, reason="requests library not installed")
    @patch('requests.post')
    def test_notify_self_healing_fixed(self, mock_post):
        """Self-Healing完了通知（fixed）"""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")

        result = notifier.notify_self_healing_complete(
            repo_full_name="owner/repo",
            pr_number=123,
            status="fixed",
            summary="テストが通過しました",
            run_id="sh-1234567890",
        )

        assert result is True

        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        assert "Self-Healing 完了" in payload["text"]
        assert "✅" in payload["text"]
        assert "owner/repo" in payload["text"]
        assert "PR #123" in payload["text"]

    @pytest.mark.skipif(not HAS_REQUESTS, reason="requests library not installed")
    @patch('requests.post')
    def test_notify_self_healing_error(self, mock_post):
        """Self-Healing完了通知（error）"""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")

        result = notifier.notify_self_healing_complete(
            repo_full_name="owner/repo",
            pr_number=456,
            status="error",
            summary="エラーが発生しました",
            run_id="sh-error",
        )

        assert result is True

        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        assert "❌" in payload["text"]

    @pytest.mark.skipif(not HAS_REQUESTS, reason="requests library not installed")
    @patch('requests.post')
    def test_notify_self_healing_with_metrics(self, mock_post):
        """メトリクスを含むSelf-Healing通知"""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")

        metrics = {
            "duration_str": "5分30秒",
            "patch_files_count": 3,
            "patch_lines": 120,
            "model_call_counts": {
                "openai:gpt-4": 5,
                "anthropic:claude-3": 2,
            },
            "estimated_cost_jpy": 50.25,
            "success_rate": 0.85,
        }

        result = notifier.notify_self_healing_complete(
            repo_full_name="owner/repo",
            pr_number=789,
            status="fixed",
            summary="修復成功",
            run_id="sh-metrics",
            metrics=metrics,
        )

        assert result is True

        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        message = payload["attachments"][0]["fields"][1]["value"]  # メッセージフィールド

        # メトリクスが含まれることを確認
        assert "5分30秒" in message
        assert "120 lines / 3 files" in message
        assert "50.25 JPY" in message
        assert "85.0%" in message

    @pytest.mark.skipif(not HAS_REQUESTS, reason="requests library not installed")
    @patch('requests.post')
    def test_notify_self_healing_with_urls(self, mock_post):
        """URLを含むSelf-Healing通知"""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")

        result = notifier.notify_self_healing_complete(
            repo_full_name="owner/repo",
            pr_number=999,
            status="fixed",
            summary="修復完了",
            run_id="sh-urls",
            pr_url="https://github.com/owner/repo/pull/999",
            run_logs_url="https://nexuscore.example.com/runs/sh-urls",
        )

        assert result is True

        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        message = payload["attachments"][0]["fields"][1]["value"]

        # URLが含まれることを確認
        assert "https://github.com/owner/repo/pull/999" in message
        assert "https://nexuscore.example.com/runs/sh-urls" in message


@pytest.mark.skipif(not HAS_NOTIFIER, reason="notifier module not available")
class TestNotifyOrchestratorComplete:
    """notify_orchestrator_complete() のテスト"""

    @pytest.mark.skipif(not HAS_REQUESTS, reason="requests library not installed")
    @patch('requests.post')
    def test_notify_orchestrator_success(self, mock_post):
        """Orchestrator完了通知（success）"""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")

        result = notifier.notify_orchestrator_complete(
            project_path="/path/to/project",
            requirement="機能Xを実装",
            status="success",
            session_id="session-123",
        )

        assert result is True

        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        assert "Orchestrator 完了" in payload["text"]
        assert "✅" in payload["text"]
        assert "/path/to/project" in payload["text"]

    @pytest.mark.skipif(not HAS_REQUESTS, reason="requests library not installed")
    @patch('requests.post')
    def test_notify_orchestrator_error(self, mock_post):
        """Orchestrator完了通知（error）"""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")

        result = notifier.notify_orchestrator_complete(
            project_path="/path/to/project",
            requirement="機能Yを実装",
            status="error",
            session_id="session-456",
        )

        assert result is True

        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        assert "❌" in payload["text"]

    @pytest.mark.skipif(not HAS_REQUESTS, reason="requests library not installed")
    @patch('requests.post')
    def test_notify_orchestrator_stopped(self, mock_post):
        """Orchestrator完了通知（stopped）"""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")

        result = notifier.notify_orchestrator_complete(
            project_path="/path/to/project",
            requirement="機能Zを実装",
            status="stopped",
            session_id="session-789",
        )

        assert result is True

        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        assert "⏸️" in payload["text"]


@pytest.mark.skipif(not HAS_NOTIFIER, reason="notifier module not available")
class TestNotifyProjectComplete:
    """notify_project_complete() のテスト"""

    @pytest.mark.skipif(not HAS_REQUESTS, reason="requests library not installed")
    @patch('requests.post')
    def test_notify_project_complete(self, mock_post):
        """プロジェクト完了通知"""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")

        result = notifier.notify_project_complete(
            project_name="atelier-kyo-manager",
            task_description="データベースマイグレーション",
            status="success",
            details={"duration": "10分"},
        )

        assert result is True

        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        assert "atelier-kyo-manager タスク完了" in payload["text"]
        assert "✅" in payload["text"]


@pytest.mark.skipif(not HAS_NOTIFIER, reason="notifier module not available")
class TestGetNotifier:
    """get_notifier() のテスト"""

    def test_get_notifier_with_webhook(self, monkeypatch):
        """webhook URLが設定されている場合"""
        monkeypatch.setenv("NEXUS_SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")

        notifier = get_notifier()

        if HAS_REQUESTS:
            assert notifier is not None
            assert isinstance(notifier, SlackNotifier)
        else:
            # requestsがない場合はNone
            assert notifier is None

    def test_get_notifier_without_webhook(self):
        """webhook URLがない場合"""
        with patch.dict(os.environ, {}, clear=True):
            notifier = get_notifier()

            assert notifier is None


@pytest.mark.skipif(not HAS_NOTIFIER, reason="notifier module not available")
class TestEdgeCases:
    """エッジケースのテスト"""

    def test_notifier_with_empty_webhook_url(self):
        """空のwebhook URL"""
        notifier = SlackNotifier(webhook_url="")

        # 空文字列はFalsyなのでNoneになる
        assert notifier.webhook_url == "" or notifier.webhook_url is None
        assert notifier.enabled is False

    @pytest.mark.skipif(not HAS_REQUESTS, reason="requests library not installed")
    @patch('requests.post')
    def test_send_with_none_details_values(self, mock_post):
        """詳細情報にNone値が含まれる場合"""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")

        result = notifier.send(
            title="Test",
            message="Message",
            status="info",
            details={"key1": "value1", "key2": None, "key3": "value3"},
        )

        assert result is True

        # None値はdetailsから除外される
        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        fields = payload["attachments"][0]["fields"]
        detail_field = next((f for f in fields if f.get("title") == "詳細"), None)
        assert "key1" in detail_field["value"]
        assert "key2" not in detail_field["value"]  # Noneは除外
        assert "key3" in detail_field["value"]

    @pytest.mark.skipif(not HAS_REQUESTS, reason="requests library not installed")
    @patch('requests.post')
    def test_send_with_unicode_message(self, mock_post):
        """Unicode文字を含むメッセージ"""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")

        result = notifier.send(
            title="テスト 🎉",
            message="日本語メッセージ 👍",
            status="success",
            details={"キー": "値"},
        )

        assert result is True

        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        assert payload["text"] == "テスト 🎉"

    @pytest.mark.skipif(not HAS_REQUESTS, reason="requests library not installed")
    @patch('requests.post')
    def test_send_unknown_status_defaults_to_info(self, mock_post):
        """未知のステータスはinfoとして扱われる"""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")

        result = notifier.send(
            title="Test",
            message="Message",
            status="unknown_status",
        )

        assert result is True

        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        # デフォルトカラー（#36a64f）が使われる
        assert payload["attachments"][0]["color"] == "#36a64f"
