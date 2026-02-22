"""
CR ガバナンス定義（cr_spec.py）変更検知の強制ゲート

cr_spec.py（SSoT）が変更されたら必ず pytest を FAIL させる。
開発者が影響確認した上で、専用更新ツールを実行した場合のみ PASS する状態にする。
"""

import hashlib
from pathlib import Path

# プロジェクトルートのパス
PROJECT_ROOT = Path(__file__).parent.parent.parent
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


def test_cr_spec_fingerprint_matches():
    """
    cr_spec.py の fingerprint が CR_SPEC_FINGERPRINT.txt と一致することを検証

    cr_spec.py が変更された場合、このテストは FAIL する。
    解除するには、以下を実行すること：
    python tools/update_cr_spec_fingerprint.py
    """
    assert CR_SPEC_PATH.exists(), f"cr_spec.py not found: {CR_SPEC_PATH}"
    assert FINGERPRINT_PATH.exists(), f"Fingerprint file not found: {FINGERPRINT_PATH}"

    # 現在の cr_spec.py の fingerprint を計算
    current_fingerprint = calculate_fingerprint(CR_SPEC_PATH)

    # CR_SPEC_FINGERPRINT.txt から保存された fingerprint を読み込む
    stored_fingerprint = FINGERPRINT_PATH.read_text(encoding="utf-8").strip()

    assert current_fingerprint == stored_fingerprint, (
        f"cr_spec.py が変更されました。\n\n"
        f"現在の fingerprint: {current_fingerprint}\n"
        f"保存された fingerprint: {stored_fingerprint}\n\n"
        f"影響範囲チェックリスト:\n"
        f"  - scaffold（tools/scaffold_cr.py）が cr_spec を参照しているか確認\n"
        f"  - 品質ゲート（tests/api/test_*_quality_gate.py）が cr_spec を参照しているか確認\n"
        f"  - README 整合性（tests/api/test_readme_cr_*.py）が cr_spec を参照しているか確認\n"
        f"  - 既存の Completion Report が新しい定義に適合しているか確認\n\n"
        f"解除方法:\n"
        f"  python tools/update_cr_spec_fingerprint.py\n\n"
        f"注意: このツールを実行する前に、上記の影響範囲を確認してください。"
    )
