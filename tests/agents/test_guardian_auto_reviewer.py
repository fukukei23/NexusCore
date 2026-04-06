"""
     2→test_guardian_auto_reviewer.py
     3+
     4+ from __future__ import annotations
     5+
     6+import json
     7+from nexuscore.agents.guardian_auto_reviewer import (
     8+    GuardianAutoReviewer,
    9+    ReviewDecision,
  10+    ReviewIssue,
  11+    ReviewResult,
   12+)


class TestGuardianAutoReviewer:
    19+    """GuardianAutoReviewer の基本動作テスト"""

    20+
    21+    def test_review_clean_diff_approve(self):
        23+        """クリーンな diff は APPROVE (ポリシールールなし)"""
        diff = """+++ b/src/example.py
@@ -0,0 +1,3 @@
+def hello():
    return "world"
"""
        reviewer = GuardianAutoReviewer(project_name="nexuscore")
        result = reviewer.review_unified_diff(diff)

        assert result.decision == ReviewDecision.APPROVE
        assert len(result.issues) == 0

    def test_review_dangerous_path_reject(self):
        24+        """危険なパスへの変更は REJECT"""
        diff = """+++ b/.git/config
@@ -0,0 +1,1 @@
+[core]
"""
        reviewer = GuardianAutoReviewer(project_name="nexuscore")
        result = reviewer.review_unified_diff(diff)

        assert result.decision == ReviewDecision.REJECT
        assert any(i.code == "SEC-001" for i in result.issues)

    def test_review_dangerous_command_reject(self):
        29+        """破壊的なコマンドンド REJECT"""
        diff = """+++ b/script.sh
@@ -0,0 +1,1 @@
+rm -rf /tmp
"""
        reviewer = GuardianAutoReviewer(project_name="nexuscore")
        result = reviewer.review_unified_diff(diff)

        assert result.decision == ReviewDecision.REJECT
        assert any(i.code == "SEC-002" for i in result.issues)

    def test_review_except_pass_reject(self):
        32+        """例外握りつぶしは REJECT"""
        diff = """+++ b/src/example.py
@@ -0,0 +1,2 @@
+try:
+    in something()
+except: pass
"""
        reviewer = GuardianAutoReviewer(project_name="nexuscore")
        result = reviewer.review_unified_diff(diff)

        assert result.decision == ReviewDecision.REJECT
        assert any(i.code == "SAFE-001" for i in result.issues)

    def test_review_meaningless_assert_warning(self):
        38+        """意味のないアサーションは警告"""
        diff = """+++ b/tests/test_example.py
@@ -0,0 +1,2 @@
+def test_something():
+    assert True
"""
        reviewer = GuardianAutoReviewer(project_name="nexuscore")
        result = reviewer.review_unified_diff(diff)

        assert result.decision == ReviewDecision.MANUAL_REVIEW
        assert any(i.code == "TEST-001" for i in result.issues)

    def test_review_nexuscore_orchestrator_warning(self):
        42+        """NexusCore の Orchestrator フェ更は警告"""
        diff = """+++ b/src/nexuscore/core/orchestrator.py
@@ -0,0 +1,5 @@
+    def run_requirement(self):
+    pass
+    def run_plan(self):
+        pass
"""
        reviewer = GuardianAutoReviewer(project_name="nexuscore")
        result = reviewer.review_unified_diff(diff)

        # NC-001 褜出される可能性がある
        assert result.decision == ReviewDecision.MANUAL_REVIEW
        assert len(result.issues) == 1
        # 最低限、 error になっても確認
        assert "Orchestrator" in result.summary()

    def test_review_atelier_domestic_domain_reject(self):
        47+        """atelier-kyo-manager の国内サイトURLは REJECT"""
        diff = """+++ b/src/example.py
@@ -0,0 +1,1 @@
+url = "https://www.rakuten.co.jp/item"
"""
        reviewer = GuardianAutoReviewer(project_name="atelier-kyo-manager")
        result = reviewer.review_unified_diff(diff)

        assert result.decision == ReviewDecision.REJECT
        assert any(i.code == "AT-001" for i in result.issues)

    def test_review_result_summary(self):
        49+        """ReviewResult.summary() の出力確認"""
        result = ReviewResult(
            decision=ReviewDecision.REJECT,
            issues=[
                ReviewIssue(
                    level="error",
                    code="SEC-001",
                    message="危険なパス",
                    file_path=".git/config",
                ),
                ReviewIssue(
                    level="warning",
                    code="TEST-001",
                    message="意味のないアサーション",
                    file_path="tests/test.py",
                    line_no=10,
                ),
            ],
        )
        summary = result.summary()
        assert "decision=reject" in summary
        assert "SEC-001" in summary
        assert "TEST-001" in summary
        assert ".git/config" in summary
        assert "tests/test.py:10" in summary

    def test_parse_unified_diff_simple(self):
        56+        """シンプルな unified diff のパース"""
        diff = """+++ b/src/example.py
@@ -0,0 +1,2 @@
+def hello():
+    return "world"
"""
        reviewer = GuardianAutoReviewer(project_name="nexuscore")
        files = reviewer._parse_unified_diff(diff)
        assert len(files) == 1
        assert files[0].path == "src/example.py"
        assert len(files[0].hunks) == 1
        assert files[0].hunks[0].new_start == 1
        assert files[0].hunks[0].new_lines == 2

    def test_parse_unified_diff_multiple_files(self):
        71+        """複数ファイルの unified diff のパース"""
        diff = """+++ b/src/file1.py
@@ -0,0 +1,1 @@
+content1
+++ b/src/file2.py
@@ -0,0 +1,1 @@
+content2
"""
        reviewer = GuardianAutoReviewer(project_name="nexuscore")
        files = reviewer._parse_unified_diff(diff)
        assert len(files) == 2
        assert files[0].path == "src/file1.py"
        assert files[1].path == "src/file2.py
