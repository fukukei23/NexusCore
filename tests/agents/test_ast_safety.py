"""壁2-B: 削除パッチ適用前のASTレベル安全検証（最小実装）のテスト（nexuscore-bench Phase 0）."""
from src.nexuscore.agents._guardian_helpers.ast_safety import check_delete_safety


class TestCheckDeleteSafety:
    def test_syntax_broken_after_delete_rejected(self) -> None:
        # 削除後に構文エラーになるケース: 関数本体だけ消してdefを残す
        before = "def f():\n    return 1\n"
        after = "def f():\n"  # 本体消失=IndentationError
        verdict = check_delete_safety(before, after)
        assert verdict["ok"] is False
        assert "syntax" in verdict["reason"]
        assert verdict["human_approval_required"] is True

    def test_syntax_valid_passed(self) -> None:
        before = "import os\nimport sys\nprint(sys.argv)\n"
        after = "import sys\nprint(sys.argv)\n"  # unused import os を削除
        verdict = check_delete_safety(before, after)
        assert verdict["ok"] is True
        assert verdict["human_approval_required"] is False

    def test_file_emptied_rejected(self) -> None:
        before = "x = 1\ny = 2\n"
        after = ""
        verdict = check_delete_safety(before, after)
        assert verdict["ok"] is False
        assert verdict["human_approval_required"] is True
