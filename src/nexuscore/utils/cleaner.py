"""Jupyter/セル実行のトレースバックからエラーメッセージを抽出・整形するユーティリティ。"""

import os
import re

PYTHON_PREFIX = os.environ.get("CONDA_PREFIX", "/usr/local")

SITE_PKG_ERROR_PREFIX = f"File {PYTHON_PREFIX}/lib/python3.10/"


def get_error_header(traceback_str: str) -> str:
    """トレースバック文字列から 'Error:' を含む最初の行を返す。

    Args:
        traceback_str: トレースバック文字列。

    Returns:
        エラー行。見つからなければ空文字列。
    """
    lines = traceback_str.split("\n")
    for line in lines:
        if "Error:" in line:
            return line
    return ""  # Return None if no error message is found


def clean_error_msg(error_str: str = "") -> str:
    """セル実行エラーメッセージから ANSIエスケープ・サイトパッケージ経路を除去し整形する。

    Args:
        error_str: セル実行時に発生した生のエラー文字列。

    Returns:
        整形済みのエラーメッセージ。
    """
    filtered_error_msg = (
        error_str.__str__()
        .split("An error occurred while executing the following cell")[-1]
        .split("\n------------------\n")[-1]
    )
    raw_error_msg = "".join(filtered_error_msg)

    # Remove escape sequences for colored text
    ansi_escape = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
    error_msg = ansi_escape.sub("", raw_error_msg)

    error_str_out = ""
    error_msg_only_cell = error_msg.split(SITE_PKG_ERROR_PREFIX)

    error_str_out += f"{error_msg_only_cell[0]}\n"
    error_header = get_error_header(error_msg_only_cell[-1])
    if error_header not in error_str_out:
        error_str_out += get_error_header(error_msg_only_cell[-1])

    return error_str_out
