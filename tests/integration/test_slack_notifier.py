"""
Slack 通知のテスト
"""
import pytest
from unittest.mock import Mock, patch

from nexuscore.core.notifier import SlackNotifier


def test_notify_self_healing_complete_with_metrics():
    """メトリクス付きの Self-Healing 通知が正しく送信されるか"""
    notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")

    # send メソッドをモック
    with patch.object(notifier, "send", return_value=True) as mock_send:
        success = notifier.notify_self_healing_complete(
            repo_full_name="owner/repo",
            pr_number=123,
            status="fixed",
            summary="Test summary",
            run_id="test-run-123",
            metrics={
                "duration_str": "5m 30s",
                "patch_files_count": 3,
                "patch_lines": 150,
                "model_call_counts": {"gpt-4.1": 5, "claude-3.5": 2},
                "estimated_cost_jpy": 123.45,
                "success_rate": 0.85,
            },
        )

        assert success is True
        assert mock_send.called

        # 呼び出し引数を確認
        call_args = mock_send.call_args
        assert call_args is not None
        kwargs = call_args.kwargs

        assert "実行時間: 5m 30s" in kwargs["message"]
        assert "パッチ: 150 lines / 3 files" in kwargs["message"]
        assert "使用モデル:" in kwargs["message"]
        assert "推定コスト: ~123.45 JPY" in kwargs["message"]
        assert "最近の成功率 (last 30): 85.0%" in kwargs["message"]


def test_notify_self_healing_complete_without_metrics():
    """メトリクスなしの Self-Healing 通知が正しく送信されるか"""
    notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")

    with patch.object(notifier, "send", return_value=True) as mock_send:
        success = notifier.notify_self_healing_complete(
            repo_full_name="owner/repo",
            pr_number=123,
            status="fixed",
            summary="Test summary",
            run_id="test-run-123",
        )

        assert success is True
        assert mock_send.called

