"""壁2-A: 学習経路の削除行数上限ガードのテスト（nexuscore-bench Phase 0）.

spec: obsidian-ssot docs/superpowers/specs/2026-08-17-nexuscore-bench-design.md §3 Phase 0
単純True化を避け、allow_deletions=True でも削除行数上限でブロックする。
"""
from pathlib import Path

from src.nexuscore.config.self_healing_config import SelfHealingConfig
from src.nexuscore.services.patch_applier import PatchApplier


def _patch(deletions: int, total: int = 30) -> str:
    """削除行のみの unified diff 風テキストを生成する（危険検知は行頭'-'を数える）."""
    lines = "\n".join(f"-line{i}" for i in range(deletions))
    return (
        "--- a/demo.txt\n"
        "+++ b/demo.txt\n"
        f"@@ -1,{total} +1,{total - deletions} @@\n"
        f"{lines}\n"
    )


class TestDeleteCap:
    def test_over_cap_blocked(self, tmp_path: Path) -> None:
        ap = PatchApplier()
        (tmp_path / "demo.txt").write_text(
            "\n".join(f"line{i}" for i in range(30)) + "\n"
        )
        result = ap.apply_patch(
            patch_text=_patch(25),
            project_path=str(tmp_path),
            allow_deletions=True,
            max_delete_lines=20,
        )
        assert result.get("blocked_reason") == "delete_cap_exceeded"
        assert result.get("applied") is False
        assert result.get("delete_lines") == 25

    def test_under_cap_not_blocked_by_cap(self, tmp_path: Path) -> None:
        ap = PatchApplier()
        (tmp_path / "demo.txt").write_text(
            "\n".join(f"line{i}" for i in range(30)) + "\n"
        )
        result = ap.apply_patch(
            patch_text=_patch(10),
            project_path=str(tmp_path),
            allow_deletions=True,
            max_delete_lines=20,
        )
        # 上限ガードではブロックされない（適用成否はパッチ内容次第で別判定）
        assert result.get("blocked_reason") is None

    def test_cap_default_is_20(self) -> None:
        cfg = SelfHealingConfig()
        assert cfg.max_delete_lines == 20


class TestAstSafetyRollback:
    """壁2-B: 削除適用後のAST安全検証+ロールバック（difflibで有効なdiffを生成）."""

    def test_broken_delete_rolled_back(self, tmp_path: Path) -> None:
        import difflib

        before = "def f():\n    return 1\nx = f()\n"
        target = tmp_path / "demo.py"
        target.write_text(before)
        after_lines = ["def f():\n", "x = f()\n"]  # 関数本体を削除→IndentationError
        diff = "".join(
            difflib.unified_diff(
                before.splitlines(keepends=True),
                after_lines,
                fromfile="demo.py",
                tofile="demo.py",
            )
        )
        ap = PatchApplier()
        result = ap.apply_patch(
            patch_text=diff,
            project_path=str(tmp_path),
            allow_deletions=True,
        )
        assert result.get("blocked_reason") == "ast_safety_reject"
        assert result.get("applied") is False
        assert result.get("human_approval_required") is True
        # ロールバック確認: ファイルは適用前のまま
        assert target.read_text() == before
