"""FKB参照ログ: どのknowledge_idがどのタスクのどのステップで使われたか（nexuscore-bench主指標の前提）.

spec: obsidian-ssot docs/superpowers/specs/2026-08-17-nexuscore-bench-design.md §3 Task「FKB参照ログ保存スキーマ」
"""
import os
import tempfile

from database.knowledge_base import KnowledgeBase  # noqa: E402


def _make_kb_with_entry(signature: str) -> tuple[KnowledgeBase, int]:
    # テストごとに独立したsqliteファイル（テスト間のDB共有を避ける）
    os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mktemp(suffix='.db')}"
    kb = KnowledgeBase()
    status = kb.add_knowledge({
        "error_signature": signature,
        "cause": "テスト用",
        "solution_pattern": {"action": "edit"},
    })
    assert status in ("created", "updated")
    entry_id = kb.get_id_by_signature(signature)
    assert entry_id is not None
    return kb, entry_id


class TestReferenceLog:
    def test_log_and_query(self) -> None:
        kb, entry_id = _make_kb_with_entry("sig-reflog-001")
        kb.log_reference(
            knowledge_id=entry_id,
            task_id="task-A1",
            step="debugger",
            outcome="success",
        )
        refs = kb.query_references(task_id="task-A1")
        assert len(refs) == 1
        assert refs[0]["knowledge_id"] == entry_id
        assert refs[0]["step"] == "debugger"
        assert refs[0]["outcome"] == "success"

    def test_multiple_refs_across_tasks(self) -> None:
        kb, entry_id = _make_kb_with_entry("sig-reflog-002")
        kb.log_reference(entry_id, "task-A1", "debugger", "failure")
        kb.log_reference(entry_id, "task-A2", "postmortem", "success")
        a1 = kb.query_references(task_id="task-A1")
        a2 = kb.query_references(task_id="task-A2")
        assert len(a1) == 1 and a1[0]["outcome"] == "failure"
        assert len(a2) == 1 and a2[0]["outcome"] == "success"
        # 参照タイミング(step)も記録されている
        assert a2[0]["step"] == "postmortem"

    def test_get_id_by_signature_missing_returns_none(self) -> None:
        kb, _ = _make_kb_with_entry("sig-reflog-003")
        assert kb.get_id_by_signature("no-such-signature-xyz") is None
