# modules/diff_viewer.py

import difflib

def generate_diff(old_code: str, new_code: str) -> str:
    diff = difflib.unified_diff(
        old_code.splitlines(),
        new_code.splitlines(),
        fromfile='Before',
        tofile='After',
        lineterm=''
    )
    return "\n".join(diff)
