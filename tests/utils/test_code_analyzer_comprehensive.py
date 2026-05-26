"""
Comprehensive tests for code_analyzer module.
Covers all functions, data classes, and edge cases.
"""

import json
from unittest.mock import Mock, patch

from nexuscore.utils.code_analyzer import (
    QualityReport,
    SecurityIssue,
    _generate_feedback,
    _parse_bandit_issues,
    analyze_code_quality,
    run_bandit,
    run_mypy,
    run_pylint,
    run_pytest_cov,
)

# ==============================================================================
# Data Class Tests
# ==============================================================================


class TestSecurityIssue:
    """Test SecurityIssue dataclass"""

    def test_security_issue_creation(self):
        """SecurityIssue can be created with all fields"""
        issue = SecurityIssue(
            severity="HIGH",
            confidence="MEDIUM",
            issue_text="SQL injection vulnerability",
            filename="app.py",
            line_number=42,
        )

        assert issue.severity == "HIGH"
        assert issue.confidence == "MEDIUM"
        assert issue.issue_text == "SQL injection vulnerability"
        assert issue.filename == "app.py"
        assert issue.line_number == 42

    def test_security_issue_defaults(self):
        """SecurityIssue can be created with minimal fields"""
        issue = SecurityIssue(
            severity="LOW", confidence="LOW", issue_text="Test", filename="test.py", line_number=1
        )

        assert issue is not None


class TestQualityReport:
    """Test QualityReport dataclass"""

    def test_quality_report_creation_success(self):
        """QualityReport can be created for passing checks"""
        report = QualityReport(
            passed=True,
            coverage_percentage=95.0,
            coverage_passed=True,
            pylint_score=9.5,
            pylint_passed=True,
            mypy_passed=True,
            mypy_output="Success: no issues found",
            bandit_passed=True,
        )

        assert report.passed is True
        assert report.coverage_percentage == 95.0
        assert report.pylint_score == 9.5
        assert len(report.security_issues) == 0
        assert len(report.violations) == 0

    def test_quality_report_creation_failure(self):
        """QualityReport can be created for failing checks"""
        issues = [SecurityIssue("HIGH", "HIGH", "Test", "app.py", 1)]
        violations = ["Coverage too low", "Pylint score too low"]

        report = QualityReport(
            passed=False,
            coverage_percentage=50.0,
            coverage_passed=False,
            pylint_score=5.0,
            pylint_passed=False,
            mypy_passed=False,
            mypy_output="Error: type mismatch",
            bandit_passed=False,
            security_issues=issues,
            violations=violations,
            feedback="Fix these issues",
        )

        assert report.passed is False
        assert len(report.security_issues) == 1
        assert len(report.violations) == 2
        assert report.feedback == "Fix these issues"

    def test_quality_report_to_dict(self):
        """QualityReport.to_dict() returns correct dictionary"""
        report = QualityReport(
            passed=True,
            coverage_percentage=85.5,
            coverage_passed=True,
            pylint_score=8.8,
            pylint_passed=True,
            mypy_passed=True,
            mypy_output="Success",
            bandit_passed=True,
            violations=["test violation"],
        )

        result = report.to_dict()

        assert result["passed"] is True
        assert result["coverage"]["percentage"] == 85.5
        assert result["coverage"]["passed"] is True
        assert result["pylint"]["score"] == 8.8
        assert result["pylint"]["passed"] is True
        assert result["mypy"]["passed"] is True
        assert result["mypy"]["output"] == "Success"
        assert result["bandit"]["passed"] is True
        assert result["bandit"]["issues_count"] == 0
        assert result["violations_count"] == 1


# ==============================================================================
# Individual Tool Function Tests
# ==============================================================================


class TestRunPylint:
    """Test run_pylint function"""

    @patch("subprocess.run")
    def test_run_pylint_success(self, mock_run):
        """run_pylint returns score when successful"""
        mock_run.return_value = Mock(stdout="Your code has been rated at 8.50/10", returncode=0)

        score = run_pylint("test.py")

        assert score == 8.50
        mock_run.assert_called_once_with(
            ["pylint", "test.py"], capture_output=True, text=True, encoding="utf-8"
        )

    @patch("subprocess.run")
    def test_run_pylint_perfect_score(self, mock_run):
        """run_pylint handles perfect 10/10 score"""
        mock_run.return_value = Mock(stdout="Your code has been rated at 10.00/10", returncode=0)

        score = run_pylint("perfect.py")

        assert score == 10.00

    @patch("subprocess.run")
    def test_run_pylint_low_score(self, mock_run):
        """run_pylint handles low scores"""
        mock_run.return_value = Mock(stdout="Your code has been rated at 2.35/10", returncode=0)

        score = run_pylint("bad.py")

        assert score == 2.35

    @patch("subprocess.run")
    def test_run_pylint_no_score_found(self, mock_run):
        """run_pylint returns 0.0 when score not found"""
        mock_run.return_value = Mock(stdout="Some other output without score", returncode=0)

        score = run_pylint("test.py")

        assert score == 0.0

    @patch("subprocess.run")
    def test_run_pylint_exception(self, mock_run):
        """run_pylint returns 0.0 on exception"""
        mock_run.side_effect = RuntimeError("Command failed")

        score = run_pylint("test.py")

        assert score == 0.0


class TestRunMypy:
    """Test run_mypy function"""

    @patch("subprocess.run")
    def test_run_mypy_success(self, mock_run):
        """run_mypy returns True when no issues found"""
        mock_run.return_value = Mock(
            stdout="Success: no issues found in 1 source file", stderr="", returncode=0
        )

        passed, output = run_mypy("test.py")

        assert passed is True
        assert output == "Passed"
        mock_run.assert_called_once_with(
            ["mypy", "test.py"], capture_output=True, text=True, encoding="utf-8"
        )

    @patch("subprocess.run")
    def test_run_mypy_with_errors(self, mock_run):
        """run_mypy returns False and error messages when issues found"""
        error_output = """test.py:10: error: Incompatible types
test.py:20: error: Name not defined"""

        mock_run.return_value = Mock(stdout=error_output, stderr="", returncode=1)

        passed, output = run_mypy("test.py")

        assert passed is False
        assert "error: Incompatible types" in output
        assert "error: Name not defined" in output

    @patch("subprocess.run")
    def test_run_mypy_with_stderr(self, mock_run):
        """run_mypy includes stderr in output"""
        mock_run.return_value = Mock(
            stdout="", stderr="test.py:5: error: Import error", returncode=1
        )

        passed, output = run_mypy("test.py")

        assert passed is False
        assert "error: Import error" in output

    @patch("subprocess.run")
    def test_run_mypy_exception(self, mock_run):
        """run_mypy returns False with exception message on error"""
        mock_run.side_effect = RuntimeError("MyPy not installed")

        passed, output = run_mypy("test.py")

        assert passed is False
        assert "MyPy not installed" in output


class TestRunBandit:
    """Test run_bandit function"""

    @patch("subprocess.run")
    def test_run_bandit_no_issues(self, mock_run):
        """run_bandit returns True when no issues found"""
        bandit_output = {"results": []}

        mock_run.return_value = Mock(stdout=json.dumps(bandit_output), returncode=0)

        passed, issues = run_bandit("src/")

        assert passed is True
        assert issues == []
        mock_run.assert_called_once_with(
            ["bandit", "-r", "src/", "-f", "json"], capture_output=True, text=True, encoding="utf-8"
        )

    @patch("subprocess.run")
    def test_run_bandit_with_high_severity(self, mock_run):
        """run_bandit detects HIGH severity issues"""
        bandit_output = {
            "results": [
                {
                    "issue_severity": "HIGH",
                    "issue_confidence": "HIGH",
                    "issue_text": "Use of exec detected",
                    "filename": "app.py",
                    "line_number": 42,
                }
            ]
        }

        mock_run.return_value = Mock(stdout=json.dumps(bandit_output), returncode=1)

        passed, issues = run_bandit("src/")

        assert passed is False
        assert len(issues) == 1
        assert issues[0]["issue_severity"] == "HIGH"

    @patch("subprocess.run")
    def test_run_bandit_with_medium_severity(self, mock_run):
        """run_bandit detects MEDIUM severity issues"""
        bandit_output = {
            "results": [
                {
                    "issue_severity": "MEDIUM",
                    "issue_confidence": "MEDIUM",
                    "issue_text": "Hardcoded password",
                    "filename": "config.py",
                    "line_number": 10,
                }
            ]
        }

        mock_run.return_value = Mock(stdout=json.dumps(bandit_output), returncode=1)

        passed, issues = run_bandit("src/")

        assert passed is False
        assert len(issues) == 1

    @patch("subprocess.run")
    def test_run_bandit_ignores_low_severity(self, mock_run):
        """run_bandit ignores LOW severity issues"""
        bandit_output = {
            "results": [
                {
                    "issue_severity": "LOW",
                    "issue_confidence": "LOW",
                    "issue_text": "Minor issue",
                    "filename": "util.py",
                    "line_number": 5,
                }
            ]
        }

        mock_run.return_value = Mock(stdout=json.dumps(bandit_output), returncode=0)

        passed, issues = run_bandit("src/")

        assert passed is True
        assert issues == []

    @patch("subprocess.run")
    def test_run_bandit_json_decode_error(self, mock_run):
        """run_bandit handles JSON decode errors gracefully"""
        mock_run.return_value = Mock(stdout="Invalid JSON output", returncode=0)

        passed, issues = run_bandit("src/")

        assert passed is True
        assert issues == []

    @patch("subprocess.run")
    def test_run_bandit_exception(self, mock_run):
        """run_bandit returns False on exception"""
        mock_run.side_effect = RuntimeError("Bandit not installed")

        passed, issues = run_bandit("src/")

        assert passed is False
        assert issues == []


class TestRunPytestCov:
    """Test run_pytest_cov function"""

    @patch("subprocess.run")
    def test_run_pytest_cov_success(self, mock_run):
        """run_pytest_cov returns coverage percentage"""
        output = """
============ test session starts ============
collected 50 items

tests/test_app.py ........ PASSED [100%]

----------- coverage: platform linux -----------
Name                Stmts   Miss  Cover
---------------------------------------
src/app.py           100     15    85%
TOTAL                100     15    85%
"""

        mock_run.return_value = Mock(stdout=output, returncode=0)

        coverage = run_pytest_cov("/project/path")

        assert coverage == 85.0
        mock_run.assert_called_once_with(
            ["pytest"], cwd="/project/path", capture_output=True, text=True, encoding="utf-8"
        )

    @patch("subprocess.run")
    def test_run_pytest_cov_100_percent(self, mock_run):
        """run_pytest_cov handles 100% coverage"""
        output = "TOTAL  100  0  100%"

        mock_run.return_value = Mock(stdout=output, returncode=0)

        coverage = run_pytest_cov("/project/path")

        assert coverage == 100.0

    @patch("subprocess.run")
    def test_run_pytest_cov_zero_percent(self, mock_run):
        """run_pytest_cov handles 0% coverage"""
        output = "TOTAL  100  100  0%"

        mock_run.return_value = Mock(stdout=output, returncode=0)

        coverage = run_pytest_cov("/project/path")

        assert coverage == 0.0

    @patch("subprocess.run")
    def test_run_pytest_cov_no_match(self, mock_run):
        """run_pytest_cov returns 0.0 when no match found"""
        mock_run.return_value = Mock(stdout="No coverage information", returncode=0)

        coverage = run_pytest_cov("/project/path")

        assert coverage == 0.0

    @patch("subprocess.run")
    def test_run_pytest_cov_exception(self, mock_run):
        """run_pytest_cov returns 0.0 on exception"""
        mock_run.side_effect = RuntimeError("Pytest not found")

        coverage = run_pytest_cov("/project/path")

        assert coverage == 0.0


# ==============================================================================
# Helper Function Tests
# ==============================================================================


class TestParseBanditIssues:
    """Test _parse_bandit_issues function"""

    def test_parse_high_severity_issues(self):
        """_parse_bandit_issues filters HIGH severity"""
        issues = [
            {
                "issue_severity": "HIGH",
                "issue_confidence": "HIGH",
                "issue_text": "SQL injection",
                "filename": "db.py",
                "line_number": 100,
            }
        ]

        result = _parse_bandit_issues(issues, "MEDIUM")

        assert len(result) == 1
        assert result[0].severity == "HIGH"
        assert result[0].issue_text == "SQL injection"

    def test_parse_medium_severity_issues(self):
        """_parse_bandit_issues filters MEDIUM severity"""
        issues = [
            {
                "issue_severity": "MEDIUM",
                "issue_confidence": "MEDIUM",
                "issue_text": "Weak crypto",
                "filename": "crypto.py",
                "line_number": 50,
            }
        ]

        result = _parse_bandit_issues(issues, "MEDIUM")

        assert len(result) == 1
        assert result[0].severity == "MEDIUM"

    def test_parse_ignores_low_severity(self):
        """_parse_bandit_issues ignores LOW severity when max is MEDIUM"""
        issues = [
            {
                "issue_severity": "LOW",
                "issue_confidence": "LOW",
                "issue_text": "Minor issue",
                "filename": "util.py",
                "line_number": 10,
            }
        ]

        result = _parse_bandit_issues(issues, "MEDIUM")

        assert len(result) == 0

    def test_parse_mixed_severity(self):
        """_parse_bandit_issues correctly filters mixed severities"""
        issues = [
            {
                "issue_severity": "HIGH",
                "issue_confidence": "HIGH",
                "issue_text": "High",
                "filename": "a.py",
                "line_number": 1,
            },
            {
                "issue_severity": "MEDIUM",
                "issue_confidence": "MEDIUM",
                "issue_text": "Medium",
                "filename": "b.py",
                "line_number": 2,
            },
            {
                "issue_severity": "LOW",
                "issue_confidence": "LOW",
                "issue_text": "Low",
                "filename": "c.py",
                "line_number": 3,
            },
        ]

        result = _parse_bandit_issues(issues, "MEDIUM")

        assert len(result) == 2  # HIGH and MEDIUM only
        assert result[0].severity == "HIGH"
        assert result[1].severity == "MEDIUM"

    def test_parse_empty_list(self):
        """_parse_bandit_issues handles empty list"""
        result = _parse_bandit_issues([], "MEDIUM")

        assert len(result) == 0


class TestGenerateFeedback:
    """Test _generate_feedback function"""

    def test_generate_feedback_no_violations(self):
        """_generate_feedback returns success message when no violations"""
        feedback = _generate_feedback([], "src/app.py")

        assert "全ての品質チェックに合格しました" in feedback

    def test_generate_feedback_coverage_violation(self):
        """_generate_feedback includes test suggestion for coverage"""
        violations = ["テストカバレッジ不足: 50.0% < 90%"]

        feedback = _generate_feedback(violations, "src/app.py")

        assert "カバレッジ" in feedback or "テストケースを追加" in feedback
        assert "1." in feedback

    def test_generate_feedback_pylint_violation(self):
        """_generate_feedback includes Pylint suggestions"""
        violations = ["Pylintスコア不足: 6.0/10 < 8.0/10"]

        feedback = _generate_feedback(violations, "src/app.py")

        assert "Pylint" in feedback or "複雑度を下げる" in feedback or "命名規則" in feedback

    def test_generate_feedback_mypy_violation(self):
        """_generate_feedback includes MyPy suggestions"""
        violations = ["MyPy型チェック失敗:\nError: type mismatch"]

        feedback = _generate_feedback(violations, "src/app.py")

        assert "MyPy" in feedback or "型アノテーション" in feedback

    def test_generate_feedback_security_violation(self):
        """_generate_feedback includes security suggestions"""
        violations = ["セキュリティ問題検出: 2件のMEDIUM以上の脆弱性"]

        feedback = _generate_feedback(violations, "src/app.py")

        assert "セキュリティ" in feedback or "安全でない関数" in feedback

    def test_generate_feedback_multiple_violations(self):
        """_generate_feedback handles multiple violations"""
        violations = ["テストカバレッジ不足: 50%", "Pylintスコア不足: 6.0", "MyPy型チェック失敗"]

        feedback = _generate_feedback(violations, "src/app.py")

        assert "3件の問題" in feedback
        assert "1." in feedback
        assert "2." in feedback
        assert "3." in feedback


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestAnalyzeCodeQuality:
    """Test analyze_code_quality integration function"""

    @patch("nexuscore.utils.code_analyzer.run_pytest_cov")
    @patch("nexuscore.utils.code_analyzer.run_pylint")
    @patch("nexuscore.utils.code_analyzer.run_mypy")
    @patch("nexuscore.utils.code_analyzer.run_bandit")
    def test_analyze_code_quality_all_pass(self, mock_bandit, mock_mypy, mock_pylint, mock_cov):
        """analyze_code_quality returns passing report when all checks pass"""
        mock_cov.return_value = 95.0
        mock_pylint.return_value = 9.5
        mock_mypy.return_value = (True, "Success")
        mock_bandit.return_value = (True, [])

        constitution = {
            "quality_gates": {
                "tier1": {
                    "test_coverage_min": 90,
                    "pylint_score_min": 8.0,
                    "bandit_severity_max": "MEDIUM",
                }
            }
        }

        report = analyze_code_quality("src/app.py", "tests/test_app.py", constitution)

        assert report.passed is True
        assert report.coverage_percentage == 95.0
        assert report.pylint_score == 9.5
        assert report.mypy_passed is True
        assert report.bandit_passed is True
        assert len(report.violations) == 0

    @patch("nexuscore.utils.code_analyzer.run_pytest_cov")
    @patch("nexuscore.utils.code_analyzer.run_pylint")
    @patch("nexuscore.utils.code_analyzer.run_mypy")
    @patch("nexuscore.utils.code_analyzer.run_bandit")
    def test_analyze_code_quality_coverage_fail(
        self, mock_bandit, mock_mypy, mock_pylint, mock_cov
    ):
        """analyze_code_quality detects coverage failures"""
        mock_cov.return_value = 50.0  # Below threshold
        mock_pylint.return_value = 9.0
        mock_mypy.return_value = (True, "Success")
        mock_bandit.return_value = (True, [])

        constitution = {
            "quality_gates": {"tier1": {"test_coverage_min": 90, "pylint_score_min": 8.0}}
        }

        report = analyze_code_quality("src/app.py", "tests/test_app.py", constitution)

        assert report.passed is False
        assert report.coverage_passed is False
        assert len(report.violations) >= 1
        assert any("カバレッジ" in v for v in report.violations)

    @patch("nexuscore.utils.code_analyzer.run_pytest_cov")
    @patch("nexuscore.utils.code_analyzer.run_pylint")
    @patch("nexuscore.utils.code_analyzer.run_mypy")
    @patch("nexuscore.utils.code_analyzer.run_bandit")
    def test_analyze_code_quality_pylint_fail(self, mock_bandit, mock_mypy, mock_pylint, mock_cov):
        """analyze_code_quality detects Pylint failures"""
        mock_cov.return_value = 95.0
        mock_pylint.return_value = 6.0  # Below threshold
        mock_mypy.return_value = (True, "Success")
        mock_bandit.return_value = (True, [])

        constitution = {
            "quality_gates": {"tier1": {"test_coverage_min": 90, "pylint_score_min": 8.0}}
        }

        report = analyze_code_quality("src/app.py", "tests/test_app.py", constitution)

        assert report.passed is False
        assert report.pylint_passed is False
        assert any("Pylint" in v for v in report.violations)

    @patch("nexuscore.utils.code_analyzer.run_pytest_cov")
    @patch("nexuscore.utils.code_analyzer.run_pylint")
    @patch("nexuscore.utils.code_analyzer.run_mypy")
    @patch("nexuscore.utils.code_analyzer.run_bandit")
    def test_analyze_code_quality_mypy_fail(self, mock_bandit, mock_mypy, mock_pylint, mock_cov):
        """analyze_code_quality detects MyPy failures"""
        mock_cov.return_value = 95.0
        mock_pylint.return_value = 9.0
        mock_mypy.return_value = (False, "Type errors found")
        mock_bandit.return_value = (True, [])

        constitution = {
            "quality_gates": {"tier1": {"test_coverage_min": 90, "pylint_score_min": 8.0}}
        }

        report = analyze_code_quality("src/app.py", "tests/test_app.py", constitution)

        assert report.passed is False
        assert report.mypy_passed is False
        assert any("MyPy" in v for v in report.violations)

    @patch("nexuscore.utils.code_analyzer.run_pytest_cov")
    @patch("nexuscore.utils.code_analyzer.run_pylint")
    @patch("nexuscore.utils.code_analyzer.run_mypy")
    @patch("nexuscore.utils.code_analyzer.run_bandit")
    @patch("nexuscore.utils.code_analyzer._parse_bandit_issues")
    def test_analyze_code_quality_bandit_fail(
        self, mock_parse, mock_bandit, mock_mypy, mock_pylint, mock_cov
    ):
        """analyze_code_quality detects Bandit security issues"""
        mock_cov.return_value = 95.0
        mock_pylint.return_value = 9.0
        mock_mypy.return_value = (True, "Success")
        mock_bandit.return_value = (False, [{"issue_severity": "HIGH"}])
        mock_parse.return_value = [SecurityIssue("HIGH", "HIGH", "SQL injection", "app.py", 10)]

        constitution = {
            "quality_gates": {
                "tier1": {
                    "test_coverage_min": 90,
                    "pylint_score_min": 8.0,
                    "bandit_severity_max": "MEDIUM",
                }
            }
        }

        report = analyze_code_quality("src/app.py", "tests/test_app.py", constitution)

        assert report.passed is False
        assert report.bandit_passed is False
        assert len(report.security_issues) == 1
        assert any("セキュリティ" in v for v in report.violations)

    @patch("nexuscore.utils.code_analyzer.run_pytest_cov")
    @patch("nexuscore.utils.code_analyzer.run_pylint")
    @patch("nexuscore.utils.code_analyzer.run_mypy")
    @patch("nexuscore.utils.code_analyzer.run_bandit")
    def test_analyze_code_quality_all_fail(self, mock_bandit, mock_mypy, mock_pylint, mock_cov):
        """analyze_code_quality handles all checks failing"""
        mock_cov.return_value = 40.0
        mock_pylint.return_value = 4.0
        mock_mypy.return_value = (False, "Many errors")
        mock_bandit.return_value = (False, [{"issue_severity": "HIGH"}])

        constitution = {
            "quality_gates": {"tier1": {"test_coverage_min": 90, "pylint_score_min": 8.0}}
        }

        report = analyze_code_quality("src/app.py", "tests/test_app.py", constitution)

        assert report.passed is False
        assert len(report.violations) >= 4  # All checks failed

    @patch("nexuscore.utils.code_analyzer.run_pytest_cov")
    @patch("nexuscore.utils.code_analyzer.run_pylint")
    @patch("nexuscore.utils.code_analyzer.run_mypy")
    @patch("nexuscore.utils.code_analyzer.run_bandit")
    def test_analyze_code_quality_custom_thresholds(
        self, mock_bandit, mock_mypy, mock_pylint, mock_cov
    ):
        """analyze_code_quality respects custom constitution thresholds"""
        mock_cov.return_value = 85.0
        mock_pylint.return_value = 9.0
        mock_mypy.return_value = (True, "Success")
        mock_bandit.return_value = (True, [])

        # Strict thresholds
        constitution = {
            "quality_gates": {
                "tier1": {
                    "test_coverage_min": 95,  # Higher than actual
                    "pylint_score_min": 9.5,  # Higher than actual
                }
            }
        }

        report = analyze_code_quality("src/app.py", "tests/test_app.py", constitution)

        assert report.passed is False
        assert report.coverage_passed is False
        assert report.pylint_passed is False
