# src/utils/code_analyzer.py

import json
import logging
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)

# ==============================================================================
# Data Classes
# ==============================================================================


@dataclass
class SecurityIssue:
    """Banditで検出されたセキュリティ問題"""

    severity: str  # "HIGH", "MEDIUM", "LOW"
    confidence: str  # "HIGH", "MEDIUM", "LOW"
    issue_text: str
    filename: str
    line_number: int


@dataclass
class QualityReport:
    """Tier 1 品質ゲートの結果レポート"""

    # 総合結果
    passed: bool

    # カバレッジ
    coverage_percentage: float
    coverage_passed: bool

    # Pylint
    pylint_score: float
    pylint_passed: bool

    # MyPy
    mypy_passed: bool
    mypy_output: str

    # Bandit
    bandit_passed: bool
    security_issues: list[SecurityIssue] = field(default_factory=list)

    # フィードバック
    feedback: str = ""
    violations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """辞書形式に変換（ログ出力用）"""
        return {
            "passed": self.passed,
            "coverage": {"percentage": self.coverage_percentage, "passed": self.coverage_passed},
            "pylint": {"score": self.pylint_score, "passed": self.pylint_passed},
            "mypy": {"passed": self.mypy_passed, "output": self.mypy_output},
            "bandit": {"passed": self.bandit_passed, "issues_count": len(self.security_issues)},
            "violations_count": len(self.violations),
        }


# ==============================================================================
# Individual Tool Functions
# ==============================================================================


def run_pylint(file_path: str) -> float:
    """指定されたファイルに対してPylintを実行し、スコアを返す"""
    _logger.info("Running Pylint on %s...", file_path)
    command = ["pylint", file_path]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        output = result.stdout
        match = re.search(r"Your code has been rated at (\d+\.\d+)/10", output)
        if match:
            score = float(match.group(1))
            _logger.info("Pylint score: %s/10", score)
            return score
        _logger.warning("Pylint score not found in output.")
        return 0.0
    except (OSError, subprocess.SubprocessError, RuntimeError) as e:
        _logger.error("An error occurred while running Pylint: %s", e)
        return 0.0


def run_mypy(file_path: str) -> tuple[bool, str]:
    """指定されたファイルに対してMyPyを実行し、(成功フラグ, 結果メッセージ)を返す"""
    _logger.info("Running MyPy on %s...", file_path)
    command = ["mypy", file_path]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        output = result.stdout + result.stderr
        if "Success: no issues found" in output:
            _logger.info("MyPy found no issues.")
            return True, "Passed"
        else:
            error_summary = "\n".join(line for line in output.splitlines() if "error:" in line)
            _logger.error("MyPy found issues.")
            return False, error_summary
    except (OSError, subprocess.SubprocessError, RuntimeError) as e:
        _logger.error("An error occurred while running MyPy: %s", e)
        return False, str(e)


def run_bandit(target_path: str) -> tuple[bool, list[dict[str, Any]]]:
    """
    指定されたパスに対してBanditを実行し、(成功フラグ, 問題リスト)を返す

    Returns:
        tuple[bool, List[Dict]]: (合格フラグ, 問題の辞書リスト)
    """
    _logger.info("Running Bandit security scan on %s...", target_path)
    command = ["bandit", "-r", target_path, "-f", "json"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        report = json.loads(result.stdout)
        issues = report.get("results", [])

        high_medium_issues = [
            issue for issue in issues if issue["issue_severity"] in ["HIGH", "MEDIUM"]
        ]

        if not high_medium_issues:
            _logger.info("Bandit: No high or medium severity issues found.")
            return True, []
        else:
            _logger.error("Bandit found %d security issues.", len(high_medium_issues))
            return False, high_medium_issues

    except json.JSONDecodeError:
        _logger.info("Bandit: No security issues reported.")
        return True, []
    except (OSError, subprocess.SubprocessError, RuntimeError) as e:
        _logger.error("An error occurred while running Bandit: %s", e)
        return False, []


def run_pytest_cov(project_path: str) -> float:
    """
    指定されたプロジェクトパスを基準にテストとカバレッジ計測を実行する。
    設定はpyproject.tomlから読み込まれる。
    """
    _logger.info("Running pytest-cov on %s...", project_path)
    # 設定ファイルがあるので、コマンドはシンプルに 'pytest' だけで良い
    command = ["pytest"]
    try:
        # cwdを指定して、対象プロジェクトのルートでコマンドを実行する
        result = subprocess.run(
            command,
            cwd=project_path,  # これが重要！
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        output = result.stdout
        match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", output)
        if match:
            coverage = float(match.group(1))
            _logger.info("Pytest-cov coverage: %s%%", coverage)
            return coverage
        _logger.warning("Pytest-cov coverage not found. Output:\n%s", output)
        return 0.0
    except (OSError, subprocess.SubprocessError, RuntimeError) as e:
        _logger.error("An error occurred while running pytest-cov: %s", e)
        return 0.0


# ==============================================================================
# Integrated Quality Analysis
# ==============================================================================


def analyze_code_quality(
    source_path: str,
    test_path: str,
    constitution: dict[str, Any],
    project_root: str | None = None,
) -> QualityReport:
    """
    Tier 1 品質ゲートを実行し、憲法に基づいて合否判定。

    Args:
        source_path: ソースコードのパス (ファイルまたはディレクトリ)
        test_path: テストコードのパス
        constitution: 品質基準を定義した辞書
        project_root: プロジェクトルート (pytest実行用)

    Returns:
        QualityReport: 詳細な検査結果
    """
    # Step 1: 憲法から基準値を抽出
    tier1_config = constitution.get("quality_gates", {}).get("tier1", {})
    min_coverage = tier1_config.get("test_coverage_min", 90)
    min_pylint = tier1_config.get("pylint_score_min", 8.0)
    max_severity = tier1_config.get("bandit_severity_max", "MEDIUM")

    _logger.info("品質ゲート開始: Coverage≥%s%%, Pylint≥%s", min_coverage, min_pylint)

    violations = []

    # Step 2: カバレッジ測定
    if project_root is None:
        project_root = str(Path(source_path).parent)

    coverage = run_pytest_cov(project_root)
    coverage_passed = coverage >= min_coverage
    if not coverage_passed:
        violations.append(f"テストカバレッジ不足: {coverage:.1f}% < {min_coverage}% (最低基準)")

    # Step 3: Pylint実行
    pylint_score = run_pylint(source_path)
    pylint_passed = pylint_score >= min_pylint
    if not pylint_passed:
        violations.append(f"Pylintスコア不足: {pylint_score:.1f}/10 < {min_pylint}/10 (最低基準)")

    # Step 4: MyPy実行
    mypy_passed, mypy_output = run_mypy(source_path)
    if not mypy_passed:
        violations.append(f"MyPy型チェック失敗:\n{mypy_output}")

    # Step 5: Bandit実行
    bandit_passed, bandit_issues = run_bandit(source_path)
    security_issues = _parse_bandit_issues(bandit_issues, max_severity)
    if not bandit_passed:
        violations.append(
            f"セキュリティ問題検出: {len(security_issues)}件の{max_severity}以上の脆弱性"
        )

    # Step 6: 総合判定
    all_passed = coverage_passed and pylint_passed and mypy_passed and bandit_passed

    # Step 7: フィードバック生成
    feedback = _generate_feedback(violations, source_path)

    return QualityReport(
        passed=all_passed,
        coverage_percentage=coverage,
        coverage_passed=coverage_passed,
        pylint_score=pylint_score,
        pylint_passed=pylint_passed,
        mypy_passed=mypy_passed,
        mypy_output=mypy_output,
        bandit_passed=bandit_passed,
        security_issues=security_issues,
        feedback=feedback,
        violations=violations,
    )


def _parse_bandit_issues(
    bandit_issues: list[dict[str, Any]], max_severity: str
) -> list[SecurityIssue]:
    """Bandit問題リストをSecurityIssueオブジェクトに変換"""
    severity_levels = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    max_level = severity_levels.get(max_severity, 2)

    issues = []
    for issue in bandit_issues:
        severity = issue.get("issue_severity", "UNKNOWN")
        if severity_levels.get(severity, 0) >= max_level:
            issues.append(
                SecurityIssue(
                    severity=severity,
                    confidence=issue.get("issue_confidence", "UNKNOWN"),
                    issue_text=issue.get("issue_text", ""),
                    filename=issue.get("filename", ""),
                    line_number=issue.get("line_number", 0),
                )
            )

    return issues


def _generate_feedback(violations: list[str], source_path: str) -> str:
    """
    CoderAgentへの具体的なフィードバックを生成

    フィードバック形式:
        品質ゲート不合格: X件の問題が見つかりました。

        1. [問題の種類]
           💡 提案: [修正方法]

        2. ...
    """
    if not violations:
        return "✅ 全ての品質チェックに合格しました。"

    feedback_lines = [f"❌ 品質ゲート不合格: {len(violations)}件の問題が見つかりました。\n"]

    for i, violation in enumerate(violations, 1):
        feedback_lines.append(f"{i}. {violation}")

        # 修正提案を追加
        if "カバレッジ" in violation:
            feedback_lines.append(
                "   💡 提案: テストケースを追加してください。"
                "特にエッジケースや例外処理のテストが不足している可能性があります。"
            )
        elif "Pylint" in violation:
            feedback_lines.append(
                "   💡 提案: コードの複雑度を下げるか、命名規則を見直してください。"
            )
        elif "MyPy" in violation:
            feedback_lines.append("   💡 提案: 型アノテーションを追加または修正してください。")
        elif "セキュリティ" in violation:
            feedback_lines.append(
                "   💡 提案: 安全でない関数（eval, exec等）の使用を避けてください。"
            )

        feedback_lines.append("")  # 空行

    return "\n".join(feedback_lines)
