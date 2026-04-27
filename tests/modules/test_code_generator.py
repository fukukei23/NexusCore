"""Tests for nexuscore.modules.code_generator — MiniMax HTTP backend"""

import pytest
import requests
from unittest.mock import patch, MagicMock

from nexuscore.modules.code_generator import generate_code_from_text, _call_minimax


class TestCallMinimax:
    """_call_minimax 関数のテスト"""

    @patch("nexuscore.modules.code_generator.requests.post")
    @patch.dict(
        "os.environ",
        {
            "MINIMAX_API_KEY": "test-api-key",
            "MINIMAX_API_BASE": "https://mock.api/v1",
            "MINIMAX_MODEL": "MockModel-V1",
        },
    )
    def test_call_minimax_success(self, mock_post):
        """[正常系] API呼び出しが成功し、レスポンスのcontentが返る"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "```python\nprint('hello')\n```"}}]
        }
        mock_post.return_value = mock_response

        messages = [{"role": "user", "content": "Test prompt"}]
        result = _call_minimax(messages, temperature=0.5)

        assert result == "```python\nprint('hello')\n```"
        mock_post.assert_called_once_with(
            "https://mock.api/v1/chat/completions",
            headers={
                "Authorization": "Bearer test-api-key",
                "Content-Type": "application/json",
            },
            json={
                "model": "MockModel-V1",
                "messages": messages,
                "temperature": 0.5,
            },
            timeout=120,
        )

    @patch.dict("os.environ", {}, clear=True)
    def test_call_minimax_no_api_key(self):
        """[異常系] MINIMAX_API_KEY未設定時にRuntimeError"""
        messages = [{"role": "user", "content": "Test prompt"}]
        with pytest.raises(RuntimeError, match="MINIMAX_API_KEY is not set"):
            _call_minimax(messages)

    @patch("nexuscore.modules.code_generator.requests.post")
    @patch.dict("os.environ", {"MINIMAX_API_KEY": "test-api-key"})
    def test_call_minimax_http_error(self, mock_post):
        """[異常系] HTTPエラー時にraise_for_statusが例外を送出"""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_post.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError):
            _call_minimax([{"role": "user", "content": "test"}])


class TestGenerateCodeFromText:
    """generate_code_from_text 関数のテスト"""

    @patch("nexuscore.modules.code_generator._call_minimax")
    def test_success_returns_code(self, mock_call):
        """[正常系] LLMからの文字列がそのまま返る"""
        expected = "```python\ndef hello():\n    return 'world'\n```"
        mock_call.return_value = expected

        result = generate_code_from_text("Hello Worldを出力する関数")

        assert result == expected
        mock_call.assert_called_once()

    @patch("nexuscore.modules.code_generator._call_minimax")
    def test_prompt_includes_user_input(self, mock_call):
        """[正常系] プロンプトにユーザー入力が含まれる"""
        mock_call.return_value = "```python\npass\n```"
        user_input = "フィボナッチ数列を計算する関数"

        generate_code_from_text(user_input)

        messages = mock_call.call_args[0][0]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert user_input in messages[0]["content"]

    @patch("nexuscore.modules.code_generator._call_minimax")
    def test_temperature_is_02(self, mock_call):
        """[正常系] temperature=0.2が渡される"""
        mock_call.return_value = "```python\npass\n```"

        generate_code_from_text("テスト")

        _, kwargs = mock_call.call_args
        assert kwargs.get("temperature") == 0.2

    @patch("nexuscore.modules.code_generator._call_minimax")
    def test_error_returns_minimax_prefix(self, mock_call):
        """[エラー] RuntimeError時にMiniMaxエラーメッセージが返る"""
        mock_call.side_effect = RuntimeError("MINIMAX_API_KEY is not set")

        result = generate_code_from_text("テスト")

        assert "⚠️ MiniMax code generation failed:" in result

    @patch("nexuscore.modules.code_generator._call_minimax")
    def test_error_http_returns_minimax_prefix(self, mock_call):
        """[エラー] HTTPエラー時にMiniMaxエラーメッセージが返る"""
        mock_call.side_effect = requests.exceptions.HTTPError("500 Server Error")

        result = generate_code_from_text("テスト")

        assert "⚠️ MiniMax code generation failed:" in result
        assert "500 Server Error" in result

    @patch("nexuscore.modules.code_generator._call_minimax")
    def test_empty_input_still_calls(self, mock_call):
        """[境界] 空文字でも呼び出しは行われる"""
        mock_call.return_value = "```python\npass\n```"

        result = generate_code_from_text("")
        assert result is not None
        mock_call.assert_called_once()

    @patch("nexuscore.modules.code_generator._call_minimax")
    def test_code_block_with_explanation(self, mock_call):
        """[正常系] コードブロック + 説明文が含まれるレスポンス"""
        mock_call.return_value = "Here is the code:\n```python\ndef hello():\n    return True\n```\nDone."

        result = generate_code_from_text("Create example")
        assert "def hello()" in result

    @patch("nexuscore.modules.code_generator._call_minimax")
    def test_response_without_code_block(self, mock_call):
        """[正常系] コードブロックなしの生コードレスポンス"""
        mock_call.return_value = "def hello():\n    print('world')"

        result = generate_code_from_text("Hello world")
        assert "def hello()" in result

    @patch("nexuscore.modules.code_generator._call_minimax")
    def test_multiple_requests_sequential(self, mock_call):
        """[正常系] 連続リクエストで異なる結果が返る"""
        mock_call.side_effect = [
            "```python\ndef f1(): pass\n```",
            "```python\ndef f2(): pass\n```",
        ]

        r1 = generate_code_from_text("Create f1")
        r2 = generate_code_from_text("Create f2")

        assert "f1" in r1
        assert "f2" in r2

    @patch("nexuscore.modules.code_generator._call_minimax")
    def test_error_recovery(self, mock_call):
        """[正常系] エラー後も次の呼び出しで成功"""
        mock_call.side_effect = [
            Exception("Network error"),
            "```python\npass\n```",
        ]

        r1 = generate_code_from_text("Test 1")
        assert "⚠️ MiniMax code generation failed:" in r1

        r2 = generate_code_from_text("Test 2")
        assert "pass" in r2

    @patch("nexuscore.modules.code_generator._call_minimax")
    def test_unicode_in_response(self, mock_call):
        """[正常系] Unicode文字を含むレスポンス"""
        mock_call.return_value = "```python\ndef 関数名():\n    return '🎉'\n```"

        result = generate_code_from_text("Create Unicode function")
        assert "関数名" in result

    @patch("nexuscore.modules.code_generator._call_minimax")
    def test_long_response(self, mock_call):
        """[正常系] 非常に長いレスポンス"""
        long_code = "def func():\n    " + "\n    ".join([f"x{i} = {i}" for i in range(500)])
        mock_call.return_value = f"```python\n{long_code}\n```"

        result = generate_code_from_text("Create long function")
        assert len(result) > 1000
        assert "def func()" in result
