"""tool_policy.yaml ローダ（Task 10）

ローダは純粋に読むだけ（例外は握りつぶさない）。
fail-closed 判定は ToolGate 側で行う（責務分離）。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_policy(path: Path) -> dict[str, Any]:
    """tool_policy.yaml を読み込み dict で返す（壊れていれば例外を上位へ）"""
    data = yaml.safe_load(path.read_text())
    return data if isinstance(data, dict) else {"tools": {}}
