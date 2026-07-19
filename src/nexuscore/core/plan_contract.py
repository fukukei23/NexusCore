"""plan JSON の target_files 契約（検証・フォールバック）。

spec: docs/superpowers/specs/2026-07-17-twelve-agent-pipeline-design.md §3-1
- role は implementation / test / config の3値
- 欠落・不正時は main.py 1枚の劣化モードに縮退（WARN ログ必須）
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

VALID_ROLES = frozenset({"implementation", "test", "config"})
FALLBACK_TARGET = {"path": "main.py", "role": "implementation"}


def extract_target_files(
    plan: dict[str, Any] | None,
) -> tuple[list[dict[str, str]], bool]:
    """plan から target_files を検証付きで取り出す。

    Args:
        plan: plan JSON オブジェクト（None 可）。

    Returns:
        (target_files, degraded): degraded=True は劣化モード（フォールバック適用）。
    """
    raw = (plan or {}).get("target_files")
    if not isinstance(raw, list) or not raw:
        logger.warning(
            "[plan_contract] target_files が欠落。劣化モード（main.py 1枚）に縮退します"
        )
        return [dict(FALLBACK_TARGET)], True

    valid: list[dict[str, str]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        path = entry.get("path")
        role = entry.get("role")
        if not path or not isinstance(path, str) or role not in VALID_ROLES:
            continue
        # ".." は部分文字列で保守的に拒否（"a..b.py" の偽陽性は安全側に倒す）
        # "\\" と ":" は Windows 形式パス・ドライブレターの混入防止
        if path.startswith("/") or ".." in path or "\\" in path or ":" in path:
            logger.warning("[plan_contract] 不正パスを除外: %s", path)
            continue
        valid.append({"path": path, "role": role})

    if not any(e["role"] == "implementation" for e in valid):
        logger.warning(
            "[plan_contract] implementation ロールが無い。劣化モードに縮退します"
        )
        return [dict(FALLBACK_TARGET)], True

    return valid, False
