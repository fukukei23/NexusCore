from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class SelfHealingConfig:
    # Self-Healing を走らせる PR のラベル名
    label: str = "self-healing"

    # 対象とする PR の base ブランチ (None or [] の場合 → 全ブランチ許可)
    allowed_target_branches: list[str] | None = None

    # テスト実行コマンド (例: "pytest -q", "npm test" など)
    test_command: str = "pytest -q"

    # テストファイル (tests/ や test_*.py) を修正してもよいか
    # false の場合、テストファイルを触る patch はブロックされる
    allow_test_modification: bool = False

    # ファイルの削除行 (unified diff の '-') を含む patch を許可するか
    allow_deletions: bool = False

    @classmethod
    def load(cls, project_root: str) -> SelfHealingConfig:
        """
        project_root/.nexus/self_healing.config.json を読み込み、
        見つからなければデフォルト設定を返す。
        """
        root = Path(project_root)
        path = root / ".nexus" / "self_healing.config.json"

        if not path.exists():
            return cls()

        try:
            data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            # 壊れている場合は安全側デフォルト
            return cls()

        def _get_bool(name: str, default: bool) -> bool:
            v = data.get(name, default)
            if isinstance(v, bool):
                return v
            if isinstance(v, str):
                v_lower = v.lower()
                if v_lower in ("true", "1", "yes", "y"):
                    return True
                if v_lower in ("false", "0", "no", "n"):
                    return False
            return default

        label = data.get("label", cls.label)
        allowed_target_branches = data.get("allowed_target_branches")
        if isinstance(allowed_target_branches, list):
            allowed_target_branches = [str(b) for b in allowed_target_branches]
        else:
            allowed_target_branches = None

        test_command = data.get("test_command", cls.test_command)

        allow_test_modification = _get_bool("allow_test_modification", cls.allow_test_modification)
        allow_deletions = _get_bool("allow_deletions", cls.allow_deletions)

        return cls(
            label=str(label),
            allowed_target_branches=allowed_target_branches,
            test_command=str(test_command),
            allow_test_modification=allow_test_modification,
            allow_deletions=allow_deletions,
        )
