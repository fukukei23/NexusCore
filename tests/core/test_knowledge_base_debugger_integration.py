"""中央FKB(database.knowledge_base)への永続化がDebuggerAgentの検索から
参照可能であることを検証する回帰テスト（Stage 3・spec §5「debuggerとの接続」）。

新規DBは作らない設計のため、DebuggerAgent側の `knowledge_base` シングルトンを
一時SQLiteに差し替えて検証する。
"""

from unittest.mock import patch

from database.knowledge_base import KnowledgeBase


def test_debugger_finds_solution_persisted_via_add_knowledge(tmp_path):
    db_path = tmp_path / "fkb_test.db"
    kb = KnowledgeBase(db_url=f"sqlite:///{db_path}")

    entry = {
        "error_signature": "ZeroDivisionError: division by zero",
        "cause": "ゼロ除算",
        "target": "source_file",
        "solution_pattern": {"type": "llm_diagnose_and_fix", "instruction": "guard against zero"},
        "description": "desc",
    }
    status = kb.add_knowledge(entry)
    assert status == "created"

    with patch("nexuscore.agents.debugger_agent.knowledge_base", kb):
        from nexuscore.agents.debugger_agent import DebuggerAgent

        debugger = DebuggerAgent()
        solution = debugger._find_solution_from_kb("Traceback...\nZeroDivisionError: division by zero")

    assert solution is not None
    assert solution["error_signature"] == "ZeroDivisionError: division by zero"
    assert solution["solution_pattern"]["instruction"] == "guard against zero"
