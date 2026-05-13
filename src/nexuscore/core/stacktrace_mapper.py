from __future__ import annotations

import re

# 例: File "/app/src/foo/bar.py", line 123, in some_function
STACKTRACE_FILE_RE = re.compile(r'File "([^"]+)", line (\d+), in (.+)$')


def extract_candidate_files(error_log: str) -> list[str]:
    """
    Python スタックトレースから、登場順にファイルパスを抽出する。

    :param error_log: pytest やユニットテストの標準エラー出力など
    :return: スタックトレースに登場したファイルパスのリスト（重複は除外）
    """
    candidates: list[str] = []

    for line in error_log.splitlines():
        line = line.rstrip("\n")
        m = STACKTRACE_FILE_RE.search(line)
        if not m:
            continue

        path = m.group(1)
        if path not in candidates:
            candidates.append(path)

    return candidates
