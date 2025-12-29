"""
MutationTesterAgent のユニットテスト

Tier 2品質ゲート（ミューテーションテスト）エージェントの
包括的なテストスイート。

テストカバレッジ目標: 80%以上
"""

import pytest
import subprocess
from unittest.mock import Mock, patch, MagicMock
from dataclasses import asdict

from nexuscore.agents.mutation_tester_agent import (
    MutationTesterAgent,
    MutationReport,
    Mutant,
    MutationTestError,
    MutationTestTimeoutError
)


@pytest.fixture
def mock_constitution():
    """テスト用憲法データ"""
    return {
        "quality_gates": {
            "tier2": {
                "mutation_score_min": 80,
                "mutation_timeout_sec": 10
            }
        }
    }


@pytest.fixture
def mutation_agent():
    """MutationTesterAgentインスタンス"""
    return MutationTesterAgent()


@pytest.fixture
def mock_mutmut_success_output():
    """mutmut成功時の出力（パース可能な形式）"""
    return """
Legend for output:
🎉 Killed mutants.   The goal is for everything to end up in this bucket.
⏰ Timeout.          Test suite took 10 times as long as the baseline so were killed.
🤔 Suspicious.       Tests took a long time, but not long enough to be fatal.
🙁 Survived.         This means your tests needs to be expanded.

Total mutants: 20
Killed: 17 (85.0%)
Timeout: 0 (0.0%)
Suspicious: 0 (0.0%)
Survived: 3 (15.0%)
Skipped: 0

Mutation score: 85.0%
"""


@pytest.fixture
def mock_mutmut_fail_output():
    """mutmut失敗時の出力（低スコア）"""
    return """
Total mutants: 23
Killed: 13 (56.5%)
Timeout: 2 (8.7%)
Suspicious: 1 (4.3%)
Survived: 7 (30.4%)

Mutation score: 56.5%
"""


@pytest.fixture
def mock_survived_mutants_output():
    """mutmut results コマンドの出力"""
    return """
To apply a mutant on disk:
    mutmut apply <id>

Survived 🙁

1. src/calculator.py:15
   - from: result = a + b
   - to:   result = a - b

2. src/calculator.py:20
   - from: if x > 0:
   - to:   if x >= 0:
"""


class TestMutationTesterAgentInit:
    """MutationTesterAgent初期化テスト"""

    def test_init_creates_instance(self):
        """インスタンス生成の確認"""
        agent = MutationTesterAgent()
        assert agent is not None
        assert isinstance(agent, MutationTesterAgent)


class TestRunMutationTesting:
    """run_mutation_testing メソッドのテスト"""

    def test_run_mutation_testing_success_pass(
        self,
        mutation_agent,
        mock_constitution,
        mock_mutmut_success_output
    ):
        """ミューテーションテスト成功（合格）"""
        # _run_mutmut は Dict[str, int] を返す
        mock_mutmut_result = {
            "total": 20,
            "killed": 17,
            "survived": 3,
            "timeout": 0,
            "suspicious": 0
        }

        with patch.object(mutation_agent, '_run_mutmut', return_value=mock_mutmut_result):
            with patch.object(mutation_agent, '_get_survived_mutants', return_value=[]):
                result = mutation_agent.run_mutation_testing(
                    source_path="src/example.py",
                    test_path="tests/test_example.py",
                    constitution=mock_constitution,
                    timeout_per_test=10
                )

                # 検証
                assert isinstance(result, MutationReport)
                assert result.passed is True  # 85% >= 80%
                assert result.mutation_score == 85.0  # 17/20 * 100
                assert result.total_mutants == 20
                assert result.killed == 17
                assert result.survived == 3
                assert result.timeout == 0
                assert result.suspicious == 0
                assert len(result.survived_mutants) == 0
                assert "✅" in result.feedback or "クリア" in result.feedback

    def test_run_mutation_testing_success_fail(
        self,
        mutation_agent,
        mock_constitution,
        mock_mutmut_fail_output
    ):
        """ミューテーションテスト成功（不合格）"""
        survived_mutant = Mutant(
            file_path="example.py",
            line_number=10,
            mutator="BinaryOperator",
            original_code="a + b",
            mutated_code="a - b",
            status="survived"
        )

        mock_mutmut_result = {
            "total": 23,
            "killed": 13,
            "survived": 7,
            "timeout": 2,
            "suspicious": 1
        }

        with patch.object(mutation_agent, '_run_mutmut', return_value=mock_mutmut_result):
            with patch.object(mutation_agent, '_get_survived_mutants', return_value=[survived_mutant]):
                result = mutation_agent.run_mutation_testing(
                    source_path="src/example.py",
                    test_path="tests/test_example.py",
                    constitution=mock_constitution,
                    timeout_per_test=10
                )

                assert result.passed is False  # 56.5% < 80%
                assert result.mutation_score == pytest.approx(56.52, rel=0.1)  # 13/23 * 100
                assert result.total_mutants == 23
                assert result.survived == 7
                assert len(result.survived_mutants) == 1
                assert "❌" in result.feedback or "不合格" in result.feedback

    def test_run_mutation_testing_no_mutants(
        self,
        mutation_agent,
        mock_constitution
    ):
        """mutantが0個の場合"""
        mock_mutmut_result = {
            "total": 0,
            "killed": 0,
            "survived": 0,
            "timeout": 0,
            "suspicious": 0
        }

        with patch.object(mutation_agent, '_run_mutmut', return_value=mock_mutmut_result):
            result = mutation_agent.run_mutation_testing(
                source_path="src/empty.py",
                test_path="tests/test_empty.py",
                constitution=mock_constitution
            )

            assert result.passed is False  # 0% < 80%
            assert result.mutation_score == 0.0
            assert result.total_mutants == 0

    def test_run_mutation_testing_edge_case_100_percent(
        self,
        mutation_agent,
        mock_constitution
    ):
        """全てのmutantをkillした場合（100%）"""
        mock_mutmut_result = {
            "total": 15,
            "killed": 15,
            "survived": 0,
            "timeout": 0,
            "suspicious": 0
        }

        with patch.object(mutation_agent, '_run_mutmut', return_value=mock_mutmut_result):
            with patch.object(mutation_agent, '_get_survived_mutants', return_value=[]):
                result = mutation_agent.run_mutation_testing(
                    source_path="src/perfect.py",
                    test_path="tests/test_perfect.py",
                    constitution=mock_constitution
                )

                assert result.passed is True
                assert result.mutation_score == 100.0
                assert result.survived == 0
                assert "✅" in result.feedback

    def test_run_mutation_testing_timeout_error(
        self,
        mutation_agent,
        mock_constitution
    ):
        """mutmutタイムアウト時は適切なMutationReportを返す"""
        with patch.object(mutation_agent, '_run_mutmut', side_effect=MutationTestTimeoutError("timeout")):
            result = mutation_agent.run_mutation_testing(
                source_path="src/example.py",
                test_path="tests/test_example.py",
                constitution=mock_constitution
            )

            # タイムアウトエラーは適切に処理される
            assert isinstance(result, MutationReport)
            assert result.passed is False
            assert result.mutation_score == 0.0
            assert result.total_mutants == 0
            assert "タイムアウト" in result.feedback
            assert "600秒" in result.feedback

    def test_run_mutation_testing_execution_error(
        self,
        mutation_agent,
        mock_constitution
    ):
        """mutmut実行エラー時は適切なMutationReportを返す"""
        with patch.object(mutation_agent, '_run_mutmut', side_effect=MutationTestError("execution failed")):
            result = mutation_agent.run_mutation_testing(
                source_path="src/example.py",
                test_path="tests/test_example.py",
                constitution=mock_constitution
            )

            # 実行エラーは適切に処理される
            assert isinstance(result, MutationReport)
            assert result.passed is False
            assert result.mutation_score == 0.0
            assert result.total_mutants == 0
            assert "実行に失敗" in result.feedback
            assert "execution failed" in result.feedback


class TestRunMutmut:
    """_run_mutmut メソッドのテスト"""

    def test_run_mutmut_success(self, mutation_agent, mock_mutmut_success_output):
        """mutmut正常実行"""
        # 2回の subprocess.run 呼び出し: 1. mutmut run --rerun-all, 2. mutmut run 本体
        mock_rerun_result = Mock()
        mock_rerun_result.stdout = ""
        mock_rerun_result.stderr = ""

        mock_result = Mock()
        mock_result.stdout = mock_mutmut_success_output
        mock_result.stderr = ""

        with patch('subprocess.run', side_effect=[mock_rerun_result, mock_result]):
            result = mutation_agent._run_mutmut(
                source_path="src/example.py",
                test_path="tests/test_example.py",
                timeout=10
            )

            assert isinstance(result, dict)
            assert result["total"] == 20
            assert result["killed"] == 17
            assert result["survived"] == 3
            assert result["timeout"] == 0
            assert result["suspicious"] == 0

    def test_run_mutmut_timeout(self, mutation_agent):
        """mutmut実行タイムアウト時に適切な例外を投げる"""
        # 1回目のcall (rerun-all) は成功、2回目のcall (本体) がタイムアウト
        mock_rerun_result = Mock()
        mock_rerun_result.stdout = ""
        mock_rerun_result.stderr = ""

        with patch('subprocess.run', side_effect=[
            mock_rerun_result,
            subprocess.TimeoutExpired(cmd="mutmut", timeout=600)
        ]):
            # タイムアウト時はMutationTestTimeoutErrorを投げる
            with pytest.raises(MutationTestTimeoutError) as exc_info:
                mutation_agent._run_mutmut(
                    source_path="src/example.py",
                    test_path="tests/test_example.py",
                    timeout=10
                )

            # エラーメッセージの検証
            assert "timed out" in str(exc_info.value).lower()

    def test_run_mutmut_exception(self, mutation_agent):
        """mutmut実行時の予期しない例外を適切にラップする"""
        # 1回目のcall (rerun-all) は成功、2回目のcall (本体) が例外
        mock_rerun_result = Mock()
        mock_rerun_result.stdout = ""
        mock_rerun_result.stderr = ""

        with patch('subprocess.run', side_effect=[
            mock_rerun_result,
            Exception("Unexpected error")
        ]):
            # 予期しない例外はMutationTestErrorでラップされる
            with pytest.raises(MutationTestError) as exc_info:
                mutation_agent._run_mutmut(
                    source_path="src/example.py",
                    test_path="tests/test_example.py",
                    timeout=10
                )

            # エラーメッセージの検証
            assert "execution failed" in str(exc_info.value).lower()
            assert "unexpected error" in str(exc_info.value).lower()


class TestParseMutmutOutput:
    """_parse_mutmut_output メソッドのテスト"""

    def test_parse_mutmut_output_success(self, mutation_agent):
        """正常なmutmut出力のパース"""
        output = """
        Total mutants: 120
        Killed: 96 (80.0%)
        Survived: 18 (15.0%)
        Timeout: 4 (3.3%)
        Suspicious: 2 (1.7%)
        """

        result = mutation_agent._parse_mutmut_output(output)

        assert result["total"] == 120
        assert result["killed"] == 96
        assert result["survived"] == 18
        assert result["timeout"] == 4
        assert result["suspicious"] == 2

    def test_parse_mutmut_output_no_mutants(self, mutation_agent):
        """ミュータントが0の場合"""
        output = "Total mutants: 0"

        result = mutation_agent._parse_mutmut_output(output)

        assert result["total"] == 0
        assert result["killed"] == 0
        assert result["survived"] == 0

    def test_parse_mutmut_output_partial_data(self, mutation_agent):
        """一部のデータのみ存在する場合"""
        output = """
        Total mutants: 50
        Killed: 40
        """

        result = mutation_agent._parse_mutmut_output(output)

        assert result["total"] == 50
        assert result["killed"] == 40
        assert result["survived"] == 0  # デフォルト値
        assert result["timeout"] == 0
        assert result["suspicious"] == 0

    def test_parse_mutmut_output_malformed(self, mutation_agent):
        """不正な出力のパース"""
        output = "Invalid output"

        result = mutation_agent._parse_mutmut_output(output)

        # デフォルト値が返される
        assert result["total"] == 0
        assert result["killed"] == 0
        assert result["survived"] == 0
        assert result["timeout"] == 0
        assert result["suspicious"] == 0


class TestGetSurvivedMutants:
    """_get_survived_mutants メソッドのテスト"""

    def test_get_survived_mutants_success(
        self,
        mutation_agent,
        mock_survived_mutants_output
    ):
        """生き残ったmutantの正常取得"""
        mock_result = Mock()
        mock_result.stdout = mock_survived_mutants_output
        mock_result.stderr = ""

        with patch('subprocess.run', return_value=mock_result):
            mutants = mutation_agent._get_survived_mutants()

            assert len(mutants) == 2
            assert mutants[0].file_path == "src/calculator.py"
            assert mutants[0].line_number == 15
            assert mutants[0].original_code == "result = a + b"
            assert mutants[0].mutated_code == "result = a - b"
            assert mutants[0].status == "survived"

            assert mutants[1].file_path == "src/calculator.py"
            assert mutants[1].line_number == 20

    def test_get_survived_mutants_no_survivors(self, mutation_agent):
        """生き残ったmutantなし"""
        mock_result = Mock()
        mock_result.stdout = "No mutants survived"
        mock_result.stderr = ""

        with patch('subprocess.run', return_value=mock_result):
            mutants = mutation_agent._get_survived_mutants()

            assert len(mutants) == 0

    def test_get_survived_mutants_error(self, mutation_agent):
        """mutmut results エラー"""
        with patch('subprocess.run', side_effect=Exception("Error")):
            mutants = mutation_agent._get_survived_mutants()

            assert len(mutants) == 0


class TestParseSurvivedMutants:
    """_parse_survived_mutants メソッドのテスト"""

    def test_parse_survived_mutants_multiple(
        self,
        mutation_agent,
        mock_survived_mutants_output
    ):
        """複数のmutantをパース"""
        mutants = mutation_agent._parse_survived_mutants(mock_survived_mutants_output)

        assert len(mutants) == 2
        assert all(m.status == "survived" for m in mutants)

    def test_parse_survived_mutants_empty(self, mutation_agent):
        """空の出力"""
        mutants = mutation_agent._parse_survived_mutants("")

        assert len(mutants) == 0


class TestSuggestTestForMutant:
    """_suggest_test_for_mutant メソッドのテスト"""

    def test_suggest_binary_operator_add_to_sub(self, mutation_agent):
        """加算→減算の変異に対する提案"""
        mutant = Mutant(
            file_path="example.py",
            line_number=10,
            mutator="BinaryOperator",
            original_code="a + b",
            mutated_code="a - b",
            status="survived"
        )

        suggestion = mutation_agent._suggest_test_for_mutant(mutant)

        assert "加算と減算" in suggestion or "境界テスト" in suggestion

    def test_suggest_binary_operator_sub_to_add(self, mutation_agent):
        """減算→加算の変異に対する提案"""
        mutant = Mutant(
            file_path="example.py",
            line_number=11,
            mutator="BinaryOperator",
            original_code="a - b",
            mutated_code="a + b",
            status="survived"
        )

        suggestion = mutation_agent._suggest_test_for_mutant(mutant)

        assert "減算と加算" in suggestion or "境界テスト" in suggestion

    def test_suggest_binary_operator_mul_to_div(self, mutation_agent):
        """乗算→除算の変異に対する提案"""
        mutant = Mutant(
            file_path="example.py",
            line_number=12,
            mutator="BinaryOperator",
            original_code="a * b",
            mutated_code="a / b",
            status="survived"
        )

        suggestion = mutation_agent._suggest_test_for_mutant(mutant)

        assert "乗算と除算" in suggestion

    def test_suggest_comparison_operator_gt_to_gte(self, mutation_agent):
        """比較演算子 > → >= の変異に対する提案"""
        mutant = Mutant(
            file_path="example.py",
            line_number=15,
            mutator="ComparisonOperator",
            original_code="x > 0",
            mutated_code="x >= 0",
            status="survived"
        )

        suggestion = mutation_agent._suggest_test_for_mutant(mutant)

        assert "境界値" in suggestion

    def test_suggest_comparison_operator_lt_to_lte(self, mutation_agent):
        """比較演算子 < → <= の変異に対する提案"""
        mutant = Mutant(
            file_path="example.py",
            line_number=16,
            mutator="ComparisonOperator",
            original_code="x < 100",
            mutated_code="x <= 100",
            status="survived"
        )

        suggestion = mutation_agent._suggest_test_for_mutant(mutant)

        assert "境界値" in suggestion

    def test_suggest_logical_operator_and_to_or(self, mutation_agent):
        """論理演算子 and → or の変異に対する提案"""
        mutant = Mutant(
            file_path="example.py",
            line_number=20,
            mutator="LogicalOperator",
            original_code="if a and b:",
            mutated_code="if a or b:",
            status="survived"
        )

        suggestion = mutation_agent._suggest_test_for_mutant(mutant)

        assert "論理演算子" in suggestion or "真偽値テーブル" in suggestion

    def test_suggest_logical_operator_or_to_and(self, mutation_agent):
        """論理演算子 or → and の変異に対する提案"""
        mutant = Mutant(
            file_path="example.py",
            line_number=21,
            mutator="LogicalOperator",
            original_code="if a or b:",
            mutated_code="if a and b:",
            status="survived"
        )

        suggestion = mutation_agent._suggest_test_for_mutant(mutant)

        assert "論理演算子" in suggestion or "真偽値テーブル" in suggestion

    def test_suggest_unknown_mutator(self, mutation_agent):
        """未知の変異タイプ"""
        mutant = Mutant(
            file_path="example.py",
            line_number=30,
            mutator="UnknownMutator",
            original_code="foo()",
            mutated_code="bar()",
            status="survived"
        )

        suggestion = mutation_agent._suggest_test_for_mutant(mutant)

        assert "テストケース" in suggestion


class TestGenerateFeedback:
    """_generate_feedback メソッドのテスト"""

    def test_generate_feedback_passed(self, mutation_agent):
        """合格時のフィードバック"""
        feedback = mutation_agent._generate_feedback(
            survived_mutants=[],
            mutation_score=85.0,
            min_score=80.0
        )

        assert "✅" in feedback
        assert "85.0" in feedback
        assert "クリア" in feedback or "基準" in feedback

    def test_generate_feedback_failed_with_mutants(self, mutation_agent):
        """不合格時のフィードバック（mutant詳細付き）"""
        mutants = [
            Mutant(
                file_path="test.py",
                line_number=10,
                mutator="BinaryOperator",
                original_code="a + b",
                mutated_code="a - b",
                status="survived"
            ),
            Mutant(
                file_path="test.py",
                line_number=20,
                mutator="ComparisonOperator",
                original_code="x > 0",
                mutated_code="x >= 0",
                status="survived"
            )
        ]

        feedback = mutation_agent._generate_feedback(
            survived_mutants=mutants,
            mutation_score=60.0,
            min_score=80.0
        )

        assert "❌" in feedback
        assert "不合格" in feedback
        assert "60.0" in feedback
        assert "80.0" in feedback
        assert "2個のミュータント" in feedback
        assert "test.py:10" in feedback
        assert "test.py:20" in feedback

    def test_generate_feedback_many_mutants(self, mutation_agent):
        """多数のmutant（最大10個表示）"""
        mutants = [
            Mutant(
                file_path=f"test{i}.py",
                line_number=i,
                mutator="BinaryOperator",
                original_code="x",
                mutated_code="y",
                status="survived"
            )
            for i in range(15)
        ]

        feedback = mutation_agent._generate_feedback(
            survived_mutants=mutants,
            mutation_score=50.0,
            min_score=80.0
        )

        assert "15個のミュータント" in feedback
        assert "test0.py:0" in feedback  # 最初
        assert "test9.py:9" in feedback  # 10番目
        assert "... 他 5個" in feedback  # 残り


class TestMutationReportDataclass:
    """MutationReport dataclassのテスト"""

    def test_mutation_report_creation(self):
        """MutationReport作成"""
        report = MutationReport(
            passed=True,
            mutation_score=85.0,
            total_mutants=20,
            killed=17,
            survived=3,
            timeout=0,
            suspicious=0,
            survived_mutants=[],
            feedback="Good"
        )

        assert report.passed is True
        assert report.mutation_score == 85.0
        assert report.total_mutants == 20

    def test_mutation_report_to_dict(self):
        """MutationReportの辞書変換"""
        mutant = Mutant(
            file_path="test.py",
            line_number=1,
            mutator="Test",
            original_code="a",
            mutated_code="b",
            status="survived"
        )

        report = MutationReport(
            passed=False,
            mutation_score=50.0,
            total_mutants=10,
            killed=5,
            survived=5,
            timeout=0,
            suspicious=0,
            survived_mutants=[mutant],
            feedback="Needs improvement"
        )

        report_dict = report.to_dict()

        assert report_dict["passed"] is False
        assert report_dict["mutation_score"] == 50.0
        assert report_dict["survived_count"] == 1  # survived_mutants ではなく survived_count


class TestMutantDataclass:
    """Mutant dataclassのテスト"""

    def test_mutant_creation(self):
        """Mutant作成"""
        mutant = Mutant(
            file_path="example.py",
            line_number=42,
            mutator="BinaryOperator",
            original_code="x + y",
            mutated_code="x - y",
            status="survived"
        )

        assert mutant.file_path == "example.py"
        assert mutant.line_number == 42
        assert mutant.mutator == "BinaryOperator"
        assert mutant.status == "survived"


class TestIntegration:
    """統合テスト"""

    def test_full_workflow_success(
        self,
        mutation_agent,
        mock_constitution,
        mock_mutmut_success_output
    ):
        """完全なワークフロー（成功）"""
        # subprocess.run の呼び出し順: 1. rerun-all, 2. run本体, 3. results
        mock_rerun_result = Mock()
        mock_rerun_result.stdout = ""
        mock_rerun_result.stderr = ""

        mock_run_result = Mock()
        mock_run_result.stdout = mock_mutmut_success_output
        mock_run_result.stderr = ""

        mock_results_result = Mock()
        mock_results_result.stdout = ""  # No survivors
        mock_results_result.stderr = ""

        with patch('subprocess.run', side_effect=[
            mock_rerun_result,
            mock_run_result,
            mock_results_result
        ]):
            result = mutation_agent.run_mutation_testing(
                source_path="src/example.py",
                test_path="tests/test_example.py",
                constitution=mock_constitution,
                timeout_per_test=10
            )

            # 総合検証
            assert result.passed is True
            assert result.mutation_score >= 80.0
            assert "✅" in result.feedback or "クリア" in result.feedback

    def test_full_workflow_fail(
        self,
        mutation_agent,
        mock_constitution,
        mock_mutmut_fail_output,
        mock_survived_mutants_output
    ):
        """完全なワークフロー（不合格）"""
        mock_rerun_result = Mock()
        mock_rerun_result.stdout = ""
        mock_rerun_result.stderr = ""

        mock_run_result = Mock()
        mock_run_result.stdout = mock_mutmut_fail_output
        mock_run_result.stderr = ""

        mock_results_result = Mock()
        mock_results_result.stdout = mock_survived_mutants_output
        mock_results_result.stderr = ""

        with patch('subprocess.run', side_effect=[
            mock_rerun_result,
            mock_run_result,
            mock_results_result
        ]):
            result = mutation_agent.run_mutation_testing(
                source_path="src/example.py",
                test_path="tests/test_example.py",
                constitution=mock_constitution,
                timeout_per_test=10
            )

            # 総合検証
            assert result.passed is False  # 56.5% < 80%
            assert result.mutation_score < 80.0
            assert "❌" in result.feedback or "不合格" in result.feedback
            assert len(result.survived_mutants) == 2


class TestIntegrationReal:
    """
    統合テスト（実データ版）

    subprocessだけモックし、それ以外は実際のコードを実行。
    実際のmutmut出力をパースして、計算・フィードバック生成が正しいか検証。
    """

    def test_run_mutation_testing_with_real_parsing(self, mutation_agent, mock_constitution):
        """実際のパース処理を含む統合テスト"""
        # 実際のmutmut出力（本物のフォーマット）
        real_mutmut_output = """
Legend for output:
🎉 Killed mutants.   The goal is for everything to end up in this bucket.
⏰ Timeout.          Test suite took 10 times as long as the baseline so were killed.
🤔 Suspicious.       Tests took a long time, but not long enough to be fatal.
🙁 Survived.         This means your tests needs to be expanded.

Total mutants: 25
Killed: 20 (80.0%)
Timeout: 1 (4.0%)
Suspicious: 0 (0.0%)
Survived: 4 (16.0%)
Skipped: 0

Mutation score: 80.0%
"""

        real_survived_output = """
To apply a mutant on disk:
    mutmut apply <id>

Survived 🙁

1. src/calculator.py:10
   - from: result = a + b
   - to:   result = a - b

2. src/calculator.py:15
   - from: if x > 0:
   - to:   if x >= 0:

3. src/validator.py:20
   - from: return True
   - to:   return False

4. src/validator.py:25
   - from: value * 2
   - to:   value / 2
"""

        # subprocessのみモック
        mock_rerun_result = Mock()
        mock_rerun_result.stdout = ""
        mock_rerun_result.stderr = ""

        mock_run_result = Mock()
        mock_run_result.stdout = real_mutmut_output
        mock_run_result.stderr = ""

        mock_results_result = Mock()
        mock_results_result.stdout = real_survived_output
        mock_results_result.stderr = ""

        with patch('subprocess.run', side_effect=[
            mock_rerun_result,
            mock_run_result,
            mock_results_result
        ]):
            # 実際のコードを実行
            result = mutation_agent.run_mutation_testing(
                source_path="src/calculator.py",
                test_path="tests/test_calculator.py",
                constitution=mock_constitution,
                timeout_per_test=10
            )

        # 実際のパース結果を検証
        assert result.total_mutants == 25, "Total mutantsのパースが正しいか"
        assert result.killed == 20, "Killedのパースが正しいか"
        assert result.survived == 4, "Survivedのパースが正しいか"
        assert result.timeout == 1, "Timeoutのパースが正しいか"
        assert result.suspicious == 0, "Suspiciousのパースが正しいか"

        # 計算が正しいか（20/25 = 80.0%）
        assert result.mutation_score == 80.0, "mutation_scoreの計算が正しいか"

        # 合格判定が正しいか（80% == 80%なので合格）
        assert result.passed is True, "合格判定が正しいか"

        # 生き残ったmutantのパースが正しいか
        assert len(result.survived_mutants) == 4, "生き残ったmutantの数が正しいか"

        # 1番目のmutantの詳細検証
        mutant1 = result.survived_mutants[0]
        assert mutant1.file_path == "src/calculator.py"
        assert mutant1.line_number == 10
        assert mutant1.original_code == "result = a + b"
        assert mutant1.mutated_code == "result = a - b"
        assert mutant1.status == "survived"

        # フィードバックが生成されているか
        assert "✅" in result.feedback, "合格時のフィードバックが正しいか"
        assert "80.0" in result.feedback, "スコアが含まれているか"

    def test_run_mutation_testing_fail_with_suggestions(self, mutation_agent, mock_constitution):
        """不合格時のフィードバック生成を実データでテスト"""
        # 低スコアの実データ
        real_mutmut_output = """
Total mutants: 50
Killed: 25 (50.0%)
Timeout: 2 (4.0%)
Suspicious: 3 (6.0%)
Survived: 20 (40.0%)

Mutation score: 50.0%
"""

        real_survived_output = """
Survived 🙁

1. src/calc.py:5
   - from: a + b
   - to:   a - b

2. src/calc.py:10
   - from: x > 0
   - to:   x >= 0

3. src/calc.py:15
   - from: if a and b:
   - to:   if a or b:
"""

        mock_rerun_result = Mock()
        mock_rerun_result.stdout = ""
        mock_rerun_result.stderr = ""

        mock_run_result = Mock()
        mock_run_result.stdout = real_mutmut_output
        mock_run_result.stderr = ""

        mock_results_result = Mock()
        mock_results_result.stdout = real_survived_output
        mock_results_result.stderr = ""

        with patch('subprocess.run', side_effect=[
            mock_rerun_result,
            mock_run_result,
            mock_results_result
        ]):
            result = mutation_agent.run_mutation_testing(
                source_path="src/calc.py",
                test_path="tests/test_calc.py",
                constitution=mock_constitution,
                timeout_per_test=10
            )

        # 不合格判定
        assert result.passed is False, "50% < 80%なので不合格"
        assert result.mutation_score == 50.0

        # フィードバックの内容検証
        assert "❌" in result.feedback or "不合格" in result.feedback
        assert "50.0" in result.feedback, "実際のスコアが含まれているか"
        assert "80" in result.feedback, "基準スコアが含まれているか"
        # パースされたmutantは3個（real_survived_outputに3個しかない）
        assert "3個のミュータント" in result.feedback, "パースされたmutantの数が含まれているか"

        # 具体的な提案が含まれているか
        assert "src/calc.py:5" in result.feedback, "ファイル位置が含まれているか"
        assert "a + b" in result.feedback, "元のコードが含まれているか"
        assert "a - b" in result.feedback, "変更後のコードが含まれているか"

        # 生き残ったmutantに対する提案が生成されているか
        # （_suggest_test_for_mutantが実際に呼ばれている）
        feedback_lower = result.feedback.lower()
        assert "テスト" in result.feedback or "追加" in result.feedback, "改善提案が含まれているか"

    def test_edge_case_zero_mutants_real_data(self, mutation_agent, mock_constitution):
        """mutantが0個の実データでテスト"""
        real_mutmut_output = """
Total mutants: 0
Killed: 0 (0.0%)
Timeout: 0 (0.0%)
Suspicious: 0 (0.0%)
Survived: 0 (0.0%)

Mutation score: 0.0%
"""

        mock_rerun_result = Mock()
        mock_rerun_result.stdout = ""
        mock_rerun_result.stderr = ""

        mock_run_result = Mock()
        mock_run_result.stdout = real_mutmut_output
        mock_run_result.stderr = ""

        with patch('subprocess.run', side_effect=[mock_rerun_result, mock_run_result]):
            result = mutation_agent.run_mutation_testing(
                source_path="src/empty.py",
                test_path="tests/test_empty.py",
                constitution=mock_constitution
            )

        # 0個のmutantは不合格（テストする価値のあるコードがない）
        assert result.total_mutants == 0
        assert result.mutation_score == 0.0
        assert result.passed is False, "mutant=0は不合格（0% < 80%）"

    def test_edge_case_malformed_output_recovery(self, mutation_agent):
        """不正な出力からの回復をテスト"""
        # 実際に起こりうる異常な出力
        malformed_outputs = [
            "Error: mutmut not found\n",  # コマンド未インストール
            "Total mutants: ???\nKilled: abc",  # 不正な値
            "",  # 空出力
            "Some random output\nwithout proper format",  # フォーマット違反
        ]

        for malformed_output in malformed_outputs:
            mock_rerun_result = Mock()
            mock_rerun_result.stdout = ""
            mock_rerun_result.stderr = ""

            mock_run_result = Mock()
            mock_run_result.stdout = malformed_output
            mock_run_result.stderr = ""

            with patch('subprocess.run', side_effect=[mock_rerun_result, mock_run_result]):
                # _run_mutmutレベルでテスト
                result = mutation_agent._run_mutmut(
                    source_path="src/test.py",
                    test_path="tests/test_test.py",
                    timeout=10
                )

            # 不正な出力でもクラッシュせず、デフォルト値を返す
            assert isinstance(result, dict), f"Failed for output: {malformed_output[:50]}"
            assert result["total"] == 0, "不正な出力ではtotal=0"
            assert result["killed"] == 0, "不正な出力ではkilled=0"

    def test_partial_data_parsing(self, mutation_agent):
        """一部のデータしかない場合のパース"""
        partial_outputs = [
            "Total mutants: 100\n",  # Totalだけ
            "Total mutants: 50\nKilled: 30\n",  # Survivedなし
            "Killed: 20\nSurvived: 5\n",  # Totalなし
        ]

        for output in partial_outputs:
            result = mutation_agent._parse_mutmut_output(output)

            # クラッシュせず、パースできた部分は正しい
            assert isinstance(result, dict)
            assert "total" in result
            assert "killed" in result
            assert "survived" in result

            # パースできなかった部分はデフォルト値0
            if "Total mutants: 100" in output:
                assert result["total"] == 100
            if "Killed: 30" in output:
                assert result["killed"] == 30


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
