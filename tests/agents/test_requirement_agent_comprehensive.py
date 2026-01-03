"""
============================================================================
Comprehensive Tests for RequirementAgent
============================================================================
高品質テストの原則:
- 外部依存（Gradio UI、LLM API）のみモック
- 実際のビジネスロジックをテスト
- エッジケースとエラー条件をカバー
============================================================================
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from nexuscore.agents.requirement_agent import (
    RequirementAgent,
    TextLocalization,
    StateMachine,
)


# ============================================================================
# Tests: TextLocalization
# ============================================================================


class TestTextLocalization:
    def test_init_with_japanese(self):
        """日本語で初期化"""
        text = TextLocalization(language="ja")
        assert text.language == "ja"
        assert text["title"] == "NexusCore: 対話型 要件定義エージェント"

    def test_init_with_english(self):
        """英語で初期化"""
        text = TextLocalization(language="en")
        assert text.language == "en"
        assert text["title"] == "NexusCore: Interactive Requirement Agent"

    def test_fallback_to_english(self):
        """未知の言語は英語にフォールバック"""
        text = TextLocalization(language="fr")
        assert text["title"] == "NexusCore: Interactive Requirement Agent"

    def test_unknown_key_returns_placeholder(self):
        """未知のキーはプレースホルダーを返す"""
        text = TextLocalization()
        assert text["unknown_key"] == "<unknown_key>"

    def test_all_japanese_keys_exist(self):
        """すべての日本語キーが存在"""
        text = TextLocalization(language="ja")
        required_keys = [
            "title", "boot_msg", "initial_greeting", "status_ready",
            "status_thinking", "status_suggesting", "status_finished",
            "input_placeholder", "send_button", "finish_button",
            "final_output_label", "yes_button", "no_button", "suggest_button"
        ]
        for key in required_keys:
            assert text[key] != f"<{key}>"

    def test_all_english_keys_exist(self):
        """すべての英語キーが存在"""
        text = TextLocalization(language="en")
        required_keys = [
            "title", "boot_msg", "initial_greeting", "status_ready"
        ]
        for key in required_keys:
            assert text[key] != f"<{key}>"


# ============================================================================
# Tests: StateMachine
# ============================================================================


class TestStateMachine:
    def test_init_with_agent(self):
        """エージェントで初期化"""
        agent = RequirementAgent()
        fsm = StateMachine(agent)
        assert fsm.agent == agent
        assert fsm.state is not None
        assert "state" in fsm.state

    def test_transition_updates_state(self):
        """遷移が状態を更新"""
        agent = RequirementAgent()
        fsm = StateMachine(agent)
        initial_state = fsm.state["state"]

        responses = fsm.transition("ユーザー入力")

        # 状態が変わる
        assert fsm.state["state"] != initial_state
        # レスポンスが返される
        assert isinstance(responses, list)


# ============================================================================
# Tests: RequirementAgent.__init__
# ============================================================================


class TestRequirementAgentInit:
    def test_init_with_defaults(self):
        """デフォルト値で初期化"""
        agent = RequirementAgent()
        assert agent.language == "ja"
        assert agent.text is not None
        assert agent.final_requirements is None
        assert agent.use_ui is False
        assert agent._initial_requirement == ""

    def test_init_with_japanese(self):
        """日本語で初期化"""
        agent = RequirementAgent(language="ja", use_ui=False)
        assert agent.language == "ja"
        assert agent.text["title"] == "NexusCore: 対話型 要件定義エージェント"

    def test_init_with_english(self):
        """英語で初期化"""
        agent = RequirementAgent(language="en", use_ui=False)
        assert agent.language == "en"
        assert agent.text["title"] == "NexusCore: Interactive Requirement Agent"

    def test_init_with_ui_enabled(self):
        """UIモード有効で初期化"""
        agent = RequirementAgent(use_ui=True)
        assert agent.use_ui is True


# ============================================================================
# Tests: _get_initial_state
# ============================================================================


class TestGetInitialState:
    def test_returns_initial_state(self):
        """初期状態を返す"""
        agent = RequirementAgent()
        state = agent._get_initial_state()

        assert "session_id" in state
        assert "history" in state
        assert "state" in state
        assert state["state"] == "INIT"
        assert isinstance(state["history"], list)
        assert len(state["history"]) == 0

    def test_unique_session_ids(self):
        """各呼び出しでユニークなセッションIDを生成"""
        agent = RequirementAgent()
        state1 = agent._get_initial_state()
        state2 = agent._get_initial_state()

        assert state1["session_id"] != state2["session_id"]


# ============================================================================
# Tests: generate_final_spec
# ============================================================================


class TestGenerateFinalSpec:
    def test_with_user_messages(self):
        """ユーザーメッセージから仕様を生成"""
        agent = RequirementAgent()
        history = [
            {"role": "assistant", "content": "こんにちは"},
            {"role": "user", "content": "Webアプリを作りたい"},
            {"role": "assistant", "content": "どんな機能が必要ですか？"},
            {"role": "user", "content": "ログイン機能とダッシュボード"},
        ]

        spec = agent.generate_final_spec(history)

        assert "summary" in spec
        assert "details" in spec
        assert "ログイン機能とダッシュボード" in spec["details"]

    def test_with_no_user_messages(self):
        """ユーザーメッセージがない場合"""
        agent = RequirementAgent()
        history = [{"role": "assistant", "content": "こんにちは"}]

        spec = agent.generate_final_spec(history)

        assert "summary" in spec
        assert "details" in spec
        assert spec["details"] == "No user input."

    def test_with_empty_history(self):
        """履歴が空の場合"""
        agent = RequirementAgent()
        spec = agent.generate_final_spec([])

        assert spec["details"] == "No user input."


# ============================================================================
# Tests: set_initial_requirement
# ============================================================================


class TestSetInitialRequirement:
    def test_sets_initial_requirement(self):
        """初期要件を設定"""
        agent = RequirementAgent()
        agent.set_initial_requirement("Eコマースサイトを作成")

        assert agent._initial_requirement == "Eコマースサイトを作成"

    def test_overwrites_previous_requirement(self):
        """前の要件を上書き"""
        agent = RequirementAgent()
        agent.set_initial_requirement("要件1")
        agent.set_initial_requirement("要件2")

        assert agent._initial_requirement == "要件2"


# ============================================================================
# Tests: analyze_requirement
# ============================================================================


class TestAnalyzeRequirement:
    @patch.object(RequirementAgent, "execute_llm_task")
    def test_with_valid_json_response(self, mock_execute):
        """有効なJSONレスポンスで要件を分析"""
        mock_execute.return_value = json.dumps({
            "summary": "Webアプリケーション",
            "features": ["ユーザー認証", "ダッシュボード"],
            "constraints": ["レスポンス時間は1秒以内"],
            "acceptance_criteria": ["全機能がテスト済み"]
        })

        agent = RequirementAgent()
        result = agent.analyze_requirement("Webアプリを作成")

        assert result["summary"] == "Webアプリケーション"
        assert len(result["features"]) == 2
        assert "ユーザー認証" in result["features"]
        assert agent.final_requirements == result
        mock_execute.assert_called_once()

    @patch.object(RequirementAgent, "execute_llm_task")
    def test_with_invalid_json_response(self, mock_execute):
        """無効なJSONレスポンスの場合"""
        mock_execute.return_value = "This is not JSON"

        agent = RequirementAgent()
        result = agent.analyze_requirement("要件")

        # フォールバック値が返される
        assert "summary" in result
        assert "features" in result
        assert isinstance(result["features"], list)

    @patch.object(RequirementAgent, "execute_llm_task")
    def test_with_empty_requirement(self, mock_execute):
        """空の要件の場合"""
        mock_execute.return_value = json.dumps({
            "summary": "No requirement",
            "features": [],
            "constraints": [],
            "acceptance_criteria": []
        })

        agent = RequirementAgent()
        result = agent.analyze_requirement("")

        # LLMが呼ばれる
        mock_execute.assert_called_once()

    @patch.object(RequirementAgent, "execute_llm_task")
    def test_uses_initial_requirement_if_empty(self, mock_execute):
        """空の場合は初期要件を使用"""
        mock_execute.return_value = json.dumps({
            "summary": "Test",
            "features": [],
            "constraints": [],
            "acceptance_criteria": []
        })

        agent = RequirementAgent()
        agent.set_initial_requirement("初期要件")
        agent.analyze_requirement("")

        # プロンプトに初期要件が含まれる
        call_args = mock_execute.call_args[0][0]
        assert "初期要件" in call_args

    @patch("nexuscore.agents.requirement_agent.sanitize_json_like")
    @patch.object(RequirementAgent, "execute_llm_task")
    def test_llm_exception_handling(self, mock_execute, mock_sanitize):
        """LLM呼び出しの例外処理"""
        mock_execute.return_value = "valid json string"
        mock_sanitize.side_effect = Exception("Parse error")

        agent = RequirementAgent()
        result = agent.analyze_requirement("要件")

        # フォールバック値が返される
        assert "summary" in result
        assert "Auto-generated draft feature list" in result["features"]


# ============================================================================
# Tests: launch_gradio_ui
# ============================================================================


class TestLaunchGradioUi:
    def test_headless_mode_calls_analyze_requirement(self):
        """ヘッドレスモードではanalyze_requirementを呼ぶ"""
        agent = RequirementAgent(use_ui=False)
        agent.set_initial_requirement("テスト要件")

        with patch.object(agent, "analyze_requirement") as mock_analyze:
            mock_analyze.return_value = {"summary": "Test"}
            result = agent.launch_gradio_ui()

            mock_analyze.assert_called_once_with("テスト要件")
            assert result == {"summary": "Test"}

    @patch("nexuscore.agents.requirement_agent.gr")
    def test_ui_mode_creates_gradio_blocks(self, mock_gr):
        """UIモードではGradio Blocksを作成"""
        agent = RequirementAgent(use_ui=True)

        mock_blocks = MagicMock()
        mock_gr.Blocks.return_value.__enter__.return_value = mock_blocks

        # launch()を呼ばないようにモック
        mock_blocks.queue.return_value.launch.return_value = None

        agent.launch_gradio_ui(share=False)

        # Gradio Blocksが作成される
        mock_gr.Blocks.assert_called_once()


# ============================================================================
# Tests: Integration scenarios
# ============================================================================


class TestIntegrationScenarios:
    @patch.object(RequirementAgent, "execute_llm_task")
    def test_full_headless_workflow(self, mock_execute):
        """完全なヘッドレスワークフロー"""
        mock_execute.return_value = json.dumps({
            "summary": "タスク管理アプリ",
            "features": ["タスク作成", "タスク編集", "タスク削除"],
            "constraints": ["モバイル対応"],
            "acceptance_criteria": ["すべてのCRUD操作が動作する"]
        })

        agent = RequirementAgent(language="ja", use_ui=False)
        agent.set_initial_requirement("タスク管理アプリを作りたい")

        result = agent.launch_gradio_ui()

        assert result["summary"] == "タスク管理アプリ"
        assert len(result["features"]) == 3
        assert agent.final_requirements == result

    def test_state_machine_integration(self):
        """StateMachineとの統合"""
        agent = RequirementAgent()
        fsm = StateMachine(agent)

        # 初期状態
        assert fsm.state["state"] == "INIT"

        # 遷移
        fsm.transition("要件を入力")

        # 状態が更新される
        assert fsm.state["state"] == "FINALIZING"
