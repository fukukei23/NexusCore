"""
============================================================================
Comprehensive Tests for task_classifier.py
============================================================================
高品質テストの原則:
- LLMクライアントをモック（外部依存なし）
- 実際の分類ロジックとプロンプト構築をテスト
- エッジケースとエラー条件をカバー
============================================================================
"""
import pytest
import json
from unittest.mock import Mock, MagicMock

from nexuscore.llm.task_classifier import (
    build_classify_prompt,
    TaskClassifier,
)


# ============================================================================
# Tests: build_classify_prompt
# ============================================================================


class TestBuildClassifyPrompt:
    def test_build_prompt_simple(self):
        """シンプルなプロンプト構築"""
        allowed_tasks = {
            "code_generation": "Generate code",
            "code_review": "Review code",
            "general": "General task"
        }

        classify_prompt, system_prompt = build_classify_prompt(
            "Write a function to sort numbers",
            allowed_tasks
        )

        # classify_promptに元のプロンプトが含まれる
        assert "Write a function to sort numbers" in classify_prompt
        assert "Classify this developer request:" in classify_prompt

        # system_promptにタスクタイプが含まれる
        assert "task_type" in system_prompt
        assert "code_generation" in system_prompt
        assert "code_review" in system_prompt
        assert "general" in system_prompt
        assert "You are a task classifier" in system_prompt

    def test_build_prompt_single_task_type(self):
        """単一のタスクタイプ"""
        allowed_tasks = {"general": "General task"}

        classify_prompt, system_prompt = build_classify_prompt(
            "Help me with something",
            allowed_tasks
        )

        assert "general" in system_prompt
        assert "Help me with something" in classify_prompt

    def test_build_prompt_many_task_types(self):
        """多数のタスクタイプ"""
        allowed_tasks = {
            f"task_{i}": f"Task {i}" for i in range(20)
        }

        classify_prompt, system_prompt = build_classify_prompt(
            "Complex request",
            allowed_tasks
        )

        # 全てのタスクタイプがカンマ区切りで含まれる
        for task_type in allowed_tasks.keys():
            assert task_type in system_prompt

    def test_build_prompt_empty_user_prompt(self):
        """空のユーザープロンプト"""
        allowed_tasks = {"general": "General"}

        classify_prompt, system_prompt = build_classify_prompt("", allowed_tasks)

        # 空のプロンプトでも構造は維持される
        assert "Classify this developer request:" in classify_prompt
        assert "\n\n" in classify_prompt

    def test_build_prompt_special_characters(self):
        """特殊文字を含むプロンプト"""
        allowed_tasks = {"code_generation": "Generate"}

        classify_prompt, system_prompt = build_classify_prompt(
            "Write code with {} and [] and <>\n\t\"quotes\"",
            allowed_tasks
        )

        # 特殊文字がそのまま保持される
        assert "{}" in classify_prompt
        assert "[]" in classify_prompt
        assert "<>" in classify_prompt
        assert '"quotes"' in classify_prompt

    def test_build_prompt_json_format_instruction(self):
        """JSON形式の指示が含まれる"""
        allowed_tasks = {"test": "Test"}

        classify_prompt, system_prompt = build_classify_prompt("prompt", allowed_tasks)

        assert "ONLY valid JSON" in system_prompt
        assert '{"task_type":"<one of [test]>"}' in system_prompt
        assert "If unsure, respond with general" in system_prompt

    def test_build_prompt_returns_tuple(self):
        """タプルを返す"""
        result = build_classify_prompt("test", {"general": "General"})

        assert isinstance(result, tuple)
        assert len(result) == 2
        classify_prompt, system_prompt = result
        assert isinstance(classify_prompt, str)
        assert isinstance(system_prompt, str)


# ============================================================================
# Tests: TaskClassifier initialization
# ============================================================================


class TestTaskClassifierInit:
    def test_init_with_client(self):
        """クライアントを指定して初期化"""
        mock_client = Mock()
        classifier = TaskClassifier(model_name="gpt-4", client=mock_client)

        assert classifier.model_name == "gpt-4"
        assert classifier.client is mock_client

    def test_init_with_different_models(self):
        """異なるモデル名で初期化"""
        models = ["gpt-4", "gpt-3.5-turbo", "claude-3", "custom-model"]

        for model in models:
            classifier = TaskClassifier(model_name=model, client=Mock())
            assert classifier.model_name == model

    def test_init_stores_client_reference(self):
        """クライアント参照を保持"""
        client1 = Mock()
        client2 = Mock()

        classifier1 = TaskClassifier("model1", client1)
        classifier2 = TaskClassifier("model2", client2)

        assert classifier1.client is client1
        assert classifier2.client is client2
        assert classifier1.client is not classifier2.client


# ============================================================================
# Tests: TaskClassifier.classify
# ============================================================================


class TestTaskClassifierClassify:
    def test_classify_code_generation(self):
        """コード生成タスクの分類"""
        mock_client = Mock()
        mock_client.execute.return_value = '{"task_type": "code_generation"}'

        classifier = TaskClassifier("gpt-4", mock_client)
        task_types = {
            "code_generation": "Generate code",
            "code_review": "Review code",
            "general": "General"
        }

        result = classifier.classify(
            "Write a function to calculate fibonacci",
            task_types
        )

        assert result == "code_generation"
        mock_client.execute.assert_called_once()

    def test_classify_code_review(self):
        """コードレビュータスクの分類"""
        mock_client = Mock()
        mock_client.execute.return_value = '{"task_type": "code_review"}'

        classifier = TaskClassifier("gpt-4", mock_client)
        task_types = {"code_review": "Review", "general": "General"}

        result = classifier.classify("Review this PR", task_types)

        assert result == "code_review"

    def test_classify_general_fallback(self):
        """generalタスクへのフォールバック"""
        mock_client = Mock()
        mock_client.execute.return_value = '{"task_type": "general"}'

        classifier = TaskClassifier("gpt-4", mock_client)
        task_types = {"general": "General"}

        result = classifier.classify("Help me", task_types)

        assert result == "general"

    def test_classify_missing_task_type(self):
        """task_typeが欠落している場合"""
        mock_client = Mock()
        mock_client.execute.return_value = '{}'

        classifier = TaskClassifier("gpt-4", mock_client)
        task_types = {"general": "General"}

        result = classifier.classify("prompt", task_types)

        # デフォルトで"general"が返される
        assert result == "general"

    def test_classify_normalizes_case(self):
        """大文字小文字を正規化"""
        mock_client = Mock()
        mock_client.execute.return_value = '{"task_type": "CODE_GENERATION"}'

        classifier = TaskClassifier("gpt-4", mock_client)
        task_types = {"code_generation": "Generate"}

        result = classifier.classify("prompt", task_types)

        # 小文字に変換される
        assert result == "code_generation"

    def test_classify_strips_whitespace(self):
        """空白をトリム"""
        mock_client = Mock()
        mock_client.execute.return_value = '{"task_type": "  code_review  "}'

        classifier = TaskClassifier("gpt-4", mock_client)
        task_types = {"code_review": "Review"}

        result = classifier.classify("prompt", task_types)

        # 空白がトリムされる
        assert result == "code_review"

    def test_classify_passes_correct_parameters_to_client(self):
        """クライアントに正しいパラメータを渡す"""
        mock_client = Mock()
        mock_client.execute.return_value = '{"task_type": "general"}'

        classifier = TaskClassifier("gpt-4", mock_client)
        task_types = {"general": "General"}

        classifier.classify("Test prompt", task_types)

        # execute()の呼び出しを確認
        call_args = mock_client.execute.call_args
        assert call_args is not None

        # 位置引数
        assert "Test prompt" in call_args[0][0]

        # キーワード引数
        assert call_args[1]["as_json"] is True
        assert call_args[1]["temperature"] == 0.0
        assert "You are a task classifier" in call_args[1]["system_prompt"]

    def test_classify_with_complex_json(self):
        """複雑なJSONレスポンス"""
        mock_client = Mock()
        # 追加フィールドがあっても動作する
        mock_client.execute.return_value = '''
        {
            "task_type": "code_generation",
            "confidence": 0.95,
            "reasoning": "User wants to generate code"
        }
        '''

        classifier = TaskClassifier("gpt-4", mock_client)
        task_types = {"code_generation": "Generate"}

        result = classifier.classify("prompt", task_types)

        assert result == "code_generation"

    def test_classify_multiple_calls(self):
        """複数回の分類呼び出し"""
        mock_client = Mock()
        mock_client.execute.side_effect = [
            '{"task_type": "code_generation"}',
            '{"task_type": "code_review"}',
            '{"task_type": "general"}'
        ]

        classifier = TaskClassifier("gpt-4", mock_client)
        task_types = {
            "code_generation": "Generate",
            "code_review": "Review",
            "general": "General"
        }

        result1 = classifier.classify("Write code", task_types)
        result2 = classifier.classify("Review code", task_types)
        result3 = classifier.classify("Help", task_types)

        assert result1 == "code_generation"
        assert result2 == "code_review"
        assert result3 == "general"
        assert mock_client.execute.call_count == 3


# ============================================================================
# Tests: Integration scenarios
# ============================================================================


class TestIntegrationScenarios:
    def test_full_classification_workflow(self):
        """完全な分類ワークフロー"""
        # 1. クライアントをモック
        mock_client = Mock()
        mock_client.execute.return_value = '{"task_type": "code_generation"}'

        # 2. 分類器を作成
        classifier = TaskClassifier("gpt-4", mock_client)

        # 3. タスクタイプマップを定義
        task_types = {
            "code_generation": "Generate new code",
            "code_review": "Review existing code",
            "documentation": "Write documentation",
            "testing": "Create tests",
            "general": "General programming task"
        }

        # 4. ユーザープロンプトを分類
        user_prompt = "Write a Python function to parse JSON"

        result = classifier.classify(user_prompt, task_types)

        # 5. 結果を検証
        assert result == "code_generation"

        # 6. クライアントが正しく呼ばれたか確認
        mock_client.execute.assert_called_once()
        call_kwargs = mock_client.execute.call_args[1]
        assert call_kwargs["temperature"] == 0.0
        assert call_kwargs["as_json"] is True

    def test_classifier_reuse(self):
        """同じ分類器を再利用"""
        mock_client = Mock()
        classifier = TaskClassifier("gpt-4", mock_client)

        task_types = {"general": "General"}

        # 異なるプロンプトで複数回使用
        prompts = [
            "Help with coding",
            "Explain this concept",
            "Debug this issue"
        ]

        for i, prompt in enumerate(prompts):
            mock_client.execute.return_value = '{"task_type": "general"}'
            result = classifier.classify(prompt, task_types)
            assert result == "general"

        assert mock_client.execute.call_count == len(prompts)


# ============================================================================
# Tests: Edge cases
# ============================================================================


class TestEdgeCases:
    def test_classify_with_empty_task_types(self):
        """空のタスクタイプマップ"""
        mock_client = Mock()
        mock_client.execute.return_value = '{"task_type": "general"}'

        classifier = TaskClassifier("gpt-4", mock_client)

        # 空の辞書でも動作する
        result = classifier.classify("prompt", {})
        assert result == "general"

    def test_classify_with_non_string_task_type(self):
        """数値のtask_type"""
        mock_client = Mock()
        mock_client.execute.return_value = '{"task_type": 123}'

        classifier = TaskClassifier("gpt-4", mock_client)
        task_types = {"general": "General"}

        result = classifier.classify("prompt", task_types)

        # str()で文字列に変換される
        assert result == "123"

    def test_classify_with_null_task_type(self):
        """nullのtask_type"""
        mock_client = Mock()
        mock_client.execute.return_value = '{"task_type": null}'

        classifier = TaskClassifier("gpt-4", mock_client)
        task_types = {"general": "General"}

        result = classifier.classify("prompt", task_types)

        # "none"に変換される
        assert result == "none"

    def test_classify_with_unicode_prompt(self):
        """Unicode文字を含むプロンプト"""
        mock_client = Mock()
        mock_client.execute.return_value = '{"task_type": "general"}'

        classifier = TaskClassifier("gpt-4", mock_client)
        task_types = {"general": "General"}

        result = classifier.classify("日本語のプロンプト 🚀", task_types)

        assert result == "general"
        # プロンプトがクライアントに渡される
        call_args = mock_client.execute.call_args[0][0]
        assert "日本語のプロンプト 🚀" in call_args

    def test_classify_with_very_long_prompt(self):
        """非常に長いプロンプト"""
        mock_client = Mock()
        mock_client.execute.return_value = '{"task_type": "general"}'

        classifier = TaskClassifier("gpt-4", mock_client)
        task_types = {"general": "General"}

        long_prompt = "x" * 10000
        result = classifier.classify(long_prompt, task_types)

        assert result == "general"

    def test_classify_with_malformed_json(self):
        """不正なJSON"""
        mock_client = Mock()
        mock_client.execute.return_value = "not json"

        classifier = TaskClassifier("gpt-4", mock_client)
        task_types = {"general": "General"}

        # JSONDecodeErrorが発生する
        with pytest.raises(json.JSONDecodeError):
            classifier.classify("prompt", task_types)

    def test_build_prompt_with_special_task_names(self):
        """特殊な文字を含むタスク名"""
        allowed_tasks = {
            "code-generation": "Generate",
            "code_review_v2": "Review",
            "general.task": "General"
        }

        classify_prompt, system_prompt = build_classify_prompt("test", allowed_tasks)

        # 特殊文字がそのまま保持される
        assert "code-generation" in system_prompt
        assert "code_review_v2" in system_prompt
        assert "general.task" in system_prompt

    def test_classify_case_sensitivity(self):
        """大文字小文字の違い"""
        mock_client = Mock()

        # 大文字で返される
        mock_client.execute.return_value = '{"task_type": "CODE_GENERATION"}'

        classifier = TaskClassifier("gpt-4", mock_client)
        task_types = {"code_generation": "Generate"}

        result = classifier.classify("prompt", task_types)

        # 小文字に正規化される
        assert result == "code_generation"
        assert result != "CODE_GENERATION"
