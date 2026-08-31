"""provider単位のcapability table（Task 8 / spec §10）

更新契機3系統:
1. Phase 0バルク書込: update_many()
2. Mixin初期化時: set()
3. 明示的refresh: set()/update_many()（再計測結果の上書き）

plan雛形からの変更点: update_many()追加・utcnow()非推奨のためnow(timezone.utc)。
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

DEFAULT_PATH = Path(
    os.getenv("NEXUSCORE_CAPABILITY_PATH", "artifacts/harness/capability.json")
)

SCHEMA_VERSION = 1


class CapabilityTable:
    """tool_calling対応可否をJSON永続化するtable（更新APIは set / update_many）"""
    def __init__(self, path: Path = DEFAULT_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, dict] = {}
        if self.path.exists():
            self._data = json.loads(self.path.read_text())

    def set(self, provider_id: str, *, supports_tool_calling: bool) -> None:
        """1件記録（Mixin初期化時 / 明示的refresh系統）"""
        self._data[provider_id] = {
            "supports_tool_calling": supports_tool_calling,
            "last_verified_at": dt.datetime.now(dt.UTC).isoformat(),
            "schema_version": SCHEMA_VERSION,
        }
        self._flush()

    def update_many(self, entries: dict[str, bool]) -> None:
        """複数providerを一括記録（Phase 0バルク書込系統・既存は上書き）"""
        for provider_id, ok in entries.items():
            self._data[provider_id] = {
                "supports_tool_calling": ok,
                "last_verified_at": dt.datetime.now(dt.UTC).isoformat(),
                "schema_version": SCHEMA_VERSION,
            }
        self._flush()

    def supports_tool_calling(self, provider_id: str) -> bool | None:
        """計測済みならbool・未計測ならNone（Falseと区別・spec §10）"""
        rec = self._data.get(provider_id)
        return rec["supports_tool_calling"] if rec else None

    def _flush(self) -> None:
        """原子的書き込み（temp+rename）"""
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(self._data, indent=2, ensure_ascii=False))
        os.replace(tmp, self.path)
