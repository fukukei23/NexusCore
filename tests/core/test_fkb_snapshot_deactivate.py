"""FKB汚染スパイラル対策: スナップショットとknowledge_id論理削除（nexuscore-bench Phase 0）."""
import json
import os
import tempfile

from database.knowledge_base import KnowledgeBase  # noqa: E402


def _fresh_kb() -> KnowledgeBase:
    os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mktemp(suffix='.db')}"
    return KnowledgeBase()


class TestSnapshotDeactivate:
    def test_snapshot_roundtrip(self, tmp_path) -> None:
        kb = _fresh_kb()
        kb.add_knowledge({
            "error_signature": "sig-snap-1",
            "cause": "x",
            "solution_pattern": {"action": "edit"},
        })
        path = kb.snapshot(str(tmp_path / "fkb_snapshot.json"))
        data = json.load(open(path))
        assert len(data) == 1
        assert data[0]["error_signature"] == "sig-snap-1"
        assert data[0]["disabled"] is False

    def test_deactivate_excludes_from_active(self) -> None:
        kb = _fresh_kb()
        kb.add_knowledge({
            "error_signature": "sig-dis-1",
            "cause": "x",
            "solution_pattern": {},
        })
        entry_id = kb.get_id_by_signature("sig-dis-1")
        assert entry_id is not None
        kb.deactivate(entry_id)
        active = kb.list_active()
        assert all(e["id"] != entry_id for e in active)
        # snapshotには無効化済みも含まれる（全体バックアップ）
        snap_path = kb.snapshot(str(tempfile.mktemp(suffix=".json")))
        snap = json.load(open(snap_path))
        assert any(s["id"] == entry_id and s["disabled"] for s in snap)
