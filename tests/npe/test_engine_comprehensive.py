"""
npe/engine.py の包括的テスト

LLM実行エンジン（予算ガード付き）を網羅的にテストします。
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from nexuscore.npe import budget, engine
from nexuscore.npe.budget import BudgetDecision
from nexuscore.npe.engine import _estimate_tokens, guarded_llm_call

# =============================================================================
# Test _estimate_tokens
# =============================================================================


class TestEstimateTokens:
    """_estimate_tokens() のテスト"""

    def test_estimate_tokens_empty_string(self):
        """空文字列は0トークン"""
        assert _estimate_tokens("") == 0

    def test_estimate_tokens_short_text(self):
        """短いテキストのトークン見積り"""
        # "hello" = 5文字 / 3.8 ≈ 2トークン（切り上げ）
        tokens = _estimate_tokens("hello")
        assert tokens == 2

    def test_estimate_tokens_medium_text(self):
        """中程度のテキストのトークン見積り"""
        # 100文字 / 3.8 ≈ 27トークン
        text = "a" * 100
        tokens = _estimate_tokens(text)
        assert tokens == 27

    def test_estimate_tokens_large_text(self):
        """大きなテキストのトークン見積り"""
        # 10000文字 / 3.8 ≈ 2632トークン
        text = "x" * 10000
        tokens = _estimate_tokens(text)
        assert tokens == 2632

    def test_estimate_tokens_unicode_text(self):
        """Unicode テキストのトークン見積り"""
        # 日本語も文字数でカウント
        text = "こんにちは世界"
        tokens = _estimate_tokens(text)
        assert tokens == 2  # 7文字 / 3.8 ≈ 2

    def test_estimate_tokens_minimum_is_one(self):
        """最小トークン数は1"""
        # 1文字でも最低1トークン
        tokens = _estimate_tokens("a")
        assert tokens == 1

    def test_estimate_tokens_newlines_and_whitespace(self):
        """改行や空白もカウント"""
        text = "hello\nworld\t!"
        tokens = _estimate_tokens(text)
        assert tokens > 0

    def test_estimate_tokens_special_characters(self):
        """特殊文字を含むテキスト"""
        text = "!@#$%^&*()_+-=[]{}|;':,.<>?/`~"
        tokens = _estimate_tokens(text)
        assert tokens > 0


# =============================================================================
# Test guarded_llm_call
# =============================================================================


class TestGuardedLlmCall:
    """guarded_llm_call() のテスト"""

    @pytest.fixture
    def mock_decision_allow(self):
        """許可する BudgetDecision"""
        return BudgetDecision(
            allow=True,
            reason="ok",
            est_cost_jpy=1.0,
            est_prompt_tokens=100,
            est_completion_tokens=50,
            caps={},
        )

    @pytest.fixture
    def mock_decision_deny(self):
        """拒否する BudgetDecision"""
        return BudgetDecision(
            allow=False,
            reason="per-call cap exceeded",
            est_cost_jpy=100.0,
            est_prompt_tokens=10000,
            est_completion_tokens=10000,
            caps={"per_call_cap_jpy": 80.0},
        )

    def test_guarded_llm_call_success(self, mock_decision_allow):
        """正常なLLM呼び出し"""
        with patch.object(budget, "preflight_check", return_value=mock_decision_allow):
            with patch.object(budget, "record_estimate"):
                with patch.object(budget, "record_usage"):
                    with patch.object(engine, "log_transaction"):
                        llm_fn = Mock(return_value={"ok": True, "content": "response"})

                        result = guarded_llm_call(
                            model="gpt-5",
                            task="test",
                            system_prompt="system",
                            user_prompt="user",
                            llm_complete_fn=llm_fn,
                        )

        assert result["ok"] is True
        assert result["content"] == "response"
        assert "usage" in result

    def test_guarded_llm_call_blocked_by_budget(self, mock_decision_deny):
        """予算制限でブロックされる"""
        with patch.object(budget, "preflight_check", return_value=mock_decision_deny):
            with patch.object(budget, "record_estimate"):
                with patch.object(engine, "log_transaction"):
                    llm_fn = Mock()  # 呼ばれないはず

                    result = guarded_llm_call(
                        model="gpt-5",
                        task="expensive",
                        system_prompt="system",
                        user_prompt="user",
                        llm_complete_fn=llm_fn,
                    )

        assert result["ok"] is False
        assert "Budget guard rejected" in result["reason"]
        assert llm_fn.call_count == 0  # LLM は呼ばれない

    def test_guarded_llm_call_records_estimate(self, mock_decision_allow):
        """見積りを記録"""
        with patch.object(budget, "preflight_check", return_value=mock_decision_allow):
            with patch.object(budget, "record_estimate") as mock_record_estimate:
                with patch.object(budget, "record_usage"):
                    with patch.object(engine, "log_transaction"):
                        llm_fn = Mock(return_value={"ok": True, "content": "test"})

                        guarded_llm_call(
                            model="gpt-5",
                            task="test",
                            system_prompt="system",
                            user_prompt="user",
                            llm_complete_fn=llm_fn,
                        )

        mock_record_estimate.assert_called_once()
        call_args = mock_record_estimate.call_args[0]
        assert call_args[0] == "gpt-5"
        assert call_args[1] == "test"
        assert call_args[2] == mock_decision_allow

    def test_guarded_llm_call_records_usage(self, mock_decision_allow):
        """実測使用量を記録"""
        with patch.object(budget, "preflight_check", return_value=mock_decision_allow):
            with patch.object(budget, "record_estimate"):
                with patch.object(budget, "record_usage") as mock_record_usage:
                    with patch.object(engine, "log_transaction"):
                        llm_fn = Mock(
                            return_value={
                                "ok": True,
                                "content": "response",
                                "usage": {"prompt_tokens": 120, "completion_tokens": 80},
                            }
                        )

                        guarded_llm_call(
                            model="gpt-5",
                            task="test",
                            system_prompt="system",
                            user_prompt="user",
                            llm_complete_fn=llm_fn,
                        )

        mock_record_usage.assert_called_once()
        call_kwargs = mock_record_usage.call_args[1]
        assert call_kwargs["model"] == "gpt-5"
        assert call_kwargs["task"] == "test"
        assert call_kwargs["prompt_tokens"] == 120
        assert call_kwargs["completion_tokens"] == 80

    def test_guarded_llm_call_logs_transaction(self, mock_decision_allow):
        """監査ログを記録"""
        with patch.object(budget, "preflight_check", return_value=mock_decision_allow):
            with patch.object(budget, "record_estimate"):
                with patch.object(budget, "record_usage"):
                    with patch.object(engine, "log_transaction") as mock_log:
                        llm_fn = Mock(return_value={"ok": True, "content": "test"})

                        guarded_llm_call(
                            model="gpt-5",
                            task="test_task",
                            system_prompt="system",
                            user_prompt="user",
                            llm_complete_fn=llm_fn,
                        )

        mock_log.assert_called_once()
        log_data = mock_log.call_args[0][0]
        assert log_data["event"] == "llm_call"
        assert log_data["model"] == "gpt-5"
        assert log_data["task"] == "test_task"

    def test_guarded_llm_call_logs_blocked_transaction(self, mock_decision_deny):
        """ブロックされたトランザクションもログに記録"""
        with patch.object(budget, "preflight_check", return_value=mock_decision_deny):
            with patch.object(budget, "record_estimate"):
                with patch.object(engine, "log_transaction") as mock_log:
                    llm_fn = Mock()

                    guarded_llm_call(
                        model="gpt-5",
                        task="blocked_task",
                        system_prompt="system",
                        user_prompt="user",
                        llm_complete_fn=llm_fn,
                    )

        mock_log.assert_called_once()
        log_data = mock_log.call_args[0][0]
        assert log_data["event"] == "llm_blocked"
        assert log_data["reason"] == "per-call cap exceeded"

    def test_guarded_llm_call_uses_estimated_tokens_when_no_usage(self, mock_decision_allow):
        """usage情報がない場合は見積りトークンを使用"""
        with patch.object(budget, "preflight_check", return_value=mock_decision_allow):
            with patch.object(budget, "record_estimate"):
                with patch.object(budget, "record_usage") as mock_record_usage:
                    with patch.object(engine, "log_transaction"):
                        # usage情報なしのレスポンス
                        llm_fn = Mock(return_value={"ok": True, "content": "short"})

                        guarded_llm_call(
                            model="gpt-5",
                            task="test",
                            system_prompt="sys",
                            user_prompt="usr",
                            llm_complete_fn=llm_fn,
                        )

        # 見積りトークンが使われる
        call_kwargs = mock_record_usage.call_args[1]
        assert call_kwargs["prompt_tokens"] > 0  # 見積り値
        assert call_kwargs["completion_tokens"] > 0  # contentから見積り

    def test_guarded_llm_call_enriches_result_with_usage(self, mock_decision_allow):
        """結果にusage情報を追加"""
        with patch.object(budget, "preflight_check", return_value=mock_decision_allow):
            with patch.object(budget, "record_estimate"):
                with patch.object(budget, "record_usage"):
                    with patch.object(engine, "log_transaction"):
                        llm_fn = Mock(
                            return_value={
                                "ok": True,
                                "content": "response",
                                "usage": {"prompt_tokens": 100, "completion_tokens": 50},
                            }
                        )

                        result = guarded_llm_call(
                            model="gpt-5",
                            task="test",
                            system_prompt="system",
                            user_prompt="user",
                            llm_complete_fn=llm_fn,
                        )

        assert "usage" in result
        assert "cost_jpy" in result["usage"]
        assert result["usage"]["prompt_tokens"] == 100
        assert result["usage"]["completion_tokens"] == 50

    def test_guarded_llm_call_handles_non_dict_llm_response(self, mock_decision_allow):
        """辞書でないLLMレスポンスを処理"""
        with patch.object(budget, "preflight_check", return_value=mock_decision_allow):
            with patch.object(budget, "record_estimate"):
                with patch.object(budget, "record_usage"):
                    with patch.object(engine, "log_transaction"):
                        # 文字列レスポンス
                        llm_fn = Mock(return_value="plain text response")

                        result = guarded_llm_call(
                            model="gpt-5",
                            task="test",
                            system_prompt="system",
                            user_prompt="user",
                            llm_complete_fn=llm_fn,
                        )

        assert result["ok"] is True
        assert result["content"] == "plain text response"
        assert "usage" in result

    def test_guarded_llm_call_passes_correct_params_to_llm_fn(self, mock_decision_allow):
        """LLM関数に正しいパラメータを渡す"""
        with patch.object(budget, "preflight_check", return_value=mock_decision_allow):
            with patch.object(budget, "record_estimate"):
                with patch.object(budget, "record_usage"):
                    with patch.object(engine, "log_transaction"):
                        llm_fn = Mock(return_value={"ok": True, "content": "test"})

                        guarded_llm_call(
                            model="gpt-5-mini",
                            task="test",
                            system_prompt="system prompt",
                            user_prompt="user prompt",
                            llm_complete_fn=llm_fn,
                        )

        llm_fn.assert_called_once()
        call_kwargs = llm_fn.call_args[1]
        assert call_kwargs["model"] == "gpt-5-mini"
        assert call_kwargs["system_prompt"] == "system prompt"
        assert call_kwargs["user_prompt"] == "user prompt"


# =============================================================================
# Test Integration Scenarios
# =============================================================================


class TestIntegrationScenarios:
    """統合シナリオのテスト"""

    def test_full_successful_workflow(self):
        """成功する完全ワークフロー"""
        # 許可する決定
        decision = BudgetDecision(
            allow=True,
            reason="ok",
            est_cost_jpy=1.0,
            est_prompt_tokens=100,
            est_completion_tokens=50,
            caps={},
        )

        with patch.object(budget, "preflight_check", return_value=decision):
            with patch.object(budget, "record_estimate") as mock_estimate:
                with patch.object(budget, "record_usage") as mock_usage:
                    with patch.object(engine, "log_transaction") as mock_log:
                        llm_fn = Mock(
                            return_value={
                                "ok": True,
                                "content": "LLM response",
                                "usage": {"prompt_tokens": 110, "completion_tokens": 60},
                            }
                        )

                        result = guarded_llm_call(
                            model="gpt-5",
                            task="integration_test",
                            system_prompt="You are helpful",
                            user_prompt="Tell me a joke",
                            llm_complete_fn=llm_fn,
                        )

        # 全ステップが実行される
        assert mock_estimate.called
        assert mock_usage.called
        assert mock_log.called

        # 結果が正しい
        assert result["ok"] is True
        assert result["content"] == "LLM response"
        assert result["usage"]["cost_jpy"] > 0

    def test_full_blocked_workflow(self):
        """ブロックされる完全ワークフロー"""
        # 拒否する決定
        decision = BudgetDecision(
            allow=False,
            reason="daily hard cap exceeded",
            est_cost_jpy=200.0,
            est_prompt_tokens=10000,
            est_completion_tokens=10000,
            caps={"daily_hard_cap_jpy": 1500.0, "today_total_jpy": 1400.0},
        )

        with patch.object(budget, "preflight_check", return_value=decision):
            with patch.object(budget, "record_estimate") as mock_estimate:
                with patch.object(budget, "record_usage") as mock_usage:
                    with patch.object(engine, "log_transaction") as mock_log:
                        llm_fn = Mock()

                        result = guarded_llm_call(
                            model="gpt-5",
                            task="blocked_test",
                            system_prompt="system",
                            user_prompt="user",
                            llm_complete_fn=llm_fn,
                        )

        # 見積りとログのみ実行される
        assert mock_estimate.called
        assert not mock_usage.called  # 実行されないので記録されない
        assert mock_log.called  # ブロックログが記録される

        # LLMは呼ばれない
        assert not llm_fn.called

        # 結果がエラー
        assert result["ok"] is False
        assert "Budget guard rejected" in result["reason"]


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestEdgeCases:
    """エッジケースのテスト"""

    def test_empty_prompts(self):
        """空のプロンプト"""
        decision = BudgetDecision(
            allow=True,
            reason="ok",
            est_cost_jpy=0.0,
            est_prompt_tokens=0,
            est_completion_tokens=0,
            caps={},
        )

        with patch.object(budget, "preflight_check", return_value=decision):
            with patch.object(budget, "record_estimate"):
                with patch.object(budget, "record_usage"):
                    with patch.object(engine, "log_transaction"):
                        llm_fn = Mock(return_value={"ok": True, "content": ""})

                        result = guarded_llm_call(
                            model="gpt-5",
                            task="empty",
                            system_prompt="",
                            user_prompt="",
                            llm_complete_fn=llm_fn,
                        )

        assert result["ok"] is True

    def test_very_long_prompts(self):
        """非常に長いプロンプト"""
        long_prompt = "x" * 100000

        decision = BudgetDecision(
            allow=True,
            reason="ok",
            est_cost_jpy=50.0,
            est_prompt_tokens=26316,
            est_completion_tokens=512,
            caps={},
        )

        with patch.object(budget, "preflight_check", return_value=decision):
            with patch.object(budget, "record_estimate"):
                with patch.object(budget, "record_usage"):
                    with patch.object(engine, "log_transaction"):
                        llm_fn = Mock(return_value={"ok": True, "content": "response"})

                        result = guarded_llm_call(
                            model="gpt-5",
                            task="long",
                            system_prompt=long_prompt,
                            user_prompt="user",
                            llm_complete_fn=llm_fn,
                        )

        assert result["ok"] is True

    def test_unicode_prompts(self):
        """Unicode 文字を含むプロンプト"""
        decision = BudgetDecision(
            allow=True,
            reason="ok",
            est_cost_jpy=1.0,
            est_prompt_tokens=10,
            est_completion_tokens=10,
            caps={},
        )

        with patch.object(budget, "preflight_check", return_value=decision):
            with patch.object(budget, "record_estimate"):
                with patch.object(budget, "record_usage"):
                    with patch.object(engine, "log_transaction"):
                        llm_fn = Mock(return_value={"ok": True, "content": "返信"})

                        result = guarded_llm_call(
                            model="gpt-5",
                            task="unicode",
                            system_prompt="あなたは助手です",
                            user_prompt="こんにちは",
                            llm_complete_fn=llm_fn,
                        )

        assert result["ok"] is True
        assert result["content"] == "返信"

    def test_llm_fn_raises_exception(self):
        """LLM関数が例外を投げる"""
        decision = BudgetDecision(
            allow=True,
            reason="ok",
            est_cost_jpy=1.0,
            est_prompt_tokens=10,
            est_completion_tokens=10,
            caps={},
        )

        with patch.object(budget, "preflight_check", return_value=decision):
            with patch.object(budget, "record_estimate"):
                with patch.object(budget, "record_usage"):
                    with patch.object(engine, "log_transaction"):
                        llm_fn = Mock(side_effect=Exception("LLM API error"))

                        # 例外が伝播することを確認
                        with pytest.raises(Exception, match="LLM API error"):
                            guarded_llm_call(
                                model="gpt-5",
                                task="error",
                                system_prompt="system",
                                user_prompt="user",
                                llm_complete_fn=llm_fn,
                            )

    def test_llm_returns_ok_false(self):
        """LLMがok=Falseを返す"""
        decision = BudgetDecision(
            allow=True,
            reason="ok",
            est_cost_jpy=1.0,
            est_prompt_tokens=10,
            est_completion_tokens=10,
            caps={},
        )

        with patch.object(budget, "preflight_check", return_value=decision):
            with patch.object(budget, "record_estimate"):
                with patch.object(budget, "record_usage"):
                    with patch.object(engine, "log_transaction") as mock_log:
                        llm_fn = Mock(
                            return_value={
                                "ok": False,
                                "reason": "rate limit exceeded",
                                "content": "",
                            }
                        )

                        result = guarded_llm_call(
                            model="gpt-5",
                            task="failed",
                            system_prompt="system",
                            user_prompt="user",
                            llm_complete_fn=llm_fn,
                        )

        # ログに失敗が記録される
        log_data = mock_log.call_args[0][0]
        assert log_data["ok"] is False
        assert log_data["reason"] == "rate limit exceeded"

        # 結果も失敗
        assert result["ok"] is False

    def test_missing_usage_fields_in_llm_response(self):
        """LLMレスポンスにusageフィールドがない"""
        decision = BudgetDecision(
            allow=True,
            reason="ok",
            est_cost_jpy=1.0,
            est_prompt_tokens=10,
            est_completion_tokens=10,
            caps={},
        )

        with patch.object(budget, "preflight_check", return_value=decision):
            with patch.object(budget, "record_estimate"):
                with patch.object(budget, "record_usage") as mock_usage:
                    with patch.object(engine, "log_transaction"):
                        # usageフィールドなし
                        llm_fn = Mock(return_value={"ok": True, "content": "response"})

                        result = guarded_llm_call(
                            model="gpt-5",
                            task="no_usage",
                            system_prompt="system",
                            user_prompt="user",
                            llm_complete_fn=llm_fn,
                        )

        # 見積りトークンが使われる
        assert mock_usage.called
        call_kwargs = mock_usage.call_args[1]
        assert call_kwargs["prompt_tokens"] > 0

        # 結果にusageが追加される
        assert "usage" in result

    def test_partial_usage_fields_in_llm_response(self):
        """LLMレスポンスに一部のusageフィールドのみ"""
        decision = BudgetDecision(
            allow=True,
            reason="ok",
            est_cost_jpy=1.0,
            est_prompt_tokens=10,
            est_completion_tokens=10,
            caps={},
        )

        with patch.object(budget, "preflight_check", return_value=decision):
            with patch.object(budget, "record_estimate"):
                with patch.object(budget, "record_usage") as mock_usage:
                    with patch.object(engine, "log_transaction"):
                        # prompt_tokensのみ
                        llm_fn = Mock(
                            return_value={
                                "ok": True,
                                "content": "response",
                                "usage": {"prompt_tokens": 120},
                            }
                        )

                        result = guarded_llm_call(
                            model="gpt-5",
                            task="partial_usage",
                            system_prompt="system",
                            user_prompt="user",
                            llm_complete_fn=llm_fn,
                        )

        # prompt_tokensは実測、completion_tokensは見積り
        call_kwargs = mock_usage.call_args[1]
        assert call_kwargs["prompt_tokens"] == 120
        assert call_kwargs["completion_tokens"] > 0  # 見積り値

    def test_result_without_usage_field_gets_initialized(self):
        """usageフィールドがない結果に初期化"""
        decision = BudgetDecision(
            allow=True,
            reason="ok",
            est_cost_jpy=1.0,
            est_prompt_tokens=10,
            est_completion_tokens=10,
            caps={},
        )

        with patch.object(budget, "preflight_check", return_value=decision):
            with patch.object(budget, "record_estimate"):
                with patch.object(budget, "record_usage"):
                    with patch.object(engine, "log_transaction"):
                        llm_fn = Mock(return_value={"ok": True, "content": "test"})

                        result = guarded_llm_call(
                            model="gpt-5",
                            task="test",
                            system_prompt="system",
                            user_prompt="user",
                            llm_complete_fn=llm_fn,
                        )

        # usageフィールドが追加される
        assert "usage" in result
        assert "prompt_tokens" in result["usage"]
        assert "completion_tokens" in result["usage"]
        assert "cost_jpy" in result["usage"]

    def test_zero_length_content_in_response(self):
        """レスポンスに空のコンテンツ"""
        decision = BudgetDecision(
            allow=True,
            reason="ok",
            est_cost_jpy=1.0,
            est_prompt_tokens=10,
            est_completion_tokens=10,
            caps={},
        )

        with patch.object(budget, "preflight_check", return_value=decision):
            with patch.object(budget, "record_estimate"):
                with patch.object(budget, "record_usage") as mock_usage:
                    with patch.object(engine, "log_transaction"):
                        llm_fn = Mock(return_value={"ok": True, "content": ""})

                        result = guarded_llm_call(
                            model="gpt-5",
                            task="empty_content",
                            system_prompt="system",
                            user_prompt="user",
                            llm_complete_fn=llm_fn,
                        )

        # completion_tokensは0になる（空文字列）
        call_kwargs = mock_usage.call_args[1]
        assert call_kwargs["completion_tokens"] == 0

    def test_different_models(self):
        """異なるモデルで呼び出し"""
        models = ["gpt-5", "gpt-5-mini", "gemini-2.5-pro", "gemini-2.5-flash"]

        for model in models:
            decision = BudgetDecision(
                allow=True,
                reason="ok",
                est_cost_jpy=1.0,
                est_prompt_tokens=10,
                est_completion_tokens=10,
                caps={},
            )

            with patch.object(budget, "preflight_check", return_value=decision):
                with patch.object(budget, "record_estimate"):
                    with patch.object(budget, "record_usage") as mock_usage:
                        with patch.object(engine, "log_transaction"):
                            llm_fn = Mock(return_value={"ok": True, "content": "test"})

                            guarded_llm_call(
                                model=model,
                                task="test",
                                system_prompt="system",
                                user_prompt="user",
                                llm_complete_fn=llm_fn,
                            )

            # モデル名が正しく記録される
            call_kwargs = mock_usage.call_args[1]
            assert call_kwargs["model"] == model
