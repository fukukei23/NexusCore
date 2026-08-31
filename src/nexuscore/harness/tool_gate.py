"""権限ゲート ToolGate（Task 10 / spec §4）

硬いルール（spec §4）:
- 道具1回ごと個別判定（束ね承認不可）
- fail-closed: ポリシー不在・YAML破損・非dict構造のいずれも全拒否
  （雛形は FileNotFoundError のみcatchで、構文破損時に AttributeError クラッシュ
  = fail-open 相当になる穴があったため、破損判定をローダ結果の構造検証に統一）
- askタイムアウト=deny（タイムアウト制御はループ側責務・本クラスは
  ask_supported=False を deny に倒すのみ）
- deny_paths は default より優先（deny最強・default=allowでも該当パスは拒否）
  ※ deny_paths走査は引数のネスト(list/dict)内部の文字列まで再帰適用・
    マッチ前に os.path.normpath で正規化（../ トラバーサル対策・3機レビュー採用）

判定ログ（spec §4「全判定をrunイベントログに記録」）はループ側責務として
本クラスでは行わない（Phase 1 MVP・YAGNI）。
"""
from __future__ import annotations

import fnmatch
import os
from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from nexuscore.harness.config import load_policy


def _iter_arg_strings(value: Any) -> Iterator[str]:
    """args内の全文字列を再帰列挙する（ネストされたlist/dict内部も含む）"""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _iter_arg_strings(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from _iter_arg_strings(v)


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
        self._loaded = False
        try:
            if not self.policy_path.is_file():
                # FIFO等の特殊ファイル・不在は破損扱い（read_textの無限ブロック防止）
                raise FileNotFoundError(str(self.policy_path))
            data = load_policy(self.policy_path)
        except (
            FileNotFoundError,
            yaml.YAMLError,
            OSError,
            UnicodeDecodeError,
            ValueError,
        ):
            self._policy = {"tools": {}}  # fail-closed: 全拒否
            self._loaded = False
            return
        # toolsセクションの構造検証（tools: null / 非dict は破損扱い）
        tools = data.get("tools", {})
        self._loaded = isinstance(tools, dict)
        self._policy = data if self._loaded else {"tools": {}}

    def evaluate(
        self, *, tool: str, args: dict[str, Any], ask_supported: bool
    ) -> GateDecision:
        """道具1回ごとに個別判定する（束ね承認不可・fail-closed）"""
        if not self._loaded:
            return GateDecision(Mode.DENY, "policy broken or missing (fail-closed)")
        conf = self._policy.get("tools", {}).get(tool, {})
        if not isinstance(conf, dict):
            conf = {}
        # deny_paths: default より先に、引数内の全文字列（ネスト含む）を
        # 正規化のうえglobマッチし、1つでも一致したら拒否
        for pat in conf.get("deny_paths", []) or []:
            for v in _iter_arg_strings(args):
                if fnmatch.fnmatch(os.path.normpath(v), pat):
                    return GateDecision(
                        Mode.DENY, f"path {v!r} matches deny pattern {pat!r}"
                    )
        # 既定動作: 未設定=deny（保守側）
        default = conf.get("default", "deny")
        if default == "allow":
            return GateDecision(Mode.ALLOW, "default allow")
        if default == "ask" and ask_supported:
            return GateDecision(Mode.ASK, "default ask")
        if default == "ask":
            return GateDecision(
                Mode.DENY,
                f"ask required but channel unavailable (default={default})",
            )
        return GateDecision(Mode.DENY, f"default={default} is not allow/ask")
