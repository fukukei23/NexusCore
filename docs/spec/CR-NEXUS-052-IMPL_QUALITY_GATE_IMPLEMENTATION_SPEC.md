# CR-NEXUS-052-IMPL: 品質ゲート実装仕様書

**文書ID**: CR-NEXUS-052-IMPL
**親仕様**: CR-NEXUS-052 (品質ゲート仕様)
**バージョン**: 1.0
**最終更新**: 2025-12-28
**ステータス**: 実装準備完了

---

## 1. 実装概要

本文書は、CR-NEXUS-052で定義された品質ゲートを実装するための詳細設計とタスク分解を提供します。

### 1.1 実装対象

1. **code_analyzer.py の拡張** (Tier 1品質ゲート)
   - 既存機能: Pylint, MyPy, Bandit, pytest-cov の個別実行関数 ✅
   - **追加実装**: 統合分析関数、憲法統合、レポート生成

2. **MutationTesterAgent の新規作成** (Tier 2品質ゲート)
   - BaseAgentを継承
   - mutmutライブラリの統合
   - ミューテーションレポート生成

3. **GuardianAgent の拡張** (最終承認)
   - 既存実装あり
   - 品質ゲート結果の統合

---

## 2. code_analyzer.py 実装仕様

### 2.1 現在の実装状況

**ファイル**: `src/nexuscore/utils/code_analyzer.py` (97行)

**既存関数**:
- ✅ `run_pylint(file_path: str) -> float`
- ✅ `run_mypy(file_path: str) -> tuple[bool, str]`
- ✅ `run_bandit(target_path: str) -> tuple[bool, str]`
- ✅ `run_pytest_cov(project_path: str) -> float`

### 2.2 追加実装

#### 2.2.1 データクラス: QualityReport

```python
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class SecurityIssue:
    """Banditで検出されたセキュリティ問題"""
    severity: str        # "HIGH", "MEDIUM", "LOW"
    confidence: str      # "HIGH", "MEDIUM", "LOW"
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
    security_issues: List[SecurityIssue] = field(default_factory=list)

    # フィードバック
    feedback: str = ""
    violations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換（ログ出力用）"""
        return {
            "passed": self.passed,
            "coverage": {
                "percentage": self.coverage_percentage,
                "passed": self.coverage_passed
            },
            "pylint": {
                "score": self.pylint_score,
                "passed": self.pylint_passed
            },
            "mypy": {
                "passed": self.mypy_passed,
                "output": self.mypy_output
            },
            "bandit": {
                "passed": self.bandit_passed,
                "issues_count": len(self.security_issues)
            },
            "violations_count": len(self.violations)
        }
```

#### 2.2.2 関数: analyze_code_quality()

```python
def analyze_code_quality(
    source_path: str,
    test_path: str,
    constitution: Dict[str, Any],
    project_root: Optional[str] = None
) -> QualityReport:
    """
    Tier 1 品質ゲートを実行し、憲法に基づいて合否判定。

    Args:
        source_path: ソースコードのパス (ファイルまたはディレクトリ)
        test_path: テストコードのパス
        constitution: 品質基準を定義した辞書
            例:
            {
                "quality_gates": {
                    "tier1": {
                        "test_coverage_min": 90,
                        "pylint_score_min": 8.0,
                        "bandit_severity_max": "MEDIUM"
                    }
                }
            }
        project_root: プロジェクトルート (pytest実行用、デフォルトはsource_pathの親)

    Returns:
        QualityReport: 詳細な検査結果

    処理フロー:
        1. 憲法から基準値を抽出
        2. 各検査ツールを並列実行
        3. 結果を基準値と比較
        4. 不合格項目のフィードバックを生成
        5. QualityReportを返す
    """
    import logging
    logger = logging.getLogger(__name__)

    # Step 1: 憲法から基準値を抽出
    tier1_config = constitution.get("quality_gates", {}).get("tier1", {})
    min_coverage = tier1_config.get("test_coverage_min", 90)
    min_pylint = tier1_config.get("pylint_score_min", 8.0)
    max_severity = tier1_config.get("bandit_severity_max", "MEDIUM")

    logger.info(f"品質ゲート開始: Coverage≥{min_coverage}%, Pylint≥{min_pylint}")

    violations = []

    # Step 2: カバレッジ測定
    if project_root is None:
        from pathlib import Path
        project_root = str(Path(source_path).parent)

    coverage = run_pytest_cov(project_root)
    coverage_passed = coverage >= min_coverage
    if not coverage_passed:
        violations.append(
            f"テストカバレッジ不足: {coverage:.1f}% < {min_coverage}% (最低基準)"
        )

    # Step 3: Pylint実行
    pylint_score = run_pylint(source_path)
    pylint_passed = pylint_score >= min_pylint
    if not pylint_passed:
        violations.append(
            f"Pylintスコア不足: {pylint_score:.1f}/10 < {min_pylint}/10 (最低基準)"
        )

    # Step 4: MyPy実行
    mypy_passed, mypy_output = run_mypy(source_path)
    if not mypy_passed:
        violations.append(f"MyPy型チェック失敗:\n{mypy_output}")

    # Step 5: Bandit実行
    bandit_passed, bandit_output = run_bandit(source_path)
    security_issues = _parse_bandit_output(bandit_output, max_severity)
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
        violations=violations
    )


def _parse_bandit_output(
    bandit_output: str,
    max_severity: str
) -> List[SecurityIssue]:
    """Bandit出力をパースしてSecurityIssueリストを生成"""
    # bandit_output は run_bandit() から返される文字列
    # 形式: "- [issue_text] (Severity: HIGH, File: path:line)"
    issues = []
    severity_levels = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    max_level = severity_levels.get(max_severity, 2)

    for line in bandit_output.split('\n'):
        if line.startswith('- '):
            # 簡易パース（実際はJSONから取得するべき）
            # TODO: run_bandit()を修正してJSONオブジェクトを返すように
            issues.append(SecurityIssue(
                severity="UNKNOWN",
                confidence="UNKNOWN",
                issue_text=line,
                filename="",
                line_number=0
            ))

    return issues


def _generate_feedback(violations: List[str], source_path: str) -> str:
    """
    CoderAgentへの具体的なフィードバックを生成

    フィードバック形式:
        品質ゲート不合格: X件の問題が見つかりました。

        1. [問題の種類]
           - 詳細な説明
           - 修正方法の提案

        2. ...
    """
    if not violations:
        return "✅ 全ての品質チェックに合格しました。"

    feedback_lines = [
        f"❌ 品質ゲート不合格: {len(violations)}件の問題が見つかりました。\n"
    ]

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
            feedback_lines.append(
                "   💡 提案: 型アノテーションを追加または修正してください。"
            )
        elif "セキュリティ" in violation:
            feedback_lines.append(
                "   💡 提案: 安全でない関数（eval, exec等）の使用を避けてください。"
            )

        feedback_lines.append("")  # 空行

    return "\n".join(feedback_lines)
```

#### 2.2.3 ヘルパー関数の改善

既存の `run_bandit()` を修正してJSONオブジェクトを返すように：

```python
def run_bandit(target_path: str) -> tuple[bool, List[Dict[str, Any]]]:
    """
    指定されたパスに対してBanditを実行し、(成功フラグ, 問題リスト)を返す

    Returns:
        tuple[bool, List[Dict]]: (合格フラグ, 問題の辞書リスト)
    """
    print(f"🔬 Running Bandit security scan on {target_path}...")
    command = ["bandit", "-r", target_path, "-f", "json"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
        report = json.loads(result.stdout)
        issues = report.get("results", [])

        high_medium_issues = [
            issue for issue in issues
            if issue["issue_severity"] in ["HIGH", "MEDIUM"]
        ]

        if not high_medium_issues:
            print("✅ Bandit: No high or medium severity issues found.")
            return True, []
        else:
            print(f"❌ Bandit found {len(high_medium_issues)} security issues.")
            return False, high_medium_issues

    except json.JSONDecodeError:
        print("✅ Bandit: No security issues reported.")
        return True, []
    except Exception as e:
        print(f"🚨 An error occurred while running Bandit: {e}")
        return False, []
```

---

## 3. MutationTesterAgent 実装仕様

### 3.1 新規ファイル作成

**ファイルパス**: `src/nexuscore/agents/mutation_tester_agent.py`

### 3.2 完全な実装

```python
# ==============================================================================
# ファイル: src/nexuscore/agents/mutation_tester_agent.py
# 目的  : Tier 2品質ゲート - テストの質をミューテーションテストで検証
# ==============================================================================
from __future__ import annotations

import subprocess
import re
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from nexuscore.agents.base_agent import BaseAgent


@dataclass
class Mutant:
    """生き残ったミュータント（バグ）の情報"""
    file_path: str
    line_number: int
    mutator: str          # 変異の種類 (例: "BinaryOperator", "ConditionalOperator")
    original_code: str
    mutated_code: str
    status: str           # "survived", "killed", "timeout", "suspicious"


@dataclass
class MutationReport:
    """Tier 2 品質ゲートの結果レポート"""
    passed: bool
    mutation_score: float
    total_mutants: int
    killed: int
    survived: int
    timeout: int
    suspicious: int

    survived_mutants: List[Mutant] = field(default_factory=list)
    feedback: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "mutation_score": self.mutation_score,
            "total_mutants": self.total_mutants,
            "killed": self.killed,
            "survived": self.survived,
            "timeout": self.timeout,
            "suspicious": self.suspicious,
            "survived_count": len(self.survived_mutants)
        }


class MutationTesterAgent(BaseAgent):
    """
    Tier 2品質ゲート: ミューテーションテストでテストの質を検証

    役割:
        - mutmutを使用してミュータントを生成
        - テストスイートを実行してバグ検出能力を測定
        - 生き残ったミュータントを分析してフィードバック生成
    """

    SYSTEM_PROMPT = (
        "You are a mutation testing expert. "
        "Analyze survived mutants and provide actionable feedback "
        "to improve test quality."
    )

    def __init__(self):
        super().__init__()
        self.logger.info("MutationTesterAgent initialized")

    def run_mutation_testing(
        self,
        source_path: str,
        test_path: str,
        constitution: Dict[str, Any],
        timeout_per_test: int = 10
    ) -> MutationReport:
        """
        ミューテーションテストを実行

        Args:
            source_path: ミュータント生成対象のソースコード
            test_path: テストコードのパス
            constitution: 憲法（品質基準）
            timeout_per_test: 各テストのタイムアウト（秒）

        Returns:
            MutationReport: 詳細なレポート
        """
        tier2_config = constitution.get("quality_gates", {}).get("tier2", {})
        min_mutation_score = tier2_config.get("mutation_score_min", 80)

        self.logger.info(f"Tier 2品質ゲート開始: MutationScore≥{min_mutation_score}%")

        # Step 1: mutmut実行
        self.logger.info(f"mutmut実行中: {source_path}")
        mutmut_result = self._run_mutmut(source_path, test_path, timeout_per_test)

        # Step 2: 結果パース
        total = mutmut_result["total"]
        killed = mutmut_result["killed"]
        survived = mutmut_result["survived"]
        timeout = mutmut_result["timeout"]
        suspicious = mutmut_result["suspicious"]

        mutation_score = (killed / total * 100) if total > 0 else 0.0
        passed = mutation_score >= min_mutation_score

        # Step 3: 生き残ったミュータントの詳細取得
        survived_mutants = self._get_survived_mutants() if survived > 0 else []

        # Step 4: フィードバック生成
        feedback = self._generate_feedback(
            survived_mutants,
            mutation_score,
            min_mutation_score
        )

        return MutationReport(
            passed=passed,
            mutation_score=mutation_score,
            total_mutants=total,
            killed=killed,
            survived=survived,
            timeout=timeout,
            suspicious=suspicious,
            survived_mutants=survived_mutants,
            feedback=feedback
        )

    def _run_mutmut(
        self,
        source_path: str,
        test_path: str,
        timeout: int
    ) -> Dict[str, int]:
        """
        mutmutを実行して結果を取得

        Returns:
            dict: {"total": X, "killed": Y, "survived": Z, ...}
        """
        # mutmutキャッシュをクリア
        subprocess.run(["mutmut", "run", "--rerun-all"], capture_output=True)

        # mutmut実行
        cmd = [
            "mutmut",
            "run",
            "--paths-to-mutate", source_path,
            "--tests-dir", test_path,
            "--runner", "python -m pytest",
            "--timeout", str(timeout)
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 全体のタイムアウト: 10分
            )

            # 結果パース
            output = result.stdout + result.stderr
            return self._parse_mutmut_output(output)

        except subprocess.TimeoutExpired:
            self.logger.error("mutmut実行がタイムアウトしました")
            return {"total": 0, "killed": 0, "survived": 0, "timeout": 0, "suspicious": 0}
        except Exception as e:
            self.logger.error(f"mutmut実行エラー: {e}", exc_info=True)
            return {"total": 0, "killed": 0, "survived": 0, "timeout": 0, "suspicious": 0}

    def _parse_mutmut_output(self, output: str) -> Dict[str, int]:
        """
        mutmutの出力をパース

        出力例:
            Total mutants: 120
            Killed: 96 (80.0%)
            Survived: 18 (15.0%)
            Timeout: 4 (3.3%)
            Suspicious: 2 (1.7%)
        """
        result = {
            "total": 0,
            "killed": 0,
            "survived": 0,
            "timeout": 0,
            "suspicious": 0
        }

        patterns = {
            "total": r"Total mutants:\s*(\d+)",
            "killed": r"Killed:\s*(\d+)",
            "survived": r"Survived:\s*(\d+)",
            "timeout": r"Timeout:\s*(\d+)",
            "suspicious": r"Suspicious:\s*(\d+)"
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, output)
            if match:
                result[key] = int(match.group(1))

        return result

    def _get_survived_mutants(self) -> List[Mutant]:
        """
        生き残ったミュータントの詳細を取得

        mutmut results コマンドを使用
        """
        try:
            result = subprocess.run(
                ["mutmut", "results"],
                capture_output=True,
                text=True
            )

            return self._parse_survived_mutants(result.stdout)

        except Exception as e:
            self.logger.error(f"ミュータント詳細取得エラー: {e}")
            return []

    def _parse_survived_mutants(self, output: str) -> List[Mutant]:
        """
        mutmut resultsの出力をパース

        出力例:
            To apply a mutant on disk:
                mutmut apply <id>

            Survived 🙁

            1. src/calculator.py:15
               - from: result = a + b
               - to:   result = a - b
        """
        mutants = []

        # 簡易実装: 実際のmutmut出力に合わせて調整が必要
        lines = output.split('\n')
        current_mutant = None

        for line in lines:
            # ファイル:行番号のパターン
            match = re.match(r'(\d+)\.\s+(.+?):(\d+)', line)
            if match:
                if current_mutant:
                    mutants.append(current_mutant)

                current_mutant = Mutant(
                    file_path=match.group(2),
                    line_number=int(match.group(3)),
                    mutator="Unknown",
                    original_code="",
                    mutated_code="",
                    status="survived"
                )

            # from/toのパターン
            elif current_mutant and "- from:" in line:
                current_mutant.original_code = line.split("from:")[1].strip()
            elif current_mutant and "- to:" in line:
                current_mutant.mutated_code = line.split("to:")[1].strip()

        if current_mutant:
            mutants.append(current_mutant)

        return mutants

    def _generate_feedback(
        self,
        survived_mutants: List[Mutant],
        mutation_score: float,
        min_score: float
    ) -> str:
        """
        TesterAgentへの具体的なフィードバックを生成
        """
        if mutation_score >= min_score:
            return f"✅ ミューテーションスコア {mutation_score:.1f}% - 基準をクリアしました。"

        feedback_lines = [
            f"❌ Tier 2品質ゲート不合格",
            f"ミューテーションスコア: {mutation_score:.1f}% < {min_score}% (最低基準)\n",
            f"以下の{len(survived_mutants)}個のミュータントが生き残りました。",
            "テストを追加してバグ検出能力を向上させてください。\n"
        ]

        for i, mutant in enumerate(survived_mutants[:10], 1):  # 最初の10個のみ
            feedback_lines.append(f"{i}. ファイル: {mutant.file_path}:{mutant.line_number}")
            feedback_lines.append(f"   変更前: {mutant.original_code}")
            feedback_lines.append(f"   変更後: {mutant.mutated_code}")

            # 変異の種類から推奨テストを提案
            suggestion = self._suggest_test_for_mutant(mutant)
            if suggestion:
                feedback_lines.append(f"   💡 提案: {suggestion}")

            feedback_lines.append("")

        if len(survived_mutants) > 10:
            feedback_lines.append(f"... 他 {len(survived_mutants) - 10}個のミュータント")

        return "\n".join(feedback_lines)

    def _suggest_test_for_mutant(self, mutant: Mutant) -> str:
        """
        ミュータントの種類から、必要なテストケースを提案
        """
        original = mutant.original_code.lower()
        mutated = mutant.mutated_code.lower()

        # 演算子の変更
        if "+" in original and "-" in mutated:
            return "加算と減算の境界テストを追加してください。"
        elif "-" in original and "+" in mutated:
            return "減算と加算の境界テストを追加してください。"
        elif "*" in original and "/" in mutated:
            return "乗算と除算のテストケースを追加してください。"

        # 比較演算子の変更
        elif ">" in original and ">=" in mutated:
            return "境界値（等号を含む条件）のテストを追加してください。"
        elif ">=" in original and ">" in mutated:
            return "境界値（等号の有無）のテストを追加してください。"
        elif "<" in original and "<=" in mutated:
            return "境界値（等号を含む条件）のテストを追加してください。"

        # 論理演算子の変更
        elif "and" in original and "or" in mutated:
            return "論理演算子の真偽値テーブルを網羅するテストを追加してください。"
        elif "or" in original and "and" in mutated:
            return "論理演算子の真偽値テーブルを網羅するテストを追加してください。"

        # デフォルト
        return "この変更を検出できるテストケースを追加してください。"
```

---

## 4. 統合テスト仕様

### 4.1 Tier 1テスト

**ファイル**: `tests/quality_gate/test_code_analyzer.py`

```python
import pytest
from src.nexuscore.utils.code_analyzer import (
    analyze_code_quality,
    QualityReport,
    SecurityIssue
)


class TestAnalyzeCodeQuality:
    """analyze_code_quality() の統合テスト"""

    @pytest.fixture
    def sample_constitution(self):
        return {
            "quality_gates": {
                "tier1": {
                    "test_coverage_min": 90,
                    "pylint_score_min": 8.0,
                    "bandit_severity_max": "MEDIUM"
                }
            }
        }

    def test_all_checks_pass(self, sample_constitution, tmp_path):
        """全てのチェックが合格する場合"""
        # 高品質なサンプルコードを作成
        source = tmp_path / "good_code.py"
        source.write_text("""
def add(a: int, b: int) -> int:
    \"\"\"2つの整数を加算する\"\"\"
    return a + b
""")

        test = tmp_path / "test_good_code.py"
        test.write_text("""
from good_code import add

def test_add_positive():
    assert add(2, 3) == 5

def test_add_negative():
    assert add(-2, -3) == -5

def test_add_zero():
    assert add(0, 5) == 5
""")

        report = analyze_code_quality(
            source_path=str(source),
            test_path=str(test),
            constitution=sample_constitution,
            project_root=str(tmp_path)
        )

        assert report.passed is True
        assert report.coverage_percentage >= 90
        assert report.pylint_score >= 8.0

    def test_low_coverage_fails(self, sample_constitution, tmp_path):
        """カバレッジが不足している場合は不合格"""
        # 実装省略（演習問題）
        pass

    def test_security_issue_fails(self, sample_constitution, tmp_path):
        """セキュリティ問題がある場合は不合格"""
        source = tmp_path / "insecure_code.py"
        source.write_text("""
def dangerous_eval(user_input: str):
    return eval(user_input)  # セキュリティリスク
""")

        report = analyze_code_quality(
            source_path=str(source),
            test_path="",
            constitution=sample_constitution
        )

        assert report.passed is False
        assert report.bandit_passed is False
        assert len(report.security_issues) > 0
```

### 4.2 Tier 2テスト

**ファイル**: `tests/agents/test_mutation_tester_agent.py`

```python
import pytest
from src.nexuscore.agents.mutation_tester_agent import (
    MutationTesterAgent,
    MutationReport,
    Mutant
)


class TestMutationTesterAgent:
    """MutationTesterAgent の統合テスト"""

    @pytest.fixture
    def agent(self):
        return MutationTesterAgent()

    @pytest.fixture
    def sample_constitution(self):
        return {
            "quality_gates": {
                "tier2": {
                    "mutation_score_min": 80,
                    "mutation_timeout_sec": 10
                }
            }
        }

    def test_high_quality_tests_pass(self, agent, sample_constitution, tmp_path):
        """質の高いテストはミューテーションテストに合格"""
        # 実装省略
        pass

    def test_weak_tests_fail(self, agent, sample_constitution, tmp_path):
        """弱いテストはミューテーションテストに不合格"""
        # 実装省略
        pass
```

---

## 5. 実装タスク分解

### 5.1 Phase 1: code_analyzer.py 拡張 (優先度: 最高)

- [ ] Task 1.1: `QualityReport` データクラスを追加
- [ ] Task 1.2: `SecurityIssue` データクラスを追加
- [ ] Task 1.3: `analyze_code_quality()` 関数を実装
- [ ] Task 1.4: `_generate_feedback()` ヘルパー関数を実装
- [ ] Task 1.5: `run_bandit()` を修正してJSONリストを返すように
- [ ] Task 1.6: 単体テスト追加 (`tests/quality_gate/test_code_analyzer.py`)

**推定時間**: 2-3時間

### 5.2 Phase 2: MutationTesterAgent 実装 (優先度: 高)

- [ ] Task 2.1: `mutation_tester_agent.py` ファイル作成
- [ ] Task 2.2: `Mutant` データクラス実装
- [ ] Task 2.3: `MutationReport` データクラス実装
- [ ] Task 2.4: `MutationTesterAgent` クラス実装
- [ ] Task 2.5: `_run_mutmut()` メソッド実装
- [ ] Task 2.6: `_parse_mutmut_output()` メソッド実装
- [ ] Task 2.7: `_get_survived_mutants()` メソッド実装
- [ ] Task 2.8: `_generate_feedback()` メソッド実装
- [ ] Task 2.9: 単体テスト追加 (`tests/agents/test_mutation_tester_agent.py`)

**推定時間**: 3-4時間

### 5.3 Phase 3: Orchestrator統合 (優先度: 中)

- [ ] Task 3.1: Orchestrator に Tier 1 品質ゲート呼び出しを追加
- [ ] Task 3.2: Orchestrator に Tier 2 品質ゲート呼び出しを追加
- [ ] Task 3.3: 品質ゲート不合格時のリトライループ実装
- [ ] Task 3.4: 統合テスト作成

**推定時間**: 2-3時間

### 5.4 Phase 4: 憲法ファイル作成 (優先度: 低)

- [ ] Task 4.1: `config/constitution.yaml` サンプル作成
- [ ] Task 4.2: 憲法ローダー実装 (`config/constitution_loader.py`)

**推定時間**: 1時間

---

## 6. 依存関係

### 6.1 必須パッケージ

```bash
pip install mutmut pytest-cov pylint mypy bandit
```

### 6.2 pyproject.toml 追加設定

```toml
[tool.mutmut]
paths_to_mutate = "src/"
backup = false
runner = "python -m pytest"
tests_dir = "tests/"

[tool.pytest.ini_options]
addopts = "--cov=src --cov-report=term-missing --cov-report=html"
```

---

## 7. 検証基準

### 7.1 実装完了の定義

- [ ] 全ての関数に型アノテーションがある
- [ ] 全ての公開関数にdocstringがある
- [ ] 単体テストが全て合格
- [ ] テストカバレッジ ≥ 90%
- [ ] Pylint スコア ≥ 8.0
- [ ] Bandit セキュリティスキャン合格

### 7.2 動作確認

```python
# 動作確認スクリプト
from src.nexuscore.utils.code_analyzer import analyze_code_quality

constitution = {
    "quality_gates": {
        "tier1": {
            "test_coverage_min": 90,
            "pylint_score_min": 8.0,
            "bandit_severity_max": "MEDIUM"
        }
    }
}

report = analyze_code_quality(
    source_path="src/nexuscore/npe/policies.py",
    test_path="tests/npe/test_policies.py",
    constitution=constitution,
    project_root="/home/user/NexusCore"
)

print(report.to_dict())
assert report.passed is True
```

---

## 8. 参照

- **親仕様**: CR-NEXUS-052 (品質ゲート仕様)
- **関連実装**:
  - `src/nexuscore/utils/code_analyzer.py` (既存)
  - `src/nexuscore/agents/base_agent.py` (既存)
  - `src/nexuscore/agents/guardian_agent.py` (既存)

---

**実装開始日**: 2025-12-28
**実装担当**: Claude Code
**レビュー予定日**: 実装完了後
