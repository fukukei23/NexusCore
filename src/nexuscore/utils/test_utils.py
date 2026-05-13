from __future__ import annotations

import ast
import locale
import re
import subprocess
import sys
from pathlib import Path


def project_path_to_module_path(project_root: Path, file_path: Path) -> str:
    """
    プロジェクトルートからの相対パスを Python モジュールパスに変換する。

    Args:
        project_root: プロジェクトのルートディレクトリ
        file_path: 対象ファイルのパス

    Returns:
        Python モジュールパス（例: "foo.bar"）

    Examples:
        >>> project_path_to_module_path(Path("/project"), Path("/project/src/foo/bar.py"))
        "src.foo.bar"
    """
    try:
        rel_path = file_path.relative_to(project_root)
        # .py 拡張子を除去
        module_path = str(rel_path.with_suffix(""))
        # パス区切り文字をドットに変換
        module_path = module_path.replace("/", ".").replace("\\", ".")
        return module_path
    except ValueError:
        # プロジェクト外のファイルはそのまま返す
        return str(file_path.stem)


def validate_test_code(test_code: str) -> tuple[bool, str | None, list[str]]:
    """
    生成されたテストコードを検証する。

    Args:
        test_code: 検証するテストコード

    Returns:
        (is_valid, error_message, warnings) のタプル
        - is_valid: 構文的に有効か
        - error_message: エラーメッセージ（エラーがある場合）
        - warnings: 警告メッセージのリスト
    """
    warnings: list[str] = []

    # 1. AST パースで構文チェック
    try:
        ast.parse(test_code)
    except SyntaxError as e:
        return False, f"Syntax error: {e}", warnings

    # 2. 危険な文字列のチェック
    dangerous_patterns = [
        (r"\bos\.system\s*\(", "os.system() calls are not allowed"),
        (r"\bsubprocess\.(run|call|Popen)\s*\(", "subprocess calls are not allowed"),
        (r'open\s*\([^,)]+,\s*["\']w', "File write operations are not allowed (use mock)"),
        (r'open\s*\([^,)]+,\s*["\']a', "File append operations are not allowed (use mock)"),
        (r"__import__\s*\(", "__import__() calls are not allowed"),
        (r"eval\s*\(", "eval() calls are not allowed"),
        (r"exec\s*\(", "exec() calls are not allowed"),
    ]

    for pattern, message in dangerous_patterns:
        if re.search(pattern, test_code):
            warnings.append(message)

    # 3. if __name__ == "__main__": のチェック
    if re.search(r'if\s+__name__\s*==\s*["\']__main__["\']', test_code):
        warnings.append('if __name__ == "__main__": should not be included in test files')

    # 4. pytest 関数名のチェック
    test_functions = re.findall(r"def\s+(test_\w+)", test_code)
    if not test_functions:
        warnings.append('No test functions found (functions should start with "test_")')

    # 5. import pytest のチェック
    if "import pytest" not in test_code and "from pytest import" not in test_code:
        warnings.append("pytest is not imported")

    return True, None, warnings


def extract_code_from_markdown(text: str) -> str:
    """
    Markdown コードブロックから Python コードを抽出する。

    Args:
        text: Markdown 形式のテキスト（コードブロックを含む可能性がある）

    Returns:
        抽出された Python コード
    """
    # ```python または ``` で囲まれたコードブロックを探す
    pattern = r"```(?:python)?\s*\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)

    if matches:
        # 最初のコードブロックを返す
        return matches[0].strip()

    # コードブロックが見つからない場合はそのまま返す
    return text.strip()


def create_fallback_test_file(file_path: Path, error_message: str) -> str:
    """
    エラー時のフォールバックテストファイルを生成する。

    Args:
        file_path: テストファイルのパス
        error_message: エラーメッセージ

    Returns:
        フォールバックテストコード
    """
    return f'''"""
Auto-generated test file (fallback due to generation error)

This test file was generated as a fallback because the test generation failed.
Original error: {error_message}
"""

import pytest


def test_auto_generated_test_scaffold_invalid():
    """
    Auto-generated test scaffold is invalid.

    This test intentionally fails to indicate that the test generation
    process encountered an error and could not produce valid test code.
    """
    pytest.fail(
        f"Auto-generated test scaffold is invalid. "
        f"Test generation failed with error: {error_message}"
    )
'''


def run_tests(project_path: str) -> tuple[bool, str]:
    """
    指定されたプロジェクトパスでpytestを実行し、成功したかどうかと、
    その出力結果を返します。

    Args:
        project_path: テストを実行するプロジェクトパス

    Returns:
        (成功したかどうか, 出力結果) のタプル
    """
    try:
        python_executable = sys.executable

        # OSが使用しているデフォルトの文字コードを取得
        preferred_encoding = locale.getpreferredencoding(False)

        result = subprocess.run(
            [python_executable, "-m", "pytest"],
            cwd=project_path,
            capture_output=True,
            text=True,
            encoding=preferred_encoding,
            errors="replace",
            check=False,
        )

        # UnicodeDecodeErrorで結果がNoneになる可能性を考慮し、安全に結合します。
        stdout = result.stdout if result.stdout is not None else ""
        stderr = result.stderr if result.stderr is not None else ""
        output = stdout + "\n" + stderr

        return result.returncode == 0, output

    except FileNotFoundError:
        return (
            False,
            "pytestコマンドが見つかりませんでした。仮想環境が有効で、pytestがインストールされているか確認してください。",
        )
    except Exception as e:
        return False, f"テスト実行中に予期せぬエラーが発生しました: {e}"
