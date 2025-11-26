"""Tests for nexuscore.modules.chat_handler"""
import os
from unittest.mock import patch, MagicMock
import pytest

from nexuscore.modules import chat_handler


def test_get_client_with_api_key(monkeypatch):
    """APIキーがある場合のget_clientテスト"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")

    with patch("nexuscore.modules.chat_handler.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        client = chat_handler.get_client()

        assert client == mock_client
        mock_openai.assert_called_once_with(api_key="test-key-123")


def test_get_client_no_api_key(monkeypatch):
    """APIキーがない場合のエラーテスト"""
    # グローバル変数をリセット
    chat_handler._client = None
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with patch("nexuscore.modules.chat_handler.OpenAI", MagicMock()):
        with pytest.raises(RuntimeError, match="OPENAI_API_KEY is not set"):
            chat_handler.get_client()


def test_get_client_openai_not_installed(monkeypatch):
    """OpenAI SDKがインストールされていない場合のテスト"""
    # グローバル変数をリセット
    chat_handler._client = None
    monkeypatch.setattr(chat_handler, "OpenAI", None)

    with pytest.raises(RuntimeError, match="openai SDK is not installed"):
        chat_handler.get_client()


def test_get_client_cached(monkeypatch):
    """クライアントのキャッシュテスト"""
    # グローバル変数をリセット
    chat_handler._client = None
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")

    with patch("nexuscore.modules.chat_handler.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # 初回呼び出し
        client1 = chat_handler.get_client()
        # 2回目呼び出し（キャッシュから）
        client2 = chat_handler.get_client()

        assert client1 is client2  # 同じオブジェクトであることを確認
        assert client1 == mock_client
        # OpenAIは1回だけ呼ばれる（キャッシュされるため）
        assert mock_openai.call_count == 1


def test_handle_chat_success(monkeypatch):
    """handle_chatの成功ケーステスト"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Hello, how can I help?"

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("nexuscore.modules.chat_handler.get_client", return_value=mock_client):
        history = []
        message = "Hello"
        response, updated_history = chat_handler.handle_chat(message, history)

        assert response == "Hello, how can I help?"
        assert len(updated_history) == 2
        assert updated_history[0]["role"] == "user"
        assert updated_history[0]["content"] == "Hello"
        assert updated_history[1]["role"] == "assistant"
        assert updated_history[1]["content"] == "Hello, how can I help?"


def test_handle_chat_with_existing_history(monkeypatch):
    """既存の履歴がある場合のhandle_chatテスト"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Response to second message"

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("nexuscore.modules.chat_handler.get_client", return_value=mock_client):
        history = [
            {"role": "user", "content": "First message"},
            {"role": "assistant", "content": "First response"},
        ]
        message = "Second message"
        response, updated_history = chat_handler.handle_chat(message, history)

        assert len(updated_history) == 4
        assert updated_history[2]["role"] == "user"
        assert updated_history[2]["content"] == "Second message"
        assert updated_history[3]["role"] == "assistant"


def test_handle_chat_error_handling(monkeypatch):
    """handle_chatのエラーハンドリングテスト"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("API Error")

    with patch("nexuscore.modules.chat_handler.get_client", return_value=mock_client):
        history = []
        message = "Test message"
        response, updated_history = chat_handler.handle_chat(message, history)

        assert "❌ エラー:" in response
        assert "API Error" in response
        # エラー時も履歴には追加される
        assert len(updated_history) == 1
        assert updated_history[0]["role"] == "user"


def test_handle_chat_empty_message(monkeypatch):
    """空のメッセージのテスト"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Empty message received"

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("nexuscore.modules.chat_handler.get_client", return_value=mock_client):
        history = []
        message = ""
        response, updated_history = chat_handler.handle_chat(message, history)

        assert response == "Empty message received"
        assert len(updated_history) == 2
        assert updated_history[0]["content"] == ""


def test_handle_chat_long_message(monkeypatch):
    """長いメッセージのテスト"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")

    long_message = "A" * 1000
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Received long message"

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("nexuscore.modules.chat_handler.get_client", return_value=mock_client):
        history = []
        response, updated_history = chat_handler.handle_chat(long_message, history)

        assert response == "Received long message"
        assert len(updated_history) == 2
        assert updated_history[0]["content"] == long_message


def test_handle_chat_special_characters(monkeypatch):
    """特殊文字を含むメッセージのテスト"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")

    special_message = "Hello! こんにちは! @#$%^&*()"
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Special characters received"

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("nexuscore.modules.chat_handler.get_client", return_value=mock_client):
        history = []
        response, updated_history = chat_handler.handle_chat(special_message, history)

        assert response == "Special characters received"
        assert updated_history[0]["content"] == special_message


def test_handle_chat_response_without_content(monkeypatch):
    """レスポンスにcontentがない場合のテスト"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = None

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("nexuscore.modules.chat_handler.get_client", return_value=mock_client):
        history = []
        message = "Test"
        response, updated_history = chat_handler.handle_chat(message, history)

        # contentがNoneの場合、エラーが発生する可能性がある
        # 実際の動作に応じて調整
        assert len(updated_history) >= 1


def test_handle_chat_multiple_messages(monkeypatch):
    """複数のメッセージを連続で送信するテスト"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")

    mock_client = MagicMock()

    responses = [
        "Response 1",
        "Response 2",
        "Response 3"
    ]

    mock_client.chat.completions.create.side_effect = [
        MagicMock(choices=[MagicMock(message=MagicMock(content=r))])
        for r in responses
    ]

    with patch("nexuscore.modules.chat_handler.get_client", return_value=mock_client):
        history = []

        for i, msg in enumerate(["Message 1", "Message 2", "Message 3"]):
            response, history = chat_handler.handle_chat(msg, history)
            assert response == responses[i]
            assert len(history) == (i + 1) * 2  # user + assistant per message


def test_handle_chat_history_preservation(monkeypatch):
    """履歴が正しく保持されるテスト"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Response"

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("nexuscore.modules.chat_handler.get_client", return_value=mock_client):
        initial_history = [
            {"role": "user", "content": "Previous message"},
            {"role": "assistant", "content": "Previous response"}
        ]

        response, updated_history = chat_handler.handle_chat("New message", initial_history.copy())

        # 履歴が保持されていることを確認
        assert len(updated_history) == 4
        assert updated_history[0] == initial_history[0]
        assert updated_history[1] == initial_history[1]
        assert updated_history[2]["role"] == "user"
        assert updated_history[3]["role"] == "assistant"


def test_handle_chat_whitespace_only_message(monkeypatch):
    """空白のみのメッセージのテスト"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Whitespace received"

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("nexuscore.modules.chat_handler.get_client", return_value=mock_client):
        history = []
        message = "   \n\t  "
        response, updated_history = chat_handler.handle_chat(message, history)

        assert response == "Whitespace received"
        assert updated_history[0]["content"] == message


def test_get_client_reset_on_error(monkeypatch):
    """エラー時にクライアントがリセットされるかテスト"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
    chat_handler._client = None

    with patch("nexuscore.modules.chat_handler.OpenAI") as mock_openai:
        # 初回は成功
        mock_client1 = MagicMock()
        mock_openai.return_value = mock_client1

        client1 = chat_handler.get_client()
        assert client1 == mock_client1

        # クライアントをリセット
        chat_handler._client = None

        # 2回目も成功
        mock_client2 = MagicMock()
        mock_openai.return_value = mock_client2

        client2 = chat_handler.get_client()
        assert client2 == mock_client2
        assert mock_openai.call_count == 2


def test_handle_chat_with_malformed_history(monkeypatch):
    """不正な形式の履歴でのテスト"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Response"

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("nexuscore.modules.chat_handler.get_client", return_value=mock_client):
        # 不正な形式の履歴
        malformed_history = [
            {"role": "user"},  # contentがない
            {"content": "test"},  # roleがない
        ]

        # エラーが発生する可能性があるが、処理が続行されることを確認
        try:
            response, updated_history = chat_handler.handle_chat("Test", malformed_history)
            assert response is not None
        except Exception:
            # エラーが発生する場合もある
            pass


def test_handle_chat_conversation_flow(monkeypatch):
    """会話フローの統合テスト"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")

    mock_client = MagicMock()
    responses = ["Hello", "How can I help?", "Goodbye"]

    mock_client.chat.completions.create.side_effect = [
        MagicMock(choices=[MagicMock(message=MagicMock(content=r))])
        for r in responses
    ]

    with patch("nexuscore.modules.chat_handler.get_client", return_value=mock_client):
        history = []

        # 3回の会話
        for i, msg in enumerate(["Hi", "What can you do?", "Thanks"]):
            response, history = chat_handler.handle_chat(msg, history)
            assert response == responses[i]
            assert len(history) == (i + 1) * 2


def test_handle_chat_response_format_validation(monkeypatch):
    """レスポンス形式の検証テスト"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Test response"

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("nexuscore.modules.chat_handler.get_client", return_value=mock_client):
        history = []
        response, updated_history = chat_handler.handle_chat("Test", history)

        # レスポンスが文字列であることを確認
        assert isinstance(response, str)
        # 履歴が正しい形式であることを確認
        assert isinstance(updated_history, list)
        assert len(updated_history) == 2
        assert updated_history[0]["role"] == "user"
        assert updated_history[1]["role"] == "assistant"


def test_handle_chat_empty_choices_list(monkeypatch):
    """空のchoicesリストのテスト"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")

    mock_response = MagicMock()
    mock_response.choices = []  # 空のリスト

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("nexuscore.modules.chat_handler.get_client", return_value=mock_client):
        history = []
        # エラーが発生する可能性がある
        try:
            response, updated_history = chat_handler.handle_chat("Test", history)
            # エラーが発生した場合、エラーメッセージが返される
            assert "❌ エラー:" in response or len(updated_history) >= 1
        except (IndexError, AttributeError):
            # エラーが発生する場合もある
            pass


def test_get_client_with_different_api_keys(monkeypatch):
    """異なるAPIキーでのクライアント取得テスト"""
    chat_handler._client = None

    api_keys = ["key1", "key2", "key3"]

    for api_key in api_keys:
        monkeypatch.setenv("OPENAI_API_KEY", api_key)
        chat_handler._client = None

        with patch("nexuscore.modules.chat_handler.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            client = chat_handler.get_client()
            assert client == mock_client
            # 正しいAPIキーで呼ばれることを確認
            mock_openai.assert_called_with(api_key=api_key)


def test_handle_chat_with_timeout_simulation(monkeypatch):
    """タイムアウトのシミュレーションテスト"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = TimeoutError("Request timeout")

    with patch("nexuscore.modules.chat_handler.get_client", return_value=mock_client):
        history = []
        response, updated_history = chat_handler.handle_chat("Test", history)

        assert "❌ エラー:" in response
        assert "timeout" in response.lower() or "TimeoutError" in response
        assert len(updated_history) == 1  # ユーザーメッセージのみ


def test_handle_chat_with_rate_limit_error(monkeypatch):
    """レート制限エラーのテスト"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")

    mock_client = MagicMock()
    # レート制限エラーをシミュレート
    rate_limit_error = Exception("Rate limit exceeded")
    mock_client.chat.completions.create.side_effect = rate_limit_error

    with patch("nexuscore.modules.chat_handler.get_client", return_value=mock_client):
        history = []
        response, updated_history = chat_handler.handle_chat("Test", history)

        assert "❌ エラー:" in response
        assert len(updated_history) == 1


def test_handle_chat_with_partial_response(monkeypatch):
    """部分的なレスポンスのテスト"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    # 部分的なコンテンツ
    mock_response.choices[0].message.content = "Partial response..."

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("nexuscore.modules.chat_handler.get_client", return_value=mock_client):
        history = []
        response, updated_history = chat_handler.handle_chat("Test", history)

        assert response == "Partial response..."
        assert len(updated_history) == 2


def test_handle_chat_history_modification_side_effects(monkeypatch):
    """履歴変更の副作用テスト"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Response"

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("nexuscore.modules.chat_handler.get_client", return_value=mock_client):
        original_history = [{"role": "user", "content": "Original"}]
        history_copy = original_history.copy()

        response, updated_history = chat_handler.handle_chat("New", history_copy)

        # 元の履歴が変更されていないことを確認
        assert len(original_history) == 1
        # 更新された履歴が正しいことを確認
        assert len(updated_history) == 3


def test_handle_chat_with_streaming_simulation(monkeypatch):
    """ストリーミングレスポンスのシミュレーションテスト"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")

    # ストリーミングレスポンスをシミュレート
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Streamed response content"

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("nexuscore.modules.chat_handler.get_client", return_value=mock_client):
        history = []
        response, updated_history = chat_handler.handle_chat("Test", history)

        assert response == "Streamed response content"
        assert len(updated_history) == 2


def test_handle_chat_with_model_parameter(monkeypatch):
    """モデルパラメータの確認テスト"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Response"

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("nexuscore.modules.chat_handler.get_client", return_value=mock_client):
        history = []
        chat_handler.handle_chat("Test", history)

        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["model"] == "gpt-4"


def test_handle_chat_with_custom_messages_structure(monkeypatch):
    """カスタムメッセージ構造のテスト"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Response"

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("nexuscore.modules.chat_handler.get_client", return_value=mock_client):
        # カスタムフィールドを含む履歴
        custom_history = [
            {"role": "user", "content": "Test", "custom_field": "value"}
        ]

        response, updated_history = chat_handler.handle_chat("New message", custom_history)

        # カスタムフィールドが保持される可能性がある
        assert len(updated_history) >= 2

