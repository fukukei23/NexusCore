"""debugger応答からコードブロック抽出の堅牢化（nexuscore-bench Phase 0・診断確定に基づく修正）.

観測された事故: LLMが「説明文＋```python コード```」を返した際、応答全体が
fixed_code とみなされ説明文ごとファイルへ書き込まれ SyntaxError になる。
"""
from src.nexuscore.agents.debugger_agent import _extract_code_from_response


class TestExtractCode:
    def test_prose_then_fenced_code(self) -> None:
        resp = (
            "提供されたテストログに基づき、原因を分析しました。\n"
            "```python\n"
            "def is_prime(n: int) -> bool:\n"
            "    if n < 2:\n        return False\n"
            "    return all(n % i for i in range(2, int(n**0.5) + 1))\n"
            "```\n"
            "以上が修正です。\n"
        )
        code = _extract_code_from_response(resp)
        assert code is not None
        assert code.startswith("def is_prime")
        assert "提供された" not in code
        assert "以上が修正" not in code

    def test_plain_fenced_code(self) -> None:
        resp = "```python\ndef f():\n    return 1\n```"
        assert _extract_code_from_response(resp) == "def f():\n    return 1"

    def test_bare_code_no_fence(self) -> None:
        resp = "def f():\n    return 1\n"
        assert _extract_code_from_response(resp) == "def f():\n    return 1"

    def test_fence_without_language_tag(self) -> None:
        resp = "```\ndef f():\n    return 1\n```"
        assert _extract_code_from_response(resp) == "def f():\n    return 1"

    def test_empty(self) -> None:
        assert _extract_code_from_response("") is None
        assert _extract_code_from_response("説明だけです") == "説明だけです"
