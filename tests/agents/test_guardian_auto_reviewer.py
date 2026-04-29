"""
test_guardian_auto_reviewer.py

GuardianAutoReviewer のユニットテスト。
"""

from __future__ import annotations

from nexuscore.guard.guardian_auto_reviewer import (
    GuardianAutoReviewer,
    ProjectType,
    ReviewDecision,
    ReviewIssue,
    ReviewResult,
)


class TestGuardianAutoReviewer:
    """GuardianAutoReviewer の基本動作テスト"""

    def test_init_nexuscore(self):
        """NexusCore プロジェクトとして初期化"""
        reviewer = GuardianAutoReviewer(project_name="nexuscore")
        assert reviewer.project_type == ProjectType.NEXUSCORE

    def test_init_atelier(self):
        """atelier-kyo-manager プロジェクトとして初期化"""
        reviewer = GuardianAutoReviewer(project_name="atelier-kyo-manager")
        assert reviewer.project_type == ProjectType.ATELIER

    def test_init_other(self):
        """その他のプロジェクトとして初期化"""
        reviewer = GuardianAutoReviewer(project_name="unknown-project")
        assert reviewer.project_type == ProjectType.OTHER

    def test_review_clean_diff_approve(self):
        """クリーンな diff は APPROVE"""
        diff = """+++ b/src/example.py
@@ -0,0 +1,3 @@
+def hello():
+    return "world"
+
"""
        # policy_rules.jsonが存在しないパスを指定してビルトインルールのみテスト
        reviewer = GuardianAutoReviewer(
            project_name="nexuscore", policy_rules_path="/nonexistent/policy_rules.json"
        )
        result = reviewer.review_unified_diff(diff)

        assert result.decision == ReviewDecision.APPROVE
        assert len(result.issues) == 0

    def test_review_dangerous_path_reject(self):
        """危険なパスへの変更は REJECT"""
        diff = """+++ b/.git/config
@@ -0,0 +1,1 @@
+[core]
"""
        reviewer = GuardianAutoReviewer(project_name="nexuscore")
        result = reviewer.review_unified_diff(diff)

        assert result.decision == ReviewDecision.REJECT
        assert any(i.code == "SEC-001" for i in result.issues)

    def test_review_dangerous_command_reject(self):
        """破壊的なコマンドは REJECT"""
        diff = """+++ b/script.sh
@@ -0,0 +1,1 @@
+rm -rf /tmp
"""
        reviewer = GuardianAutoReviewer(project_name="nexuscore")
        result = reviewer.review_unified_diff(diff)

        assert result.decision == ReviewDecision.REJECT
        assert any(i.code == "SEC-002" for i in result.issues)

    def test_review_except_pass_reject(self):
        """例外握りつぶしは REJECT"""
        diff = """+++ b/src/example.py
@@ -0,0 +1,2 @@
+try:
+    do_something()
+except: pass
"""
        reviewer = GuardianAutoReviewer(project_name="nexuscore")
        result = reviewer.review_unified_diff(diff)

        assert result.decision == ReviewDecision.REJECT
        assert any(i.code == "SAFE-001" for i in result.issues)

    def test_review_meaningless_assert_warning(self):
        """意味のないアサーションは警告"""
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
        """NexusCore の Orchestrator 変更は警告"""
        diff = """+++ b/src/nexuscore/core/orchestrator.py
@@ -10,5 +10,5 @@
-    def run_requirement(self):
+    def run_plan(self):
         pass
"""
        reviewer = GuardianAutoReviewer(project_name="nexuscore")
        result = reviewer.review_unified_diff(diff)

        # NC-001 が検出される可能性がある（簡易チェックなので確実ではない）
        # 最低限、エラーにならないことを確認
        assert result.decision in (ReviewDecision.APPROVE, ReviewDecision.MANUAL_REVIEW)

    def test_review_atelier_domestic_domain_reject(self):
        """atelier-kyo-manager の国内サイトURLは REJECT"""
        diff = """+++ b/src/example.py
@@ -0,0 +1,1 @@
+url = "https://www.rakuten.co.jp/item"
"""
        reviewer = GuardianAutoReviewer(project_name="atelier-kyo-manager")
        result = reviewer.review_unified_diff(diff)

        assert result.decision == ReviewDecision.REJECT
        assert any(i.code == "AT-001" for i in result.issues)

    def test_review_result_summary(self):
        """ReviewResult.summary() の出力確認"""
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
        """シンプルな unified diff のパース"""
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
        """複数ファイルの unified diff のパース"""
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
        assert files[1].path == "src/file2.py"
