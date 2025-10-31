#!/usr/bin/env python
"""
loosen_requirements.py
  requirements.txt 内の「パッケージ==x.y.z」表記を
  「パッケージ>=x.y.z,<next_major」へ自動変換するツール
使い方:
  python loosen_requirements.py requirements.txt > requirements_soft.txt
"""

import re
import sys
import subprocess
from pathlib import Path
from typing import List

# -- packaging.version が無ければ自動インストール ------------------------
try:
    from packaging.version import Version
except ImportError:  # pragma: no cover
    subprocess.check_call([sys.executable, "-m", "pip", "install", "packaging>=23"])
    from packaging.version import Version  # type: ignore
# ---------------------------------------------------------------------------


def loosen_line(line: str) -> str:
    line = line.strip()
    # 空行・コメント行はそのまま返す
    if not line or line.startswith("#"):
        return line

    # 既に >= / < などが入っている行はそのまま
    if ">" in line or "<" in line:
        return line

    # "pkg==1.2.3" を分解
    if "==" not in line:
        return line
    pkg, ver_str = line.split("==", 1)

    # バージョンが PEP440 互換でない場合は触らない
    try:
        ver = Version(ver_str)
    except Exception:
        return line

    # 次のメジャーバージョンを計算
    next_major = ver.major + 1
    upper_bound = f"<{next_major}"

    # 結果を返す
    return f"{pkg}>={ver},<{next_major}"


def main(args: List[str]) -> None:
    if not args:
        print("Usage: python loosen_requirements.py requirements.txt > requirements_soft.txt", file=sys.stderr)
        sys.exit(1)

    in_path = Path(args[0])
    if not in_path.exists():
        print(f"File not found: {in_path}", file=sys.stderr)
        sys.exit(1)

    for line in in_path.read_text(encoding="utf-8").splitlines():
        print(loosen_line(line))


if __name__ == "__main__":
    main(sys.argv[1:])
