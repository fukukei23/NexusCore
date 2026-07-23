"""Python 構文検証ユーティリティ（コード生成系 Agent の共通層1）。

ast.parse で SyntaxError を検出し、説明文等の非コード出力を早期に弾く。
ok=True のとき err=""（空文字）。

注意: None 入力は呼び出し側の責務で弾くこと（本関数は str のみ想定）。
"""
import ast


def validate_python_syntax(code: str) -> tuple[bool, str]:
    """Python コードの構文妥当性を検証する。

    Args:
        code: 検証対象の Python コード文字列。

    Returns:
        (True, ""): 構文OK。
        (False, "<msg>"): 構文NG（SyntaxError/ValueError/空文字）。

    Raises:
        TypeError: code が None 等 str でない場合（呼び出し側責務）。
        MemoryError / SystemExit / RecursionError: 握りつぶさず再送出。
    """
    if not code or not code.strip():
        return False, "ParseError: empty code"
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as e:
        return False, f"SyntaxError: {e}"
    except ValueError as e:
        # ast.parse が稀に ValueError を投げる（NUL文字等）
        return False, f"ValueError: {e}"
    # MemoryError / SystemExit / RecursionError 等は再送出（握りつぶさない）
