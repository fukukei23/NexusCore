"""CapabilityTable 単体テスト（Task 8 / plan §Task 8）

plan雛形をベースに、spec §10 の契約「更新契機3系統（Phase 0バルク書込 /
Mixin初期化時 / 明示的refresh）」を満たす API を検証する。

plan雛形からの変更点（実装時判断）:
- 雛形に無い update_many()（Phase 0バルク書込系統）を検証対象に追加
  （雛形の set() 1件ずつflushは3系統の1つしか担えないため）
- utcnow() は Python 3.12 で非推奨のため last_verified_at は
  tz-aware ISO 形式で検証（"Z" サフィックス固定はしない）
"""
from __future__ import annotations

import json
from datetime import datetime

from nexuscore.harness.capability import SCHEMA_VERSION, CapabilityTable


def test_set_persists_schema_fields(tmp_path):
    """set() で spec §10 のスキーマ4項目が永続化されること"""
    f = tmp_path / "cap.json"
    t = CapabilityTable(path=f)
    t.set("openai", supports_tool_calling=True)
    t.set("glm", supports_tool_calling=False)

    data = json.loads(f.read_text())
    assert data["openai"]["supports_tool_calling"] is True
    assert data["glm"]["supports_tool_calling"] is False
    assert data["openai"]["schema_version"] == SCHEMA_VERSION
    assert data["openai"]["last_verified_at"]


def test_last_verified_at_is_tz_aware_iso(tmp_path):
    """last_verified_at は tz-aware ISO 形式（utcnow 非推奨回避・parse検証）"""
    f = tmp_path / "cap.json"
    CapabilityTable(path=f).set("openai", supports_tool_calling=True)
    data = json.loads(f.read_text())
    parsed = datetime.fromisoformat(data["openai"]["last_verified_at"])
    assert parsed.tzinfo is not None  # naive時刻（utcnow）でないこと


def test_reload_keeps_previous_records(tmp_path):
    """永続化済みファイルから再構築すると既存レコードが読めること"""
    f = tmp_path / "cap.json"
    CapabilityTable(path=f).set("openai", supports_tool_calling=True)

    t2 = CapabilityTable(path=f)
    assert t2.supports_tool_calling("openai") is True


def test_unknown_provider_returns_none(tmp_path):
    """未計測 provider は None（False と区別する・spec §10）"""
    t = CapabilityTable(path=tmp_path / "cap.json")
    assert t.supports_tool_calling("no-such-provider") is None


def test_update_many_bulk_write(tmp_path):
    """Phase 0バルク書込系統: 複数providerを一括記録できること"""
    f = tmp_path / "cap.json"
    t = CapabilityTable(path=f)
    t.update_many({"openai": True, "glm": False, "minimax": True})

    data = json.loads(f.read_text())
    assert data["openai"]["supports_tool_calling"] is True
    assert data["glm"]["supports_tool_calling"] is False
    assert data["minimax"]["supports_tool_calling"] is True
    for rec in data.values():
        assert rec["schema_version"] == SCHEMA_VERSION
        assert rec["last_verified_at"]


def test_update_many_overwrites_existing(tmp_path):
    """バルク書込は既存レコードを上書きする（refresh系統と同一経路）"""
    f = tmp_path / "cap.json"
    t = CapabilityTable(path=f)
    t.set("openai", supports_tool_calling=False)
    t.update_many({"openai": True})
    assert t.supports_tool_calling("openai") is True


def test_no_tmp_file_left_after_write(tmp_path):
    """原子的書き込み（temp+rename）後、.tmp ファイルが残らないこと"""
    f = tmp_path / "cap.json"
    CapabilityTable(path=f).set("openai", supports_tool_calling=True)
    assert not (tmp_path / "cap.json.tmp").exists()
