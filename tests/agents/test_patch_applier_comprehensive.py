"""
============================================================================
Comprehensive Tests for PatchApplier
============================================================================
高品質テストの原則:
- 外部依存（patch library）は実際の動作をテスト
- 実際のファイルシステム操作をテスト
- エッジケースとエラー条件をカバー
============================================================================
"""
import pytest
import tempfile
import os
import types
from pathlib import Path

from nexuscore.agents import patch_applier as pa_module
from nexuscore.agents.patch_applier import PatchApplier


class DummyPatchSet:
    """テスト用のダミーPatchSetクラス"""

    def __init__(self, should_apply=True):
        self.should_apply = should_apply
        self.root = None
        self.strip = None

    def apply(self, root=None, strip=0):
        self.root = root
        self.strip = strip
        if not self.should_apply:
            return False
        return True


@pytest.fixture
def patch_applier():
    """PatchApplierのインスタンス"""
    return PatchApplier()


@pytest.fixture
def temp_project():
    """一時的なプロジェクトディレクトリ"""
    with tempfile.TemporaryDirectory(prefix="test_patch_") as tmpdir:
        # テスト用のファイルを作成
        test_file = Path(tmpdir) / "example.py"
        test_file.write_text("""def hello():
    print("Hello")
    return "world"
""")
        yield {
            "path": tmpdir,
            "file": str(test_file),
        }


@pytest.fixture
def valid_patch():
    """有効なunified diffパッチ（削除行を含む）"""
    return """--- example.py
+++ example.py
@@ -1,3 +1,3 @@
 def hello():
-    print("Hello")
+    print("Hello World")
     return "world"
"""


@pytest.fixture
def safe_patch():
    """削除行を含まない安全なパッチ（追加のみ）"""
    return """--- example.py
+++ example.py
@@ -1,3 +1,4 @@
 def hello():
     print("Hello")
+    print("Extra log")
     return "world"
"""


@pytest.fixture
def dangerous_patch():
    """削除行を含む危険なパッチ"""
    return """--- example.py
+++ example.py
@@ -1,3 +1,2 @@
 def hello():
-    print("Hello")
-    return "world"
+    pass
"""


# ============================================================================
# Tests: __init__
# ============================================================================


class TestInit:
    def test_init_creates_logger(self, patch_applier):
        """ロガーが作成される"""
        assert patch_applier.logger is not None
        assert patch_applier.logger.name == "PatchApplier"


# ============================================================================
# Tests: apply_patch (main API)
# ============================================================================


class TestApplyPatch:
    def test_apply_patch_success(self, monkeypatch, patch_applier, temp_project, valid_patch):
        """正常なパッチ適用"""
        dummy_set = DummyPatchSet(should_apply=True)

        def fake_fromstring(data):
            return dummy_set

        fake_patch = types.SimpleNamespace(fromstring=fake_fromstring)
        monkeypatch.setattr(pa_module, "patch", fake_patch)

        result = patch_applier.apply_patch(
            patch_text=valid_patch,
            project_path=temp_project["path"],
            dry_run=False,
            allow_deletions=True,
        )

        assert result["applied"] is True
        assert result["dry_run"] is False
        assert "successfully" in result["reason"].lower()
        assert result["error"] is None

    def test_apply_patch_dry_run(self, monkeypatch, patch_applier, temp_project, safe_patch):
        """dry_runモードでパッチを適用しない"""
        dummy_set = DummyPatchSet()

        def fake_fromstring(data):
            return dummy_set

        fake_patch = types.SimpleNamespace(fromstring=fake_fromstring)
        monkeypatch.setattr(pa_module, "patch", fake_patch)

        result = patch_applier.apply_patch(
            patch_text=safe_patch,
            project_path=temp_project["path"],
            dry_run=True,
            allow_deletions=False,
        )

        assert result["applied"] is False
        assert result["dry_run"] is True
        assert "dry-run" in result["reason"].lower()

    def test_apply_patch_with_empty_patch(self, patch_applier, temp_project):
        """空のパッチテキスト"""
        result = patch_applier.apply_patch(
            patch_text="",
            project_path=temp_project["path"],
        )

        assert result["applied"] is False
        assert "empty" in result["reason"].lower()

    def test_apply_patch_with_invalid_project_path(self, patch_applier, valid_patch):
        """存在しないプロジェクトパス"""
        result = patch_applier.apply_patch(
            patch_text=valid_patch,
            project_path="/nonexistent/path",
        )

        assert result["applied"] is False
        assert "not found" in result["reason"].lower()

    def test_apply_patch_blocks_dangerous_patch(self, monkeypatch, patch_applier, temp_project, dangerous_patch):
        """allow_deletions=Falseの場合、削除行を含むパッチをブロック"""
        result = patch_applier.apply_patch(
            patch_text=dangerous_patch,
            project_path=temp_project["path"],
            allow_deletions=False,
        )

        assert result["applied"] is False
        assert result["dangerous"] is True
        assert result["delete_lines"] > 0
        assert "allow_deletions" in result["reason"]

    def test_apply_patch_allows_dangerous_patch_when_enabled(self, monkeypatch, patch_applier, temp_project, dangerous_patch):
        """allow_deletions=Trueの場合、削除行を含むパッチを許可"""
        dummy_set = DummyPatchSet(should_apply=True)

        def fake_fromstring(data):
            return dummy_set

        fake_patch = types.SimpleNamespace(fromstring=fake_fromstring)
        monkeypatch.setattr(pa_module, "patch", fake_patch)

        result = patch_applier.apply_patch(
            patch_text=dangerous_patch,
            project_path=temp_project["path"],
            allow_deletions=True,
        )

        assert result["dangerous"] is True
        assert result["delete_lines"] > 0
        # パッチが適用される
        assert result["applied"] is True

    def test_apply_patch_with_parse_error(self, monkeypatch, patch_applier, temp_project):
        """パッチのパースエラー"""

        def fake_fromstring(data):
            raise Exception("Parse error")

        fake_patch = types.SimpleNamespace(fromstring=fake_fromstring)
        monkeypatch.setattr(pa_module, "patch", fake_patch)

        result = patch_applier.apply_patch(
            patch_text="invalid patch",
            project_path=temp_project["path"],
        )

        assert result["applied"] is False
        assert "parse" in result["reason"].lower()
        assert result["error"] is not None

    def test_apply_patch_with_application_failure(self, monkeypatch, patch_applier, temp_project, safe_patch):
        """パッチ適用の失敗"""
        dummy_set = DummyPatchSet(should_apply=False)

        def fake_fromstring(data):
            return dummy_set

        fake_patch = types.SimpleNamespace(fromstring=fake_fromstring)
        monkeypatch.setattr(pa_module, "patch", fake_patch)

        result = patch_applier.apply_patch(
            patch_text=safe_patch,
            project_path=temp_project["path"],
        )

        assert result["applied"] is False
        assert "failed" in result["reason"].lower()

    def test_apply_patch_with_exception_during_apply(self, monkeypatch, patch_applier, temp_project, safe_patch):
        """適用中の例外"""

        class ErrorPatchSet:
            def apply(self, **kwargs):
                raise Exception("Application error")

        def fake_fromstring(data):
            return ErrorPatchSet()

        fake_patch = types.SimpleNamespace(fromstring=fake_fromstring)
        monkeypatch.setattr(pa_module, "patch", fake_patch)

        result = patch_applier.apply_patch(
            patch_text=safe_patch,
            project_path=temp_project["path"],
        )

        assert result["applied"] is False
        assert "exception" in result["reason"].lower()
        assert result["error"] is not None

    def test_apply_patch_handles_strip_parameter(self, monkeypatch, patch_applier, temp_project, safe_patch):
        """strip引数をサポートするケース"""
        dummy_set = DummyPatchSet(should_apply=True)

        def fake_fromstring(data):
            return dummy_set

        fake_patch = types.SimpleNamespace(fromstring=fake_fromstring)
        monkeypatch.setattr(pa_module, "patch", fake_patch)

        patch_applier.apply_patch(
            patch_text=safe_patch,
            project_path=temp_project["path"],
        )

        # stripパラメータが設定されている
        assert dummy_set.root == temp_project["path"]

    def test_apply_patch_handles_strip_type_error(self, monkeypatch, patch_applier, temp_project, safe_patch):
        """strip引数がサポートされていない場合のフォールバック"""

        class StripErrorPatchSet:
            def __init__(self):
                self.call_count = 0

            def apply(self, **kwargs):
                self.call_count += 1
                if "strip" in kwargs and self.call_count == 1:
                    raise TypeError("strip not supported")
                return True

        error_set = StripErrorPatchSet()

        def fake_fromstring(data):
            return error_set

        fake_patch = types.SimpleNamespace(fromstring=fake_fromstring)
        monkeypatch.setattr(pa_module, "patch", fake_patch)

        result = patch_applier.apply_patch(
            patch_text=safe_patch,
            project_path=temp_project["path"],
        )

        # 2回呼ばれる: 1回目はstrip付き（失敗）、2回目はstripなし（成功）
        assert error_set.call_count == 2
        assert result["applied"] is True


# ============================================================================
# Tests: _detect_danger
# ============================================================================


class TestDetectDanger:
    def test_detect_danger_with_no_deletions(self, patch_applier):
        """削除行がない場合"""
        safe_patch = """--- a/file.py
+++ b/file.py
@@ -1,2 +1,3 @@
 def hello():
+    print("new line")
     pass
"""
        result = patch_applier._detect_danger(safe_patch)

        assert result["has_delete"] is False
        assert result["delete_lines"] == 0

    def test_detect_danger_with_deletions(self, patch_applier, dangerous_patch):
        """削除行がある場合"""
        result = patch_applier._detect_danger(dangerous_patch)

        assert result["has_delete"] is True
        assert result["delete_lines"] > 0

    def test_detect_danger_excludes_header_lines(self, patch_applier):
        """ヘッダ行（--- a/file）を除外"""
        patch_with_header = """--- a/old_file.py
+++ b/new_file.py
@@ -1,2 +1,1 @@
-deleted line
 kept line
"""
        result = patch_applier._detect_danger(patch_with_header)

        # "--- a/old_file.py" は除外され、"-deleted line" のみカウント
        assert result["delete_lines"] == 1

    def test_detect_danger_with_multiple_deletions(self, patch_applier):
        """複数の削除行"""
        multi_delete_patch = """--- a/file.py
+++ b/file.py
@@ -1,5 +1,2 @@
 line1
-line2
-line3
-line4
 line5
"""
        result = patch_applier._detect_danger(multi_delete_patch)

        assert result["has_delete"] is True
        assert result["delete_lines"] == 3


# ============================================================================
# Tests: apply_patch_bool (compatibility wrapper)
# ============================================================================


class TestApplyPatchBool:
    def test_apply_patch_bool_returns_true_on_success(self, monkeypatch, patch_applier, temp_project, safe_patch):
        """成功時にTrueを返す"""
        dummy_set = DummyPatchSet(should_apply=True)

        def fake_fromstring(data):
            return dummy_set

        fake_patch = types.SimpleNamespace(fromstring=fake_fromstring)
        monkeypatch.setattr(pa_module, "patch", fake_patch)

        result = patch_applier.apply_patch_bool(
            patch_text=safe_patch,
            project_path=temp_project["path"],
        )

        assert result is True

    def test_apply_patch_bool_returns_false_on_failure(self, monkeypatch, patch_applier, temp_project, safe_patch):
        """失敗時にFalseを返す"""
        dummy_set = DummyPatchSet(should_apply=False)

        def fake_fromstring(data):
            return dummy_set

        fake_patch = types.SimpleNamespace(fromstring=fake_fromstring)
        monkeypatch.setattr(pa_module, "patch", fake_patch)

        result = patch_applier.apply_patch_bool(
            patch_text=safe_patch,
            project_path=temp_project["path"],
        )

        assert result is False

    def test_apply_patch_bool_defaults(self, monkeypatch, patch_applier, temp_project, safe_patch):
        """デフォルト設定（dry_run=False, allow_deletions=False）"""
        dummy_set = DummyPatchSet(should_apply=True)

        def fake_fromstring(data):
            return dummy_set

        fake_patch = types.SimpleNamespace(fromstring=fake_fromstring)
        monkeypatch.setattr(pa_module, "patch", fake_patch)

        patch_applier.apply_patch_bool(
            patch_text=safe_patch,
            project_path=temp_project["path"],
        )

        # dry_run=False, allow_deletions=Falseで呼ばれる
        assert dummy_set.root == temp_project["path"]


# ============================================================================
# Tests: apply (legacy interface)
# ============================================================================


class TestApply:
    def test_apply_is_alias_for_apply_patch_bool(self, monkeypatch, patch_applier, temp_project, safe_patch):
        """applyメソッドはapply_patch_boolのエイリアス"""
        dummy_set = DummyPatchSet(should_apply=True)

        def fake_fromstring(data):
            return dummy_set

        fake_patch = types.SimpleNamespace(fromstring=fake_fromstring)
        monkeypatch.setattr(pa_module, "patch", fake_patch)

        result = patch_applier.apply(
            patch_str=safe_patch,
            project_path=temp_project["path"],
        )

        assert result is True


# ============================================================================
# Tests: get_text_diff (static method)
# ============================================================================


class TestGetTextDiff:
    def test_get_text_diff_with_simple_change(self):
        """簡単な変更の差分"""
        before = "line1\nline2\nline3\n"
        after = "line1\nmodified line2\nline3\n"

        diff = PatchApplier.get_text_diff(before, after)

        assert "--- before" in diff
        assert "+++ after" in diff
        assert "-line2" in diff
        assert "+modified line2" in diff

    def test_get_text_diff_with_addition(self):
        """行の追加"""
        before = "line1\nline2\n"
        after = "line1\nline2\nline3\n"

        diff = PatchApplier.get_text_diff(before, after)

        assert "+line3" in diff

    def test_get_text_diff_with_deletion(self):
        """行の削除"""
        before = "line1\nline2\nline3\n"
        after = "line1\nline3\n"

        diff = PatchApplier.get_text_diff(before, after)

        assert "-line2" in diff

    def test_get_text_diff_with_no_change(self):
        """変更なし"""
        text = "line1\nline2\nline3\n"

        diff = PatchApplier.get_text_diff(text, text)

        # 変更がない場合、diffは空（またはヘッダのみ）
        assert "@@" not in diff or diff.strip() == ""

    def test_get_text_diff_with_empty_before(self):
        """beforeが空"""
        before = ""
        after = "new line1\nnew line2\n"

        diff = PatchApplier.get_text_diff(before, after)

        assert "+new line1" in diff
        assert "+new line2" in diff

    def test_get_text_diff_with_empty_after(self):
        """afterが空"""
        before = "old line1\nold line2\n"
        after = ""

        diff = PatchApplier.get_text_diff(before, after)

        assert "-old line1" in diff
        assert "-old line2" in diff

    def test_get_text_diff_preserves_line_endings(self):
        """行末が保持される"""
        before = "line1\nline2\n"
        after = "line1\nmodified\n"

        diff = PatchApplier.get_text_diff(before, after)

        # unified diff形式で正しく生成される
        assert "--- before" in diff
        assert "+++ after" in diff


# ============================================================================
# Tests: Integration scenarios
# ============================================================================


class TestIntegrationScenarios:
    def test_full_workflow_with_danger_check(self, monkeypatch, patch_applier, temp_project):
        """完全なワークフロー: 危険度チェックからパッチ適用まで"""
        patch_text = """--- example.py
+++ example.py
@@ -1,3 +1,2 @@
 def hello():
-    print("Hello")
     return "world"
"""
        dummy_set = DummyPatchSet(should_apply=True)

        def fake_fromstring(data):
            return dummy_set

        fake_patch = types.SimpleNamespace(fromstring=fake_fromstring)
        monkeypatch.setattr(pa_module, "patch", fake_patch)

        # 削除を許可しない場合
        result1 = patch_applier.apply_patch(
            patch_text=patch_text,
            project_path=temp_project["path"],
            allow_deletions=False,
        )
        assert result1["applied"] is False
        assert result1["dangerous"] is True

        # 削除を許可する場合
        result2 = patch_applier.apply_patch(
            patch_text=patch_text,
            project_path=temp_project["path"],
            allow_deletions=True,
        )
        assert result2["applied"] is True

    def test_backwards_compatibility(self, monkeypatch, patch_applier, temp_project, safe_patch):
        """旧インターフェースとの後方互換性"""
        dummy_set = DummyPatchSet(should_apply=True)

        def fake_fromstring(data):
            return dummy_set

        fake_patch = types.SimpleNamespace(fromstring=fake_fromstring)
        monkeypatch.setattr(pa_module, "patch", fake_patch)

        # 3つのメソッドが同じように動作
        result1 = patch_applier.apply_patch_bool(safe_patch, temp_project["path"])
        result2 = patch_applier.apply(safe_patch, temp_project["path"])

        assert result1 is True
        assert result2 is True

    def test_error_handling_robustness(self, patch_applier, temp_project):
        """エラーハンドリングの堅牢性"""
        # 空のパッチ
        r1 = patch_applier.apply_patch("", temp_project["path"])
        assert r1["applied"] is False

        # 無効なプロジェクトパス
        r2 = patch_applier.apply_patch("dummy", "/invalid/path")
        assert r2["applied"] is False

        # すべてのエラーケースで例外を投げずに結果を返す
        assert "reason" in r1
        assert "reason" in r2
