"""権限ゲート ToolGate（Task 10 / spec §4）

硬いルール（spec §4）:
- 道具1回ごと個別判定（束ね承認不可）
- fail-closed: ポリシー不在・YAML破損・非dict構造のいずれも全拒否
  （雛形は FileNotFoundError のみcatchで、構文破損時に AttributeError クラッシュ
  = fail-open 相当になる穴があったため、破損判定をローダ結果の構造検証に統一）
- askタイムアウト=deny（タイムアウト制御はループ側責務・本クラスは
  ask_supported=False を deny に倒すのみ）

判定ログ（spec §4「全判定をrunイベントログに記録」）はループ側責務として
本クラスでは行わない（Phase 1 MVP・YAGNI）。
"""
from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from nexuscore.harness.config import load_policy


class Mode(StrEnum):
    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


@dataclass
class GateDecision:
    """1回のツール呼び出しに対する判定結果"""
    mode: Mode
    reason: str


class ToolGate:
    """ポリシーに基づきツール呼び出しを個別判定する（破損時は常に全拒否）"""

    def __init__(self, policy_path: Path):
        self.policy_path = Path(policy_path)
        self._policy: dict = {"tools": {}}
        try:
            data = load_policy(self.policy_path)
            # 構造検証: dict でなければ破損扱い（fail-closed）
            self._policy = data if isinstance(data, dict) else {"tools": {}}
            self._loaded = True
        except (FileNotFoundError, yaml.YAMLError, OSError):
            self._policy = {"tools": {}}  # fail-closed: 全拒否
            self._loaded = False

    def evaluate(
        self, *, tool: str, args: dict[str, Any], ask_supported: bool
    ) -> GateDecision:
        """道具1回ごとに個別判定する（束ね承認不可・fail-closed）"""
        if not self._loaded:
            return GateDecision(Mode.DENY, "policy broken or missing (fail-closed)")
        conf = self._policy.get("tools", {}).get(tool, {})
        if not isinstance(conf, dict):
            conf = {}
        # deny_paths: 文字列引数のパスglob一致で default より先に拒否
        # （MVP: str値を全スキャン・ツールスキーマ由来のpath特定は後続タスク）
        for pat in conf.get("deny_paths", []) or []:
            for v in args.values():
                if isinstance(v, str) and fnmatch.fnmatch(v, pat):
                    return GateDecision(Mode.DENY, f"path matches deny pattern {pat!r}")
        # 既定動作: 未設定=deny（保守側）
        default = conf.get("default", "deny")
        if default == "allow":
            return GateDecision(Mode.ALLOW, "default allow")
        if default == "ask" and ask_supported:
            return GateDecision(Mode.ASK, "default ask")
        return GateDecision(
            Mode.DENY, f"default={default} ask_supported={ask_supported}"
        )
