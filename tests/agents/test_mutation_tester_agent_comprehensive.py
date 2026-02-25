"""
mutation_tester_agent.py の包括的テスト

カバレッジ:
- MutationTesterAgent: ミューテーションテストエージェント
  - __init__: BaseAgent初期化
  - run_mutation_testing: mutmut実行とレポート生成
  - _run_mutmut: mutmutコマンド実行
  - _parse_mutmut_output: v2.x/v3.x出力パース
  - _get_survived_mutants: 生き残ったミュータント取得
  - _parse_survived_mutants: mutmut resultsパース
  - _generate_feedback: フィードバック生成
  - _suggest_test_for_mutant: テスト提案
"""

import subprocess
from unittest.mock import Mock, patch

import pytest

try:
    from nexuscore.agents.mutation_tester_agent import (
        Mutant,
        MutationReport,
        MutationTesterAgent,
        MutationTestError,  # noqa: F401
        MutationTestTimeoutError,  # noqa: F401
    )

    HAS_MUTATION_TESTER = True
except ImportError:
    HAS_MUTATION_TESTER = False
    MutationTesterAgent = None


@pytest.mark.skipif(not HAS_MUTATION_TESTER, reason="mutation_tester_agent module not available")
class TestDataClasses:
    """データクラスのテスト"""

    def test_mutant_creation(self):
        """Mutantデータクラスの作成"""
        mutant = Mutant(
            file_path="src/calc.py",
            line_number=10,
            mutator="BinaryOperator",
            original_code="return a + b",
            mutated_code="return a - b",
            status="survived",
        )

        assert mutant.file_path == "src/calc.py"
        assert mutant.line_number == 10
        assert mutant.status == "survived"

    def test_mutation_report_creation(self):
        """MutationReportデータクラスの作成"""
        report = MutationReport(
            passed=True,
            mutation_score=85.0,
            total_mutants=20,
            killed=17,
            survived=3,
            timeout=0,
            suspicious=0,
        )

        assert report.passed is True
        assert report.mutation_score == 85.0
        assert report.total_mutants == 20

    def test_mutation_report_to_dict(self):
        """MutationReport.to_dict()メソッド"""
        mutant = Mutant("file.py", 1, "Op", "old", "new", "survived")
        report = MutationReport(
            passed=False,
            mutation_score=50.0,
            total_mutants=10,
            killed=5,
            survived=5,
            timeout=0,
            suspicious=0,
            survived_mutants=[mutant],
        )

        result = report.to_dict()

        assert result["passed"] is False
        assert result["mutation_score"] == 50.0
        assert result["survived_count"] == 1


@pytest.mark.skipif(not HAS_MUTATION_TESTER, reason="mutation_tester_agent module not available")
class TestMutationTesterAgentInit:
    """MutationTesterAgent 初期化のテスト"""

    @patch("nexuscore.agents.mutation_tester_agent.BaseAgent.__init__", return_value=None)
    def test_init_basic(self, mock_base_init):
        """基本的な初期化"""
        agent = MutationTesterAgent.__new__(MutationTesterAgent)

        agent.logger = Mock()

        MutationTesterAgent.__init__(agent)

        mock_base_init.assert_called_once()


@pytest.mark.skipif(not HAS_MUTATION_TESTER, reason="mutation_tester_agent module not available")
class TestParseMutmutOutput:
    """MutationTesterAgent._parse_mutmut_output() のテスト"""

    @patch("nexuscore.agents.mutation_tester_agent.BaseAgent.__init__", return_value=None)
    def test_parse_v3_emoji_output(self, mock_base_init):
        """v3.x絵文字ベース出力のパース"""
        agent = MutationTesterAgent.__new__(MutationTesterAgent)

        agent.logger = Mock()

        MutationTesterAgent.__init__(agent)

        output = "⠧ 20/20  🎉 17 🫥 0  ⏰ 0  🤔 0  🙁 3  🔇 0"
        result = agent._parse_mutmut_output(output)

        assert result["total"] == 20
        assert result["killed"] == 17
        assert result["survived"] == 3
        assert result["timeout"] == 0
        assert result["suspicious"] == 0

    @patch("nexuscore.agents.mutation_tester_agent.BaseAgent.__init__", return_value=None)
    def test_parse_v2_text_output(self, mock_base_init):
        """v2.xテキストベース出力のパース"""
        agent = MutationTesterAgent.__new__(MutationTesterAgent)

        agent.logger = Mock()

        MutationTesterAgent.__init__(agent)

        output = """
Total mutants: 20
Killed: 17 (85.0%)
Survived: 3 (15.0%)
Timeout: 0
Suspicious: 0
"""
        result = agent._parse_mutmut_output(output)

        assert result["total"] == 20
        assert result["killed"] == 17
        assert result["survived"] == 3

    @patch("nexuscore.agents.mutation_tester_agent.BaseAgent.__init__", return_value=None)
    def test_parse_empty_output(self, mock_base_init):
        """空の出力"""
        agent = MutationTesterAgent.__new__(MutationTesterAgent)

        agent.logger = Mock()

        MutationTesterAgent.__init__(agent)

        result = agent._parse_mutmut_output("")

        assert result["total"] == 0
        assert result["killed"] == 0

    @patch("nexuscore.agents.mutation_tester_agent.BaseAgent.__init__", return_value=None)
    def test_parse_calculate_total_from_components(self, mock_base_init):
        """totalが見つからない場合は他の値から計算"""
        agent = MutationTesterAgent.__new__(MutationTesterAgent)

        agent.logger = Mock()

        MutationTesterAgent.__init__(agent)

        output = "🎉 10 🙁 5 ⏰ 2 🤔 1"
        result = agent._parse_mutmut_output(output)

        # total = killed + survived + timeout + suspicious
        assert result["total"] == 10 + 5 + 2 + 1


@pytest.mark.skipif(not HAS_MUTATION_TESTER, reason="mutation_tester_agent module not available")
class TestParseSurvivedMutants:
    """MutationTesterAgent._parse_survived_mutants() のテスト"""

    @patch("nexuscore.agents.mutation_tester_agent.BaseAgent.__init__", return_value=None)
    def test_parse_survived_mutants_basic(self, mock_base_init):
        """基本的なmutmut results出力のパース"""
        agent = MutationTesterAgent.__new__(MutationTesterAgent)

        agent.logger = Mock()

        MutationTesterAgent.__init__(agent)

        output = """
Survived 🙁

1. src/calculator.py:15
   - from: result = a + b
   - to:   result = a - b

2. src/calculator.py:20
   - from: if x > 0:
   - to:   if x >= 0:
"""
        mutants = agent._parse_survived_mutants(output)

        assert len(mutants) == 2
        assert mutants[0].file_path == "src/calculator.py"
        assert mutants[0].line_number == 15
        assert mutants[0].original_code == "result = a + b"
        assert mutants[0].mutated_code == "result = a - b"

    @patch("nexuscore.agents.mutation_tester_agent.BaseAgent.__init__", return_value=None)
    def test_parse_survived_mutants_empty(self, mock_base_init):
        """空の出力"""
        agent = MutationTesterAgent.__new__(MutationTesterAgent)

        agent.logger = Mock()

        MutationTesterAgent.__init__(agent)

        mutants = agent._parse_survived_mutants("")

        assert len(mutants) == 0


@pytest.mark.skipif(not HAS_MUTATION_TESTER, reason="mutation_tester_agent module not available")
class TestGenerateFeedback:
    """MutationTesterAgent._generate_feedback() のテスト"""

    @patch("nexuscore.agents.mutation_tester_agent.BaseAgent.__init__", return_value=None)
    def test_generate_feedback_passed(self, mock_base_init):
        """合格時のフィードバック"""
        agent = MutationTesterAgent.__new__(MutationTesterAgent)

        agent.logger = Mock()

        MutationTesterAgent.__init__(agent)

        feedback = agent._generate_feedback([], mutation_score=85.0, min_score=80.0)

        assert "✅" in feedback
        assert "85.0%" in feedback

    @patch("nexuscore.agents.mutation_tester_agent.BaseAgent.__init__", return_value=None)
    def test_generate_feedback_failed(self, mock_base_init):
        """不合格時のフィードバック"""
        agent = MutationTesterAgent.__new__(MutationTesterAgent)

        agent.logger = Mock()

        MutationTesterAgent.__init__(agent)

        mutants = [
            Mutant("calc.py", 10, "Op", "a + b", "a - b", "survived"),
            Mutant("calc.py", 15, "Cmp", "x > 0", "x >= 0", "survived"),
        ]
        feedback = agent._generate_feedback(mutants, mutation_score=50.0, min_score=80.0)

        assert "❌" in feedback
        assert "50.0%" in feedback
        assert "80.0%" in feedback
        assert "calc.py:10" in feedback
        assert "calc.py:15" in feedback

    @patch("nexuscore.agents.mutation_tester_agent.BaseAgent.__init__", return_value=None)
    def test_generate_feedback_many_mutants(self, mock_base_init):
        """多数のミュータントがある場合（最初の10個のみ）"""
        agent = MutationTesterAgent.__new__(MutationTesterAgent)

        agent.logger = Mock()

        MutationTesterAgent.__init__(agent)

        mutants = [Mutant(f"file{i}.py", i, "Op", "old", "new", "survived") for i in range(20)]
        feedback = agent._generate_feedback(mutants, mutation_score=30.0, min_score=80.0)

        # 最初の10個のみ表示
        assert "file0.py" in feedback
        assert "file9.py" in feedback
        assert "他 10個" in feedback


@pytest.mark.skipif(not HAS_MUTATION_TESTER, reason="mutation_tester_agent module not available")
class TestSuggestTestForMutant:
    """MutationTesterAgent._suggest_test_for_mutant() のテスト"""

    @patch("nexuscore.agents.mutation_tester_agent.BaseAgent.__init__", return_value=None)
    def test_suggest_for_addition_to_subtraction(self, mock_base_init):
        """加算→減算の変異"""
        agent = MutationTesterAgent.__new__(MutationTesterAgent)

        agent.logger = Mock()

        MutationTesterAgent.__init__(agent)

        mutant = Mutant("file.py", 1, "Op", "a + b", "a - b", "survived")
        suggestion = agent._suggest_test_for_mutant(mutant)

        assert "加算と減算" in suggestion

    @patch("nexuscore.agents.mutation_tester_agent.BaseAgent.__init__", return_value=None)
    def test_suggest_for_comparison_operator(self, mock_base_init):
        """比較演算子の変異"""
        agent = MutationTesterAgent.__new__(MutationTesterAgent)

        agent.logger = Mock()

        MutationTesterAgent.__init__(agent)

        mutant = Mutant("file.py", 1, "Cmp", "x > y", "x >= y", "survived")
        suggestion = agent._suggest_test_for_mutant(mutant)

        assert "境界値" in suggestion

    @patch("nexuscore.agents.mutation_tester_agent.BaseAgent.__init__", return_value=None)
    def test_suggest_for_logical_operator(self, mock_base_init):
        """論理演算子の変異"""
        agent = MutationTesterAgent.__new__(MutationTesterAgent)

        agent.logger = Mock()

        MutationTesterAgent.__init__(agent)

        mutant = Mutant("file.py", 1, "Logic", "a and b", "a or b", "survived")
        suggestion = agent._suggest_test_for_mutant(mutant)

        assert "論理演算子" in suggestion


@pytest.mark.skipif(not HAS_MUTATION_TESTER, reason="mutation_tester_agent module not available")
class TestRunMutationTesting:
    """MutationTesterAgent.run_mutation_testing() のテスト"""

    @patch("nexuscore.agents.mutation_tester_agent.BaseAgent.__init__", return_value=None)
    @patch("subprocess.run")
    def test_run_mutation_testing_success(self, mock_subprocess, mock_base_init, tmp_path):
        """ミューテーションテスト成功"""
        # mutmutの出力をモック
        mock_subprocess.return_value = Mock(
            stdout="⠧ 20/20  🎉 17 🫥 0  ⏰ 0  🤔 0  🙁 3  🔇 0", stderr="", returncode=0
        )

        agent = MutationTesterAgent.__new__(MutationTesterAgent)

        agent.logger = Mock()

        MutationTesterAgent.__init__(agent)
        constitution = {"quality_gates": {"tier2": {"mutation_score_min": 80}}}

        result = agent.run_mutation_testing(
            source_path="src/calc.py", test_path="tests/test_calc.py", constitution=constitution
        )

        assert result.total_mutants == 20
        assert result.killed == 17
        assert result.mutation_score == 85.0
        assert result.passed is True

    @patch("nexuscore.agents.mutation_tester_agent.BaseAgent.__init__", return_value=None)
    @patch("subprocess.run")
    def test_run_mutation_testing_timeout(self, mock_subprocess, mock_base_init, tmp_path):
        """mutmutタイムアウト"""
        mock_subprocess.side_effect = subprocess.TimeoutExpired(cmd=["mutmut"], timeout=600)

        agent = MutationTesterAgent.__new__(MutationTesterAgent)

        agent.logger = Mock()

        MutationTesterAgent.__init__(agent)
        constitution = {"quality_gates": {"tier2": {"mutation_score_min": 80}}}

        result = agent.run_mutation_testing(
            source_path="src/calc.py", test_path="tests/test_calc.py", constitution=constitution
        )

        assert result.passed is False
        assert "タイムアウト" in result.feedback

    @patch("nexuscore.agents.mutation_tester_agent.BaseAgent.__init__", return_value=None)
    @patch("subprocess.run")
    def test_run_mutation_testing_error(self, mock_subprocess, mock_base_init, tmp_path):
        """mutmut実行エラー"""
        mock_subprocess.side_effect = Exception("mutmut not found")

        agent = MutationTesterAgent.__new__(MutationTesterAgent)

        agent.logger = Mock()

        MutationTesterAgent.__init__(agent)
        constitution = {"quality_gates": {"tier2": {"mutation_score_min": 80}}}

        result = agent.run_mutation_testing(
            source_path="src/calc.py", test_path="tests/test_calc.py", constitution=constitution
        )

        assert result.passed is False
        assert "実行エラー" in result.feedback


@pytest.mark.skipif(not HAS_MUTATION_TESTER, reason="mutation_tester_agent module not available")
class TestEdgeCases:
    """エッジケースのテスト"""

    @patch("nexuscore.agents.mutation_tester_agent.BaseAgent.__init__", return_value=None)
    @patch("subprocess.run")
    def test_run_mutation_testing_no_mutants(self, mock_subprocess, mock_base_init):
        """ミュータントが0個の場合"""
        mock_subprocess.return_value = Mock(
            stdout="⠧ 0/0  🎉 0 🫥 0  ⏰ 0  🤔 0  🙁 0  🔇 0", stderr="", returncode=0
        )

        agent = MutationTesterAgent.__new__(MutationTesterAgent)

        agent.logger = Mock()

        MutationTesterAgent.__init__(agent)
        constitution = {"quality_gates": {"tier2": {"mutation_score_min": 80}}}

        result = agent.run_mutation_testing(
            source_path="src/empty.py", test_path="tests/test_empty.py", constitution=constitution
        )

        # total=0の場合、mutation_score=0.0
        assert result.total_mutants == 0
        assert result.mutation_score == 0.0

    @patch("nexuscore.agents.mutation_tester_agent.BaseAgent.__init__", return_value=None)
    def test_get_survived_mutants_command_failure(self, mock_base_init):
        """mutmut resultsコマンド失敗"""
        agent = MutationTesterAgent.__new__(MutationTesterAgent)

        agent.logger = Mock()

        MutationTesterAgent.__init__(agent)

        with patch("subprocess.run", side_effect=Exception("Command failed")):
            mutants = agent._get_survived_mutants()

            # エラー時は空リストを返す
            assert mutants == []

    @patch("nexuscore.agents.mutation_tester_agent.BaseAgent.__init__", return_value=None)
    def test_suggest_test_for_unknown_mutation(self, mock_base_init):
        """不明な変異タイプ"""
        agent = MutationTesterAgent.__new__(MutationTesterAgent)

        agent.logger = Mock()

        MutationTesterAgent.__init__(agent)

        mutant = Mutant("file.py", 1, "Unknown", "foo", "bar", "survived")
        suggestion = agent._suggest_test_for_mutant(mutant)

        # デフォルトメッセージが返る
        assert "テストケースを追加" in suggestion
