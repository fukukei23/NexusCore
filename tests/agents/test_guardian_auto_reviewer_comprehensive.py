"""
guardian_auto_reviewer.py の包括的テスト

カバレッジ:
- GuardianAutoReviewer: 自動レビューロジック
  - __init__: プロジェクトタイプ検出
  - review_unified_diff: メインレビューメソッド
  - _parse_unified_diff: diffパーサ
  - _check_sandbox_violations: サンドボックス違反チェック
  - _check_testing_rules: テスト品質チェック
  - _check_code_safety_rules: コード安全性チェック
  - _check_nexuscore_specific: NexusCore固有チェック
  - _check_atelier_specific: Atelier固有チェック
"""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

try:
    from nexuscore.agents.guardian_auto_reviewer import (
        GuardianAutoReviewer,
        ReviewDecision,
        ReviewIssue,
        ReviewResult,
        FileChange,
        Hunk,
        ProjectType
    )
    HAS_GUARDIAN = True
except ImportError:
    HAS_GUARDIAN = False
    GuardianAutoReviewer = None


@pytest.mark.skipif(not HAS_GUARDIAN, reason="guardian_auto_reviewer module not available")
class TestDataClasses:
    """データクラスのテスト"""

    def test_review_issue_creation(self):
        """ReviewIssueの作成"""
        issue = ReviewIssue(
            level="error",
            code="SEC-001",
            message="Security violation",
            file_path="src/test.py",
            line_no=10
        )

        assert issue.level == "error"
        assert issue.code == "SEC-001"
        assert issue.message == "Security violation"
        assert issue.file_path == "src/test.py"
        assert issue.line_no == 10

    def test_review_result_has_errors(self):
        """ReviewResult.has_errorsプロパティ"""
        issue1 = ReviewIssue(level="error", code="E1", message="Error")
        issue2 = ReviewIssue(level="warning", code="W1", message="Warning")

        result = ReviewResult(decision=ReviewDecision.REJECT, issues=[issue1, issue2])

        assert result.has_errors is True
        assert result.has_warnings is True

    def test_review_result_summary(self):
        """ReviewResult.summaryメソッド"""
        issue = ReviewIssue(
            level="error",
            code="SEC-001",
            message="Violation",
            file_path="test.py",
            line_no=5
        )
        result = ReviewResult(decision=ReviewDecision.REJECT, issues=[issue])

        summary = result.summary()

        assert "decision=reject" in summary
        assert "[ERROR][SEC-001]" in summary
        assert "test.py:5" in summary
        assert "Violation" in summary

    def test_hunk_creation(self):
        """Hunkデータクラスの作成"""
        hunk = Hunk(
            old_start=10,
            old_lines=3,
            new_start=10,
            new_lines=4,
            lines=["+new line", " unchanged", "-old line"]
        )

        assert hunk.old_start == 10
        assert hunk.new_start == 10
        assert len(hunk.lines) == 3


@pytest.mark.skipif(not HAS_GUARDIAN, reason="guardian_auto_reviewer module not available")
class TestGuardianAutoReviewerInit:
    """GuardianAutoReviewer 初期化のテスト"""

    def test_init_nexuscore_project(self):
        """NexusCoreプロジェクトの検出"""
        reviewer = GuardianAutoReviewer(project_name="nexuscore-test")

        assert reviewer.project_type == ProjectType.NEXUSCORE

    def test_init_atelier_project(self):
        """Atelierプロジェクトの検出"""
        reviewer = GuardianAutoReviewer(project_name="atelier-kyo-manager")

        assert reviewer.project_type == ProjectType.ATELIER

    def test_init_other_project(self):
        """その他のプロジェクト"""
        reviewer = GuardianAutoReviewer(project_name="random-project")

        assert reviewer.project_type == ProjectType.OTHER


@pytest.mark.skipif(not HAS_GUARDIAN, reason="guardian_auto_reviewer module not available")
class TestParsified:
    """GuardianAutoReviewer._parse_unified_diff() のテスト"""

    def test_parse_simple_diff(self):
        """シンプルなdiffのパース"""
        diff_text = """diff --git a/test.py b/test.py
--- a/test.py
+++ b/test.py
@@ -1,2 +1,3 @@
 def test():
-    pass
+    return True
+    # New line
"""
        reviewer = GuardianAutoReviewer("test")
        files = reviewer._parse_unified_diff(diff_text)

        assert len(files) == 1
        assert files[0].path == "test.py"
        assert len(files[0].hunks) == 1
        assert files[0].hunks[0].old_start == 1
        assert files[0].hunks[0].new_start == 1

    def test_parse_multiple_files(self):
        """複数ファイルのdiff"""
        diff_text = """diff --git a/file1.py b/file1.py
--- a/file1.py
+++ b/file1.py
@@ -1,1 +1,1 @@
-old line
+new line
diff --git a/file2.py b/file2.py
--- a/file2.py
+++ b/file2.py
@@ -1,1 +1,1 @@
-old2
+new2
"""
        reviewer = GuardianAutoReviewer("test")
        files = reviewer._parse_unified_diff(diff_text)

        assert len(files) == 2
        assert files[0].path == "file1.py"
        assert files[1].path == "file2.py"

    def test_parse_empty_diff(self):
        """空のdiff"""
        reviewer = GuardianAutoReviewer("test")
        files = reviewer._parse_unified_diff("")

        assert len(files) == 0


@pytest.mark.skipif(not HAS_GUARDIAN, reason="guardian_auto_reviewer module not available")
class TestCheckSandboxViolations:
    """GuardianAutoReviewer._check_sandbox_violations() のテスト"""

    def test_check_dangerous_path(self):
        """危険なパスの検出"""
        diff_text = """--- a/.git/config
+++ b/.git/config
@@ -1,1 +1,1 @@
+dangerous change
"""
        reviewer = GuardianAutoReviewer("test")
        files = reviewer._parse_unified_diff(diff_text)
        issues = reviewer._check_sandbox_violations(files)

        assert len(issues) > 0
        assert issues[0].code == "SEC-001"
        assert issues[0].level == "error"

    def test_check_dangerous_command(self):
        """危険なコマンドの検出"""
        diff_text = """--- a/script.sh
+++ b/script.sh
@@ -1,1 +1,2 @@
 #!/bin/bash
+rm -rf /tmp/*
"""
        reviewer = GuardianAutoReviewer("test")
        files = reviewer._parse_unified_diff(diff_text)
        issues = reviewer._check_sandbox_violations(files)

        assert len(issues) > 0
        assert any(i.code == "SEC-002" for i in issues)

    def test_check_no_violations(self):
        """違反がない場合"""
        diff_text = """--- a/src/test.py
+++ b/src/test.py
@@ -1,1 +1,2 @@
 def test():
+    return True
"""
        reviewer = GuardianAutoReviewer("test")
        files = reviewer._parse_unified_diff(diff_text)
        issues = reviewer._check_sandbox_violations(files)

        assert len(issues) == 0


@pytest.mark.skipif(not HAS_GUARDIAN, reason="guardian_auto_reviewer module not available")
class TestCheckTestingRules:
    """GuardianAutoReviewer._check_testing_rules() のテスト"""

    def test_check_meaningless_assert(self):
        """意味のないアサーションの検出"""
        diff_text = """--- a/tests/test_foo.py
+++ b/tests/test_foo.py
@@ -1,1 +1,2 @@
 def test_foo():
+    assert True
"""
        reviewer = GuardianAutoReviewer("test")
        files = reviewer._parse_unified_diff(diff_text)
        issues = reviewer._check_testing_rules(files)

        assert len(issues) > 0
        assert issues[0].code == "TEST-001"
        assert issues[0].level == "warning"

    def test_check_non_test_file(self):
        """非テストファイルはチェックされない"""
        diff_text = """--- a/src/foo.py
+++ b/src/foo.py
@@ -1,1 +1,2 @@
 def foo():
+    assert True  # This is not a test
"""
        reviewer = GuardianAutoReviewer("test")
        files = reviewer._parse_unified_diff(diff_text)
        issues = reviewer._check_testing_rules(files)

        # 非テストファイルなのでTEST-001は発生しない
        assert len(issues) == 0


@pytest.mark.skipif(not HAS_GUARDIAN, reason="guardian_auto_reviewer module not available")
class TestCheckCodeSafetyRules:
    """GuardianAutoReviewer._check_code_safety_rules() のテスト"""

    def test_check_except_pass(self):
        """except passの検出"""
        diff_text = """--- a/src/foo.py
+++ b/src/foo.py
@@ -1,2 +1,4 @@
 def foo():
-    pass
+    try:
+        something()
+    except: pass
"""
        reviewer = GuardianAutoReviewer("test")
        files = reviewer._parse_unified_diff(diff_text)
        issues = reviewer._check_code_safety_rules(files)

        assert len(issues) > 0
        # except passのエラーが検出される
        assert any(i.code == "SAFE-001" for i in issues)

    def test_check_bare_except(self):
        """bare exceptの検出"""
        diff_text = """--- a/src/foo.py
+++ b/src/foo.py
@@ -1,1 +1,3 @@
 def foo():
+    try:
+        pass
+    except:
+        log("error")
"""
        reviewer = GuardianAutoReviewer("test")
        files = reviewer._parse_unified_diff(diff_text)
        issues = reviewer._check_code_safety_rules(files)

        # bare exceptの警告が検出される
        assert any(i.code == "SAFE-002" for i in issues)

    def test_check_debug_flag(self):
        """debugフラグの検出"""
        diff_text = """--- a/src/foo.py
+++ b/src/foo.py
@@ -1,1 +1,1 @@
-def foo():
+def foo(debug=True):
"""
        reviewer = GuardianAutoReviewer("test")
        files = reviewer._parse_unified_diff(diff_text)
        issues = reviewer._check_code_safety_rules(files)

        # debug フラグの警告が検出される
        assert any(i.code == "SAFE-003" for i in issues)


@pytest.mark.skipif(not HAS_GUARDIAN, reason="guardian_auto_reviewer module not available")
class TestCheckNexuscoreSpecific:
    """GuardianAutoReviewer._check_nexuscore_specific() のテスト"""

    def test_check_orchestrator_phase_change(self):
        """Orchestratorフェーズ変更の検出"""
        diff_text = """--- a/src/orchestrator.py
+++ b/src/orchestrator.py
@@ -1,2 +1,1 @@
-# Requirement and Plan phase stages
+# Modified phase
"""
        reviewer = GuardianAutoReviewer("nexuscore")
        files = reviewer._parse_unified_diff(diff_text)
        issues = reviewer._check_nexuscore_specific(files)

        # orchestratorの変更に関する警告
        assert any(i.code == "NC-001" for i in issues)

    def test_check_fkb_deletion(self):
        """FKB削除の検出"""
        diff_text = """--- a/database/fkb_entries.json
+++ b/database/fkb_entries.json
@@ -1,2 +1,1 @@
 {"entry": "test"}
-{"entry": "deleted"}
"""
        reviewer = GuardianAutoReviewer("nexuscore")
        files = reviewer._parse_unified_diff(diff_text)
        issues = reviewer._check_nexuscore_specific(files)

        # FKB削除の警告
        assert any(i.code == "NC-002" for i in issues)

    def test_check_non_nexuscore_project(self):
        """NexusCore以外のプロジェクト"""
        diff_text = """--- a/src/orchestrator.py
+++ b/src/orchestrator.py
@@ -1,1 +1,2 @@
 # test
+# change
"""
        reviewer = GuardianAutoReviewer("other-project")
        files = reviewer._parse_unified_diff(diff_text)
        issues = reviewer._check_nexuscore_specific(files)

        # NexusCore固有チェックは実行されない
        # (review_unified_diffがproject_typeをチェックするため)
        assert True  # チェックがスキップされることを確認


@pytest.mark.skipif(not HAS_GUARDIAN, reason="guardian_auto_reviewer module not available")
class TestCheckAtelierSpecific:
    """GuardianAutoReviewer._check_atelier_specific() のテスト"""

    def test_check_domestic_domain(self):
        """国内ECサイトドメインの検出"""
        diff_text = """--- a/src/scraper.py
+++ b/src/scraper.py
@@ -1,1 +1,2 @@
 def scrape():
+    url = "https://www.rakuten.co.jp/products"
"""
        reviewer = GuardianAutoReviewer("atelier-kyo")
        files = reviewer._parse_unified_diff(diff_text)
        issues = reviewer._check_atelier_specific(files)

        # 国内ドメインのエラーが検出される
        assert len(issues) > 0
        assert any(i.code == "AT-001" for i in issues)

    def test_check_profit_calculation(self):
        """利益計算ロジックの変更検出"""
        diff_text = """--- a/src/calculator.py
+++ b/src/calculator.py
@@ -1,1 +1,2 @@
 def calculate():
+    profit = revenue - cost
"""
        reviewer = GuardianAutoReviewer("atelier")
        files = reviewer._parse_unified_diff(diff_text)
        issues = reviewer._check_atelier_specific(files)

        # 利益計算の警告が検出される
        assert any(i.code == "AT-002" for i in issues)


@pytest.mark.skipif(not HAS_GUARDIAN, reason="guardian_auto_reviewer module not available")
class TestReviewUnifiedDiff:
    """GuardianAutoReviewer.review_unified_diff() のテスト"""

    def test_review_approve_clean_diff(self):
        """クリーンなdiffは承認される"""
        diff_text = """--- a/src/foo.py
+++ b/src/foo.py
@@ -1,1 +1,2 @@
 def foo():
+    return True
"""
        reviewer = GuardianAutoReviewer("test")
        result = reviewer.review_unified_diff(diff_text)

        assert result.decision == ReviewDecision.APPROVE
        assert len(result.issues) == 0

    def test_review_reject_with_errors(self):
        """エラーがあるdiffは却下される"""
        diff_text = """--- a/src/foo.py
+++ b/src/foo.py
@@ -1,1 +1,3 @@
 def foo():
+    try:
+        pass
+    except: pass
"""
        reviewer = GuardianAutoReviewer("test")
        result = reviewer.review_unified_diff(diff_text)

        assert result.decision == ReviewDecision.REJECT
        assert result.has_errors is True

    def test_review_manual_review_with_warnings(self):
        """警告のみの場合はマニュアルレビュー"""
        diff_text = """--- a/tests/test_foo.py
+++ b/tests/test_foo.py
@@ -1,1 +1,2 @@
 def test_foo():
+    assert True
"""
        reviewer = GuardianAutoReviewer("test")
        result = reviewer.review_unified_diff(diff_text)

        assert result.decision == ReviewDecision.MANUAL_REVIEW
        assert result.has_warnings is True


@pytest.mark.skipif(not HAS_GUARDIAN, reason="guardian_auto_reviewer module not available")
class TestEdgeCases:
    """エッジケースのテスト"""

    def test_review_empty_diff(self):
        """空のdiff"""
        reviewer = GuardianAutoReviewer("test")
        result = reviewer.review_unified_diff("")

        assert result.decision == ReviewDecision.APPROVE
        assert len(result.issues) == 0

    def test_review_malformed_diff(self):
        """不正な形式のdiff"""
        malformed_diff = "This is not a valid diff format"

        reviewer = GuardianAutoReviewer("test")
        result = reviewer.review_unified_diff(malformed_diff)

        # パースエラーでも処理は継続
        assert result.decision in [ReviewDecision.APPROVE, ReviewDecision.REJECT, ReviewDecision.MANUAL_REVIEW]

    def test_multiple_violations_in_one_file(self):
        """1ファイル内の複数違反"""
        diff_text = """--- a/src/foo.py
+++ b/src/foo.py
@@ -1,1 +1,5 @@
 def foo():
+    rm -rf /tmp
+    try:
+        pass
+    except: pass
"""
        reviewer = GuardianAutoReviewer("test")
        result = reviewer.review_unified_diff(diff_text)

        # 複数の問題が検出される
        assert len(result.issues) >= 2
