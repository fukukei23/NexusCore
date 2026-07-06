# 📁 ファイル名: diff_tools.py
# 📂 保存先: /src/utils/diff_tools.py

from difflib import unified_diff


def generate_diff_report(original: str, modified: str) -> str:
    """元テキストと修正テキストの unified diff 形式レポートを生成する。

    引数:
        original: 比較元のテキスト。
        modified: 比較先（修正後）のテキスト。

    戻り値:
        unified diff 形式の差分文字列。差分がない場合は空文字。
    """
    diff = unified_diff(
        original.splitlines(),
        modified.splitlines(),
        fromfile="Original",
        tofile="Modified",
        lineterm="",
    )
    return "\n".join(diff)


def score_code_improvement(original: str, modified: str) -> float:
    """行数変化率でコード改善スコアを算出する。

    正の値は行数増加（肥大化）、負の値は行数削減（コンパクト化）を示す。
    分母ゼロ回避のため元行数が 0 の場合は 1 とみなす。

    引数:
        original: 改善前のコードテキスト。
        modified: 改善後のコードテキスト。

    戻り値:
        (修正後行数 - 元行数) / max(元行数, 1) を小数第2位で丸めた値。
    """
    orig_lines = len(original.strip().splitlines())
    mod_lines = len(modified.strip().splitlines())
    return round((mod_lines - orig_lines) / max(orig_lines, 1), 2)
