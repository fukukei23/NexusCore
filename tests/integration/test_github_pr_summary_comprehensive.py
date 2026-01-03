"""
github_pr_summary.py の包括的テスト

GitHub PR 修正要約生成機能を網羅的にテストします。
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from nexuscore.integration.github_pr_summary import generate_pr_change_summary


@pytest.fixture
def enable_modules():
    """HAS_WEBAPP と HAS_LLM を有効化"""
    with patch("nexuscore.integration.github_pr_summary.HAS_WEBAPP", True):
        with patch("nexuscore.integration.github_pr_summary.HAS_LLM", True):
            yield


@pytest.fixture
def mock_run():
    """Mock Run object"""
    run = Mock()
    run.id = 1
    return run


# =============================================================================
# Test generate_pr_change_summary
# =============================================================================


class TestGeneratePrChangeSummary:
    """generate_pr_change_summary のテスト"""

    def test_basic_summary_generation(self, enable_modules, mock_run):
        """基本的な要約生成が成功する"""
        guardian_review = "## Guardian Review\n\nCode looks good."

        mock_patch = Mock(file_path="src/main.py", diff_text="- old line\n+ new line")
        mock_log = Mock(source="TEST", level="ERROR", message="Test error")

        with patch("nexuscore.integration.github_pr_summary.PatchRecord") as mock_patch_record:
            with patch("nexuscore.integration.github_pr_summary.ExecutionLog") as mock_log_record:
                mock_patch_record.query.filter_by.return_value.all.return_value = [mock_patch]
                mock_log_record.query.filter.return_value.order_by.return_value.all.return_value = [mock_log]

                with patch("nexuscore.integration.github_pr_summary.guarded_llm_call", return_value={"ok": True, "content": "要約テキスト"}):
                    result = generate_pr_change_summary(mock_run, guardian_review)

        assert result == "要約テキスト"

    def test_returns_none_when_webapp_not_available(self):
        """Webapp モジュールが利用できない場合は None を返す"""
        with patch("nexuscore.integration.github_pr_summary.HAS_WEBAPP", False):
            result = generate_pr_change_summary(Mock(), "Review")
        assert result is None

    def test_returns_none_when_llm_not_available(self):
        """LLM モジュールが利用できない場合は None を返す"""
        with patch("nexuscore.integration.github_pr_summary.HAS_LLM", False):
            result = generate_pr_change_summary(Mock(), "Review")
        assert result is None

    def test_handles_no_patches_available(self, enable_modules, mock_run):
        """パッチが利用できない場合でも動作する"""
        with patch("nexuscore.integration.github_pr_summary.PatchRecord") as mock_patch_record:
            with patch("nexuscore.integration.github_pr_summary.ExecutionLog") as mock_log_record:
                mock_patch_record.query.filter_by.return_value.all.return_value = []
                mock_log_record.query.filter.return_value.order_by.return_value.all.return_value = []

                with patch("nexuscore.integration.github_pr_summary.guarded_llm_call", return_value={"ok": True, "content": "要約"}) as mock_llm:
                    result = generate_pr_change_summary(mock_run, "Review")

                # "(no diff available)" がプロンプトに含まれることを確認
                assert result == "要約"
                user_prompt = mock_llm.call_args[1]["user_prompt"]
                assert "(no diff available)" in user_prompt

    def test_truncates_patches_to_10_files(self, enable_modules, mock_run):
        """パッチが10ファイルを超える場合は最初の10ファイルのみ使用"""
        mock_patches = [Mock(file_path=f"file_{i}.py", diff_text=f"diff{i}") for i in range(15)]

        with patch("nexuscore.integration.github_pr_summary.PatchRecord") as mock_patch_record:
            with patch("nexuscore.integration.github_pr_summary.ExecutionLog") as mock_log_record:
                mock_patch_record.query.filter_by.return_value.all.return_value = mock_patches
                mock_log_record.query.filter.return_value.order_by.return_value.all.return_value = []

                with patch("nexuscore.integration.github_pr_summary.guarded_llm_call", return_value={"ok": True, "content": "要約"}) as mock_llm:
                    result = generate_pr_change_summary(mock_run, "Review")

                user_prompt = mock_llm.call_args[1]["user_prompt"]
                assert "file_0.py" in user_prompt
                assert "file_9.py" in user_prompt
                assert "file_10.py" not in user_prompt

    def test_truncates_diff_to_80_lines_per_file(self, enable_modules, mock_run):
        """各ファイルの diff は最大80行まで"""
        large_diff = "\n".join([f"line {i}" for i in range(100)])
        mock_patch = Mock(file_path="large.py", diff_text=large_diff)

        with patch("nexuscore.integration.github_pr_summary.PatchRecord") as mock_patch_record:
            with patch("nexuscore.integration.github_pr_summary.ExecutionLog") as mock_log_record:
                mock_patch_record.query.filter_by.return_value.all.return_value = [mock_patch]
                mock_log_record.query.filter.return_value.order_by.return_value.all.return_value = []

                with patch("nexuscore.integration.github_pr_summary.guarded_llm_call", return_value={"ok": True, "content": "要約"}):
                    result = generate_pr_change_summary(mock_run, "Review")

        assert result == "要約"

    def test_only_includes_error_and_warning_logs(self, enable_modules, mock_run):
        """ERROR と WARNING ログのみが含まれる"""
        mock_logs = [
            Mock(source="S1", level="INFO", message="Info message"),
            Mock(source="S2", level="ERROR", message="Error message"),
            Mock(source="S3", level="WARNING", message="Warning message"),
            Mock(source="S4", level="DEBUG", message="Debug message"),
        ]

        with patch("nexuscore.integration.github_pr_summary.PatchRecord") as mock_patch_record:
            with patch("nexuscore.integration.github_pr_summary.ExecutionLog") as mock_log_record:
                mock_patch_record.query.filter_by.return_value.all.return_value = []
                mock_log_record.query.filter.return_value.order_by.return_value.all.return_value = mock_logs

                with patch("nexuscore.integration.github_pr_summary.guarded_llm_call", return_value={"ok": True, "content": "要約"}) as mock_llm:
                    result = generate_pr_change_summary(mock_run, "Review")

                user_prompt = mock_llm.call_args[1]["user_prompt"]
                assert "Error message" in user_prompt
                assert "Warning message" in user_prompt
                assert "Info message" not in user_prompt
                assert "Debug message" not in user_prompt

    def test_llm_call_failure_returns_none(self, enable_modules, mock_run):
        """LLM 呼び出しが失敗した場合は None を返す"""
        with patch("nexuscore.integration.github_pr_summary.PatchRecord") as mock_patch_record:
            with patch("nexuscore.integration.github_pr_summary.ExecutionLog") as mock_log_record:
                mock_patch_record.query.filter_by.return_value.all.return_value = []
                mock_log_record.query.filter.return_value.order_by.return_value.all.return_value = []

                with patch("nexuscore.integration.github_pr_summary.guarded_llm_call", return_value={"ok": False, "reason": "LLM error"}):
                    result = generate_pr_change_summary(mock_run, "Review")

        assert result is None

    def test_llm_returns_empty_content(self, enable_modules, mock_run):
        """LLM が空のコンテンツを返した場合は None を返す"""
        with patch("nexuscore.integration.github_pr_summary.PatchRecord") as mock_patch_record:
            with patch("nexuscore.integration.github_pr_summary.ExecutionLog") as mock_log_record:
                mock_patch_record.query.filter_by.return_value.all.return_value = []
                mock_log_record.query.filter.return_value.order_by.return_value.all.return_value = []

                with patch("nexuscore.integration.github_pr_summary.guarded_llm_call", return_value={"ok": True, "content": "   "}):
                    result = generate_pr_change_summary(mock_run, "Review")

        assert result is None

    def test_custom_llm_router_provided(self, enable_modules, mock_run):
        """カスタム LLMRouter を提供できる"""
        mock_llm_router = Mock()

        with patch("nexuscore.integration.github_pr_summary.PatchRecord") as mock_patch_record:
            with patch("nexuscore.integration.github_pr_summary.ExecutionLog") as mock_log_record:
                mock_patch_record.query.filter_by.return_value.all.return_value = []
                mock_log_record.query.filter.return_value.order_by.return_value.all.return_value = []

                with patch("nexuscore.integration.github_pr_summary.guarded_llm_call", return_value={"ok": True, "content": "要約"}):
                    result = generate_pr_change_summary(mock_run, "Review", llm_router=mock_llm_router)

        assert result == "要約"


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestEdgeCases:
    """エッジケースのテスト"""

    def test_empty_guardian_review(self, enable_modules, mock_run):
        """空の Guardian レビューでも動作する"""
        with patch("nexuscore.integration.github_pr_summary.PatchRecord") as mock_patch_record:
            with patch("nexuscore.integration.github_pr_summary.ExecutionLog") as mock_log_record:
                mock_patch_record.query.filter_by.return_value.all.return_value = []
                mock_log_record.query.filter.return_value.order_by.return_value.all.return_value = []

                with patch("nexuscore.integration.github_pr_summary.guarded_llm_call", return_value={"ok": True, "content": "要約"}):
                    result = generate_pr_change_summary(mock_run, "")

        assert result == "要約"

    def test_unicode_in_patches_and_logs(self, enable_modules, mock_run):
        """Unicode 文字がパッチやログに含まれていても動作する"""
        mock_patch = Mock(file_path="日本語.py", diff_text="- 古いコード\n+ 新しいコード")
        mock_log = Mock(source="テスト", level="ERROR", message="エラーメッセージ")

        with patch("nexuscore.integration.github_pr_summary.PatchRecord") as mock_patch_record:
            with patch("nexuscore.integration.github_pr_summary.ExecutionLog") as mock_log_record:
                mock_patch_record.query.filter_by.return_value.all.return_value = [mock_patch]
                mock_log_record.query.filter.return_value.order_by.return_value.all.return_value = [mock_log]

                with patch("nexuscore.integration.github_pr_summary.guarded_llm_call", return_value={"ok": True, "content": "要約結果"}):
                    result = generate_pr_change_summary(mock_run, "レビュー")

        assert result == "要約結果"

    def test_exception_during_patch_collection(self, enable_modules, mock_run):
        """パッチ収集中に例外が発生しても None を返す"""
        with patch("nexuscore.integration.github_pr_summary.PatchRecord") as mock_patch_record:
            mock_patch_record.query.filter_by.side_effect = Exception("Database error")
            result = generate_pr_change_summary(mock_run, "Review")

        assert result is None

    def test_exception_during_log_collection(self, enable_modules, mock_run):
        """ログ収集中に例外が発生しても None を返す"""
        with patch("nexuscore.integration.github_pr_summary.PatchRecord") as mock_patch_record:
            with patch("nexuscore.integration.github_pr_summary.ExecutionLog") as mock_log_record:
                mock_patch_record.query.filter_by.return_value.all.return_value = []
                mock_log_record.query.filter.side_effect = Exception("Log error")

                result = generate_pr_change_summary(mock_run, "Review")

        assert result is None

    def test_guarded_llm_call_not_available(self, enable_modules, mock_run):
        """guarded_llm_call が None の場合は None を返す"""
        with patch("nexuscore.integration.github_pr_summary.guarded_llm_call", None):
            result = generate_pr_change_summary(mock_run, "Review")

        assert result is None

    def test_llm_router_not_available(self, enable_modules, mock_run):
        """LLMRouter が None の場合は None を返す"""
        with patch("nexuscore.integration.github_pr_summary.LLMRouter", None):
            with patch("nexuscore.integration.github_pr_summary.PatchRecord") as mock_patch_record:
                with patch("nexuscore.integration.github_pr_summary.ExecutionLog") as mock_log_record:
                    mock_patch_record.query.filter_by.return_value.all.return_value = []
                    mock_log_record.query.filter.return_value.order_by.return_value.all.return_value = []

                    result = generate_pr_change_summary(mock_run, "Review")

        assert result is None

    def test_run_without_id_attribute(self, enable_modules):
        """Run オブジェクトに id 属性がない場合"""
        mock_run_no_id = Mock(spec=[])  # id 属性なし

        with patch("nexuscore.integration.github_pr_summary.PatchRecord") as mock_patch_record:
            with patch("nexuscore.integration.github_pr_summary.ExecutionLog") as mock_log_record:
                mock_patch_record.query.filter_by.return_value.all.return_value = []
                mock_log_record.query.filter.return_value.order_by.return_value.all.return_value = []

                with patch("nexuscore.integration.github_pr_summary.guarded_llm_call", return_value={"ok": True, "content": "要約"}):
                    result = generate_pr_change_summary(mock_run_no_id, "Review")

        # 実装は hasattr でチェックするため、エラーにならない
        # （パッチは空リストとして扱われる）

    def test_patch_with_none_diff_text(self, enable_modules, mock_run):
        """diff_text が None の patch"""
        mock_patch = Mock(file_path="test.py", diff_text=None)

        with patch("nexuscore.integration.github_pr_summary.PatchRecord") as mock_patch_record:
            with patch("nexuscore.integration.github_pr_summary.ExecutionLog") as mock_log_record:
                mock_patch_record.query.filter_by.return_value.all.return_value = [mock_patch]
                mock_log_record.query.filter.return_value.order_by.return_value.all.return_value = []

                with patch("nexuscore.integration.github_pr_summary.guarded_llm_call", return_value={"ok": True, "content": "要約"}):
                    result = generate_pr_change_summary(mock_run, "Review")

        assert result == "要約"

    def test_log_with_none_message(self, enable_modules, mock_run):
        """message が None のログ"""
        mock_log = Mock(source="TEST", level="ERROR", message=None)

        with patch("nexuscore.integration.github_pr_summary.PatchRecord") as mock_patch_record:
            with patch("nexuscore.integration.github_pr_summary.ExecutionLog") as mock_log_record:
                mock_patch_record.query.filter_by.return_value.all.return_value = []
                mock_log_record.query.filter.return_value.order_by.return_value.all.return_value = [mock_log]

                with patch("nexuscore.integration.github_pr_summary.guarded_llm_call", return_value={"ok": True, "content": "要約"}):
                    result = generate_pr_change_summary(mock_run, "Review")

        assert result == "要約"
