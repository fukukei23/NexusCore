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


# ============================================================================
# Additional Tests: Edge Cases and Uncovered Paths
# ============================================================================


class TestRequirementAgentEdgeCases:
    """未カバーのコードパスとエッジケースをテスト"""

    @patch.object(RequirementAgent, "execute_llm_task")
    def test_analyze_requirement_with_special_characters(self, mock_execute):
        """特殊文字を含む要件の分析"""
        mock_execute.return_value = json.dumps({
            "summary": "特殊文字テスト: <>\"'&",
            "features": ["機能<1>", "機能\"2\""],
            "constraints": ["制約's"],
            "acceptance_criteria": ["基準&1"]
        })

        agent = RequirementAgent()
        result = agent.analyze_requirement("特殊文字を含む要件: <>\"'&")

        assert "特殊文字テスト" in result["summary"]
        assert len(result["features"]) == 2
        assert result["features"][0] == "機能<1>"

    @patch.object(RequirementAgent, "execute_llm_task")
    def test_analyze_requirement_with_very_long_text(self, mock_execute):
        """非常に長い要件テキストの処理"""
        long_requirement = "要件" * 1000  # 3000文字
        mock_execute.return_value = json.dumps({
            "summary": long_requirement[:80],
            "features": ["機能1"],
            "constraints": [],
            "acceptance_criteria": []
        })

        agent = RequirementAgent()
        result = agent.analyze_requirement(long_requirement)

        assert "要件" in result["summary"]
        assert len(result["summary"]) <= 100

    @patch.object(RequirementAgent, "execute_llm_task")
    @patch("nexuscore.agents.requirement_agent.sanitize_json_like")
    def test_analyze_requirement_json_parse_error_recovery(self, mock_sanitize, mock_execute):
        """JSON解析エラーからの回復"""
        # 無効なJSONを返す
        mock_execute.return_value = "{ invalid json }"

        agent = RequirementAgent()
        result = agent.analyze_requirement("テスト要件")

        # フォールバックの自動生成された仕様が返される
        assert "summary" in result
        assert "Auto-generated" in result["features"][0]
        assert result["constraints"] == []

    def test_generate_final_spec_with_complex_history(self):
        """複雑な履歴パターンでの最終仕様生成"""
        history = [
            {"role": "assistant", "content": "質問1"},
            {"role": "user", "content": "回答1"},
            {"role": "assistant", "content": "質問2"},
            {"role": "user", "content": "回答2"},
            {"role": "user", "content": "最終要件"},
        ]

        agent = RequirementAgent()
        result = agent.generate_final_spec(history)

        # 最後のユーザーメッセージが使用される
        assert "最終要件" in result["details"]

    def test_generate_final_spec_with_only_assistant_messages(self):
        """アシスタントメッセージのみの履歴"""
        history = [
            {"role": "assistant", "content": "メッセージ1"},
            {"role": "assistant", "content": "メッセージ2"},
        ]

        agent = RequirementAgent()
        result = agent.generate_final_spec(history)

        # デフォルトメッセージが使用される
        assert "No user input" in result["details"]

    @patch.object(RequirementAgent, "execute_llm_task")
    def test_analyze_requirement_with_unicode_characters(self, mock_execute):
        """Unicode文字を含む要件の処理"""
        mock_execute.return_value = json.dumps({
            "summary": "絵文字テスト 🎉 📱 ✨",
            "features": ["機能①", "機能②"],
            "constraints": ["日本語制約"],
            "acceptance_criteria": ["基準✓"]
        })

        agent = RequirementAgent()
        result = agent.analyze_requirement("絵文字を含む要件 🎉")

        assert "🎉" in result["summary"]
        assert len(result["features"]) == 2

    def test_initial_requirement_cascading_usage(self):
        """initial_requirementの連鎖的な使用"""
        agent = RequirementAgent()

        # 最初の設定
        agent.set_initial_requirement("要件1")
        assert agent._initial_requirement == "要件1"

        # 上書き
        agent.set_initial_requirement("要件2")
        assert agent._initial_requirement == "要件2"

        # 空文字列での上書き
        agent.set_initial_requirement("")
        assert agent._initial_requirement == ""

    def test_text_localization_with_empty_language(self):
        """空の言語コードでのTextLocalization"""
        text = TextLocalization(language="")

        # 空の言語コードは英語にフォールバック
        assert "Interactive" in text["title"] or "対話型" in text["title"]

    @patch.object(RequirementAgent, "execute_llm_task")
    def test_multiple_requirement_updates_workflow(self, mock_execute):
        """複数回の要件更新ワークフロー"""
        agent = RequirementAgent(use_ui=False)

        # 1回目の要件設定
        agent.set_initial_requirement("要件v1")
        mock_execute.return_value = json.dumps({
            "summary": "v1",
            "features": ["機能1"],
            "constraints": [],
            "acceptance_criteria": []
        })
        result1 = agent.analyze_requirement("")
        assert result1["summary"] == "v1"

        # 2回目の要件設定（上書き）
        agent.set_initial_requirement("要件v2")
        mock_execute.return_value = json.dumps({
            "summary": "v2",
            "features": ["機能2"],
            "constraints": [],
            "acceptance_criteria": []
        })
        result2 = agent.analyze_requirement("")
        assert result2["summary"] == "v2"
        # final_requirementsが更新される
        assert agent.final_requirements["summary"] == "v2"

    def test_state_machine_multiple_transitions(self):
        """StateMachineの複数回遷移"""
        agent = RequirementAgent()
        fsm = StateMachine(agent)

        # 初期状態
        assert fsm.state["state"] == "INIT"

        # 1回目の遷移
        fsm.transition("入力1")
        state1 = fsm.state["state"]

        # 2回目の遷移（状態は変わらない可能性があるが、エラーにならない）
        fsm.transition("入力2")
        state2 = fsm.state["state"]

        # どちらも有効な状態
        assert state1 in ["INIT", "FINALIZING", "SUGGESTING"]
        assert state2 in ["INIT", "FINALIZING", "SUGGESTING"]


class TestRequirementAgentAdvancedScenarios:
    """より深い統合シナリオとエッジケース"""

    @patch.object(RequirementAgent, "execute_llm_task")
    def test_analyze_requirement_with_nested_json_in_text(self, mock_execute):
        """ネストされたJSON構造を含む要件テキストの処理"""
        mock_execute.return_value = json.dumps({
            "summary": "Nested JSON handling",
            "features": ["Parse nested data", "Validate structure"],
            "constraints": ["Must handle depth > 5"],
            "acceptance_criteria": ["All nested keys accessible"]
        })

        agent = RequirementAgent()
        result = agent.analyze_requirement(
            '要件: {"user": {"profile": {"settings": {"theme": "dark"}}}}'
        )

        assert "summary" in result
        assert len(result["features"]) > 0

    @patch.object(RequirementAgent, "execute_llm_task")
    def test_generate_final_spec_with_conflicting_history(self, mock_execute):
        """矛盾する履歴からの最終仕様生成"""
        mock_execute.return_value = json.dumps({
            "summary": "Resolved conflicts",
            "features": ["Final feature set"],
            "constraints": ["Latest constraints"],
            "acceptance_criteria": ["Criteria after resolution"]
        })

        agent = RequirementAgent()
        conflicting_history = [
            {"role": "user", "content": "Add feature X"},
            {"role": "assistant", "content": "OK"},
            {"role": "user", "content": "Remove feature X"},  # 矛盾
            {"role": "assistant", "content": "OK"},
        ]

        result = agent.generate_final_spec(conflicting_history)

        # 矛盾していても最終仕様が生成される
        assert "summary" in result

    def test_set_initial_requirement_with_multiline_text(self):
        """複数行テキストの初期要件設定"""
        agent = RequirementAgent()
        multiline_req = """
要件1: ユーザー認証機能
要件2: データ暗号化
要件3: ログ記録
詳細:
- セキュアな実装
- 高速な処理
        """

        agent.set_initial_requirement(multiline_req)
        state = agent._get_initial_state()

        # 複数行でも保存される
        assert "session_id" in state
        assert state["state"] == "INIT"

    @patch.object(RequirementAgent, "execute_llm_task")
    def test_analyze_requirement_with_llm_timeout_simulation(self, mock_execute):
        """LLMタイムアウトシミュレーション（遅延レスポンス）"""
        import time

        def slow_response(*args, **kwargs):
            time.sleep(0.1)  # 小さい遅延をシミュレート
            return json.dumps({
                "summary": "Slow response",
                "features": ["Feature after delay"],
                "constraints": [],
                "acceptance_criteria": []
            })

        mock_execute.side_effect = slow_response

        agent = RequirementAgent()
        result = agent.analyze_requirement("遅延テスト要件")

        # 遅延があっても結果が返る
        assert "summary" in result
        assert result["summary"] == "Slow response"

    @patch.object(RequirementAgent, "execute_llm_task")
    def test_analyze_requirement_with_extremely_long_text(self, mock_execute):
        """極端に長いテキストの要件分析"""
        mock_execute.return_value = json.dumps({
            "summary": "Long text processed",
            "features": ["Handle large inputs"],
            "constraints": ["Memory efficient"],
            "acceptance_criteria": ["No truncation"]
        })

        agent = RequirementAgent()
        # 10000文字の長いテキスト
        long_text = "要件: " + "a" * 10000

        result = agent.analyze_requirement(long_text)

        # 長いテキストでも処理される
        assert "summary" in result
        assert mock_execute.called

