"""
CI Safe Lock ファイル整合性検証テスト

requirements-ci-safe.txt と requirements-ci-safe.lock の整合性を検証する。
lock ファイルに埋め込まれた SOURCE_SHA256 が、実際の txt ファイルの sha256 と一致することを確認する。
"""

import hashlib
import re
from pathlib import Path

# プロジェクトルートのパス
PROJECT_ROOT = Path(__file__).parent.parent.parent
TXT_PATH = PROJECT_ROOT / "requirements-ci-safe.txt"
LOCK_PATH = PROJECT_ROOT / "requirements-ci-safe.lock"


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
    with open(lock_path, encoding="utf-8") as f:
        # 先頭50行を読み込む（コメントブロックは先頭にある想定）
        lines = [f.readline() for _ in range(50)]
        content = "".join(lines)

    # SOURCE_SHA256: に続く値を抽出（空白を許容）
    pattern = r"SOURCE_SHA256\s*:\s*([a-fA-F0-9]{64})"
    match = re.search(pattern, content)
    if match:
        return match.group(1)
    return None


def test_ci_safe_lock_file_exists():
    """
    requirements-ci-safe.lock が存在することを確認
    """
    assert LOCK_PATH.exists(), f"requirements-ci-safe.lock not found: {LOCK_PATH}"


def test_ci_safe_lock_source_sha256_format():
    """
    lock ファイルの先頭に SOURCE_SHA256 が存在し、形式が正しいことを確認
    """
    assert LOCK_PATH.exists(), f"requirements-ci-safe.lock not found: {LOCK_PATH}"

    source_sha = extract_source_sha256_from_lock(LOCK_PATH)
    assert source_sha is not None, (
        "SOURCE_SHA256 not found in requirements-ci-safe.lock. "
        "Lock file must start with metadata comment block containing SOURCE_SHA256."
    )
    assert len(source_sha) == 64, f"SOURCE_SHA256 must be 64 hex characters, got {len(source_sha)}"
    assert re.match(
        r"^[a-fA-F0-9]{64}$", source_sha
    ), f"SOURCE_SHA256 must be hex string, got: {source_sha}"


def test_ci_safe_lock_source_sha256_matches_txt():
    """
    lock ファイル内の SOURCE_SHA256 が requirements-ci-safe.txt の sha256 と一致することを確認
    """
    assert TXT_PATH.exists(), f"requirements-ci-safe.txt not found: {TXT_PATH}"
    assert LOCK_PATH.exists(), f"requirements-ci-safe.lock not found: {LOCK_PATH}"

    # txt ファイルの sha256 を計算
    txt_sha = calculate_file_sha256(TXT_PATH)

    # lock ファイルから SOURCE_SHA256 を抽出
    lock_sha = extract_source_sha256_from_lock(LOCK_PATH)
    assert lock_sha is not None, "SOURCE_SHA256 not found in lock file"

    assert txt_sha == lock_sha, (
        "CI Safe lock/txt の整合性エラー: requirements-ci-safe.lock が古い（または不整合）です。\n\n"
        f"- requirements-ci-safe.txt sha256 : {txt_sha}\n"
        f"- requirements-ci-safe.lock SOURCE_SHA256 : {lock_sha}\n\n"
        "解除方法（1コマンド）:\n"
        "  python tools/update_ci_safe_lock.py\n\n"
        "影響範囲チェックリスト:\n"
        "- [ ] requirements-ci-safe.txt を変更した\n"
        "- [ ] tools/update_ci_safe_lock.py を実行した\n"
        "- [ ] requirements-ci-safe.lock が更新され、SOURCE_SHA256 が新しい値になった\n"
        "- [ ] CI Safe は lock のみをインストールする（txt は参照しない）運用である\n"
        "- [ ] 依存追加/削除の場合、tests/api と tests/governance が PASS することを確認した\n\n"
        "注記:\n"
        "- lock の手編集は禁止（piptools + 更新ツールで生成する）"
    )
