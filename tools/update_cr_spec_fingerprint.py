#!/usr/bin/env python3
"""
cr_spec.py の fingerprint を更新するツール

cr_spec.py を読み、sha256 を計算し、CR_SPEC_FINGERPRINT.txt を更新する。
"""

import hashlib
import sys
from pathlib import Path

# プロジェクトルートのパス
PROJECT_ROOT = Path(__file__).parent.parent
CR_SPEC_PATH = PROJECT_ROOT / "src" / "nexuscore" / "governance" / "cr_spec.py"
FINGERPRINT_PATH = PROJECT_ROOT / "docs" / "governance" / "CR_SPEC_FINGERPRINT.txt"


def calculate_fingerprint(file_path: Path) -> str:
    """
    ファイルの sha256 ハッシュを計算する

    Args:
        file_path: ファイルのパス

    Returns:
        sha256 ハッシュ値（16進数文字列）
    """
    with open(file_path, "rb") as f:
        content = f.read()
    return hashlib.sha256(content).hexdigest()


def update_fingerprint() -> int:
    """
    cr_spec.py の fingerprint を更新する

    Returns:
        終了コード（0: 成功、1: 失敗）
    """
    if not CR_SPEC_PATH.exists():
        print(f"Error: cr_spec.py not found: {CR_SPEC_PATH}", file=sys.stderr)
        return 1

    # 現在の fingerprint を読み込む（存在しない場合は空文字列）
    old_fingerprint = ""
    if FINGERPRINT_PATH.exists():
        old_fingerprint = FINGERPRINT_PATH.read_text(encoding="utf-8").strip()

    # 新しい fingerprint を計算
    new_fingerprint = calculate_fingerprint(CR_SPEC_PATH)

    # fingerprint を更新
    FINGERPRINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    FINGERPRINT_PATH.write_text(new_fingerprint + "\n", encoding="utf-8")

    # 更新前後の値を出力
    if old_fingerprint:
        print(f"Fingerprint updated:")
        print(f"  Old: {old_fingerprint}")
        print(f"  New: {new_fingerprint}")
    else:
        print(f"Fingerprint created:")
        print(f"  {new_fingerprint}")

    return 0


def main():
    """CLI エントリーポイント"""
    exit_code = update_fingerprint()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

