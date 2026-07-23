"""utils.syntax_validator の単体テスト。

コード生成系 Agent の層1（AST構文検査）を担う純粋関数の検証。
"""
from nexuscore.utils.syntax_validator import validate_python_syntax


def test_valid_python_returns_ok_with_empty_err():
    ok, err = validate_python_syntax("x = 1\nprint(x)\n")
    assert ok is True
    assert err == ""


def test_invalid_python_returns_ng_with_message():
    ok, err = validate_python_syntax("def f(\n")  # SyntaxError
    assert ok is False
    assert "SyntaxError" in err or "ValueError" in err


def test_empty_string_returns_ng():
    ok, err = validate_python_syntax("")
    assert ok is False
    assert err  # 空でないメッセージ


def test_whitespace_only_returns_ng():
    ok, err = validate_python_syntax("   \n  \t ")
    assert ok is False
    assert err
