#!/usr/bin/env python3
"""
CI Safe Lock ファイル更新ツール

requirements-ci-safe.txt から requirements-ci-safe.lock を生成し、
先頭にメタ情報（SOURCE_SHA256 など）を埋め込む。
"""

import hashlib
import re
import subprocess
import sys
from pathlib import Path

# プロジェクトルートのパス
PROJECT_ROOT = Path(__file__).parent.parent
TXT_PATH = PROJECT_ROOT / "requirements-ci-safe.txt"
LOCK_PATH = PROJECT_ROOT / "requirements-ci-safe.lock"

# メタ情報コメントブロックのテンプレート
METADATA_TEMPLATE = """# CI SAFE LOCK (generated)
# SOURCE_FILE: requirements-ci-safe.txt
# SOURCE_SHA256: {sha256}
# GENERATED_BY: pip-compile
# NOTE: do not edit by hand

"""


def calculate_file_sha256(file_path: Path) -> str:
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


def extract_source_sha256_from_lock(lock_path: Path) -> str | None:
    """
    lock ファイルの先頭コメントブロックから SOURCE_SHA256 を抽出する

    Args:
        lock_path: lock ファイルのパス

    Returns:
        SOURCE_SHA256 の値（16進数文字列）、見つからない場合は None
    """
    if not lock_path.exists():
        return None

    with open(lock_path, "r", encoding="utf-8") as f:
        # 先頭50行を読み込む（コメントブロックは先頭にある想定）
        lines = [f.readline() for _ in range(50)]
        content = "".join(lines)

    # SOURCE_SHA256: に続く値を抽出（空白を許容）
    pattern = r"SOURCE_SHA256\s*:\s*([a-fA-F0-9]{64})"
    match = re.search(pattern, content)
    if match:
        return match.group(1)
    return None


def generate_lock_file() -> None:
    """
    pip-compile を使用して lock ファイルを生成する
    """
    # python -m piptools compile を試す（pip-compile の代替）
    cmd = [
        sys.executable,
        "-m",
        "piptools",
        "compile",
        "--generate-hashes",
        "--output-file",
        str(LOCK_PATH),
        str(TXT_PATH),
    ]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=str(PROJECT_ROOT))
        if result.stderr:
            print(result.stderr, file=sys.stderr)
    except subprocess.CalledProcessError as e:
        print(f"Error: pip-compile failed with exit code {e.returncode}", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        sys.exit(2)
    except FileNotFoundError:
        print(
            "Error: piptools not found. Please install it with: pip install pip-tools",
            file=sys.stderr,
        )
        sys.exit(2)


def insert_metadata_into_lock(sha256: str) -> None:
    """
    lock ファイルの先頭にメタ情報コメントブロックを挿入/更新する

    Args:
        sha256: requirements-ci-safe.txt の sha256 値
    """
    if not LOCK_PATH.exists():
        print(f"Error: {LOCK_PATH} not found after generation", file=sys.stderr)
        sys.exit(2)

    # lock ファイルを読み込む
    with open(LOCK_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 既存のメタ情報コメントブロックを削除
    # メタ情報ブロックは先頭の # で始まる連続した行で、SOURCE_SHA256 または CI SAFE LOCK を含む
    new_lines = []
    skip_mode = False
    found_metadata = False

    for line in lines:
        # メタ情報ブロックの開始を検出（SOURCE_SHA256 または CI SAFE LOCK を含む行）
        if not found_metadata and re.search(r"SOURCE_SHA256|CI SAFE LOCK", line):
            skip_mode = True
            found_metadata = True
            continue
        # スキップモード中
        if skip_mode:
            # # で始まる行はスキップ
            if line.startswith("#"):
                continue
            # 空行もスキップ
            if line.strip() == "":
                continue
            # それ以外の行に到達したら終了
            skip_mode = False
        new_lines.append(line)

    # メタ情報を先頭に挿入
    metadata = METADATA_TEMPLATE.format(sha256=sha256)
    updated_content = metadata + "".join(new_lines)

    # lock ファイルに書き込む
    with open(LOCK_PATH, "w", encoding="utf-8") as f:
        f.write(updated_content)


def main() -> None:
    """
    メイン処理
    """
    # txt ファイルの存在確認
    if not TXT_PATH.exists():
        print(f"Error: {TXT_PATH} not found", file=sys.stderr)
        sys.exit(2)

    # 既存の lock ファイルから SOURCE_SHA256 を取得（変更前の値）
    old_sha = extract_source_sha256_from_lock(LOCK_PATH)

    # txt ファイルの sha256 を計算
    txt_sha = calculate_file_sha256(TXT_PATH)

    # lock ファイルを生成
    print(f"Generating {LOCK_PATH} from {TXT_PATH}...")
    generate_lock_file()

    # メタ情報を挿入/更新
    insert_metadata_into_lock(txt_sha)

    # 変更前後の値を表示
    if old_sha:
        print(f"SOURCE_SHA256 updated: {old_sha} -> {txt_sha}")
    else:
        print(f"SOURCE_SHA256 set: {txt_sha}")

    print(f"Lock file updated: {LOCK_PATH}")


if __name__ == "__main__":
    main()

