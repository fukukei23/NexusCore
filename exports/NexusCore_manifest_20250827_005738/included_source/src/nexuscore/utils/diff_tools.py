# 📁 ファイル名: diff_tools.py
# 📂 保存先: /src/utils/diff_tools.py

from difflib import unified_diff

def generate_diff_report(original: str, modified: str) -> str:
    diff = unified_diff(
        original.splitlines(),
        modified.splitlines(),
        fromfile="Original",
        tofile="Modified",
        lineterm=""
    )
    return "\n".join(diff)

def score_code_improvement(original: str, modified: str) -> float:
    orig_lines = len(original.strip().splitlines())
    mod_lines = len(modified.strip().splitlines())
    return round((mod_lines - orig_lines) / max(orig_lines, 1), 2)
