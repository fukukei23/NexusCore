"""
ルート gradio_app.py の「出力ボタン」1回押下時の挙動を確認するテスト。

- 保存ボタン: save_to_sample_py() を1回呼ぶと期待メッセージを返すこと
- テストコード生成ボタン: generate_test_code() を1回呼ぶと pytest 風の文字列を返すこと
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, mock_open, patch

# gradio が未インストールの環境でもテスト可能にするため、import 前にモックを差し込む
if "gradio" not in sys.modules:
    _gr = MagicMock()
    sys.modules["gradio"] = _gr
    sys.modules["gr"] = _gr

# プロジェクトルートの gradio_app（pytest.ini の pythonpath=. により import 可能）
import gradio_app

# テスト用の簡単な Python 関数コード
SAMPLE_FUNC_CODE = """
def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    return True
"""


class TestSaveButtonOutput:
    """保存ボタン1回押下に相当するテスト"""

    def test_save_to_sample_py_returns_expected_message(self):
        """save_to_sample_py() を1回呼ぶと「✅ sample.py に保存されました。」を返すこと"""
        with patch("builtins.open", mock_open()) as m:
            result = gradio_app.save_to_sample_py(SAMPLE_FUNC_CODE)
        assert result == "✅ sample.py に保存されました。"
        m.assert_called_once()
        call_args = m.call_args
        assert call_args[0][0] == "sample.py"
        assert call_args[1].get("encoding") == "utf-8"
        # 書き込まれた内容は入力コードの strip（open の戻り値＝コンテキストマネージャの write）
        m.return_value.write.assert_called_once_with(SAMPLE_FUNC_CODE.strip())


class TestGenerateTestCodeButtonOutput:
    """テストコード生成ボタン1回押下に相当するテスト"""

    def test_generate_test_code_returns_pytest_style_code(self):
        """generate_test_code() を1回呼ぶと関数名・test_・assert を含む文字列を返すこと"""
        result = gradio_app.generate_test_code(SAMPLE_FUNC_CODE)
        assert "is_prime" in result
        assert "test_is_prime" in result
        assert "assert" in result
        assert "from sample import is_prime" in result
        assert "def test_" in result

    def test_generate_test_code_no_function_returns_warning(self):
        """関数がない入力では「⚠️ 関数が見つかりません」を含むメッセージを返すこと"""
        result = gradio_app.generate_test_code("print('hello')")
        assert "⚠️ 関数が見つかりません" in result
