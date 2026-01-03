"""
Guardian Agent - 品質ゲート統合のテスト

このテストは、Guardian AgentにTier 1/Tier 2品質ゲートが
正しく統合されているかを検証します。
"""

import os
import sys
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock

# gitモジュールをモック（テスト環境でGitPythonが不要）
sys.modules['git'] = MagicMock()

from nexuscore.agents import guardian_agent as guardian_module
from nexuscore.agents.guardian_agent import GuardianAgent
from nexuscore.utils.code_analyzer import QualityReport, SecurityIssue
from nexuscore.agents.mutation_tester_agent import MutationReport, Mutant


class DummyGitController:
    """テスト用ダミーGitController"""
    def __init__(self):
        self.calls = []

    def commit_changes(self, file_paths, message):
        self.calls.append((file_paths, message))
        return "abc123"


@pytest.fixture(autouse=True)
def disable_llm_router(monkeypatch):
    """LLMRouterを無効化（テスト高速化）"""
    from nexuscore.agents import base_agent
    monkeypatch.setattr(base_agent, "LLMRouter", None)


@pytest.fixture
def setup_guardian(monkeypatch):
    """Guardian Agentのセットアップ（GitControllerをモック）"""
    dummy_controller = DummyGitController()
    monkeypatch.setattr(guardian_module, "GitController", lambda: dummy_controller)
    return dummy_controller


@pytest.fixture
def mock_constitution():
    """テスト用憲法データ"""
    return {
        "quality_gates": {
            "tier1": {
                "test_coverage_min": 90,
                "pylint_score_min": 8.0,
                "mypy_enabled": True,
                "bandit_severity_max": "MEDIUM",
                "cyclomatic_complexity_max": 10,
            },
            "tier2": {
                "mutation_score_min": 80,
                "mutation_timeout_sec": 10,
            }
        }
    }


@pytest.fixture
def mock_quality_report_pass():
    """合格するTier 1レポート"""
    return QualityReport(
        passed=True,
        coverage_percentage=95.0,
        coverage_passed=True,
        pylint_score=8.5,
        pylint_passed=True,
        mypy_passed=True,
        mypy_output="Success: no issues found",
        bandit_passed=True,
        security_issues=[],
        feedback="全ての品質基準を満たしています。",
        violations=[]
    )


@pytest.fixture
def mock_quality_report_fail():
    """不合格のTier 1レポート"""
    return QualityReport(
        passed=False,
        coverage_percentage=75.0,
        coverage_passed=False,
        pylint_score=6.5,
        pylint_passed=False,
        mypy_passed=False,
        mypy_output="Found 5 errors",
        bandit_passed=True,
        security_issues=[],
        feedback="カバレッジとPylintスコアが不足しています。",
        violations=[
            "カバレッジ 75.0% < 90% (最低基準)",
            "Pylint 6.5/10 < 8.0 (最低基準)",
            "MyPy型チェックが不合格"
        ]
    )


@pytest.fixture
def mock_mutation_report_pass():
    """合格するTier 2レポート"""
    return MutationReport(
        passed=True,
        mutation_score=85.0,
        total_mutants=20,
        killed=17,
        survived=3,
        timeout=0,
        suspicious=0,
        survived_mutants=[],
        feedback="ミューテーションスコアが基準を満たしています。"
    )


@pytest.fixture
def mock_mutation_report_fail():
    """不合格のTier 2レポート"""
    survived = [
        Mutant(
            file_path="example.py",
            line_number=10,
            mutator="BinaryOperator",
            original_code="x + y",
            mutated_code="x - y",
            status="survived"
        )
    ]
    return MutationReport(
        passed=False,
        mutation_score=65.0,
        total_mutants=20,
        killed=13,
        survived=7,
        timeout=0,
        suspicious=0,
        survived_mutants=survived,
        feedback="ミューテーションスコアが不足しています。"
    )


@pytest.fixture
def temp_source_file():
    """テスト用のソースファイルを作成"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b
""")
        source_path = f.name
    yield source_path
    os.unlink(source_path)


@pytest.fixture
def temp_test_file():
    """テスト用のテストファイルを作成"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""
import pytest

def test_add():
    from example import add
    assert add(2, 3) == 5

def test_subtract():
    from example import subtract
    assert subtract(5, 3) == 2
""")
        test_path = f.name
    yield test_path
    os.unlink(test_path)


class TestGuardianQualityGates:
    """Guardian Agent品質ゲート統合テスト"""

    def test_run_quality_gates_all_pass(
        self,
        setup_guardian,
        mock_constitution,
        mock_quality_report_pass,
        mock_mutation_report_pass
    ):
        """Tier 1とTier 2が両方合格する場合"""
        guardian = GuardianAgent()

        with patch('nexuscore.agents.guardian_agent.analyze_code_quality') as mock_analyze:
            with patch('nexuscore.agents.guardian_agent.MutationTesterAgent') as mock_mutation_cls:
                mock_analyze.return_value = mock_quality_report_pass
                mock_mutation_agent = Mock()
                mock_mutation_agent.run_mutation_testing.return_value = mock_mutation_report_pass
                mock_mutation_cls.return_value = mock_mutation_agent

                result = guardian._run_quality_gates(
                    source_path="src/example.py",
                    test_path="tests/test_example.py",
                    constitution=mock_constitution
                )

                assert result["overall_passed"] is True
                assert result["tier1"] == mock_quality_report_pass
                assert result["tier2"] == mock_mutation_report_pass
                assert len(result["violations"]) == 0

    def test_run_quality_gates_tier1_fail(
        self,
        setup_guardian,
        mock_constitution,
        mock_quality_report_fail,
        mock_mutation_report_pass
    ):
        """Tier 1が不合格の場合"""
        guardian = GuardianAgent()

        with patch('nexuscore.agents.guardian_agent.analyze_code_quality') as mock_analyze:
            with patch('nexuscore.agents.guardian_agent.MutationTesterAgent') as mock_mutation_cls:
                mock_analyze.return_value = mock_quality_report_fail
                mock_mutation_agent = Mock()
                mock_mutation_agent.run_mutation_testing.return_value = mock_mutation_report_pass
                mock_mutation_cls.return_value = mock_mutation_agent

                result = guardian._run_quality_gates(
                    source_path="src/example.py",
                    test_path="tests/test_example.py",
                    constitution=mock_constitution
                )

                assert result["overall_passed"] is False
                assert result["tier1"] == mock_quality_report_fail
                assert len(result["violations"]) == 3  # カバレッジ、Pylint、MyPy

    def test_run_quality_gates_tier2_fail(
        self,
        setup_guardian,
        mock_constitution,
        mock_quality_report_pass,
        mock_mutation_report_fail
    ):
        """Tier 2が不合格の場合"""
        guardian = GuardianAgent()

        with patch('nexuscore.agents.guardian_agent.analyze_code_quality') as mock_analyze:
            with patch('nexuscore.agents.guardian_agent.MutationTesterAgent') as mock_mutation_cls:
                mock_analyze.return_value = mock_quality_report_pass
                mock_mutation_agent = Mock()
                mock_mutation_agent.run_mutation_testing.return_value = mock_mutation_report_fail
                mock_mutation_cls.return_value = mock_mutation_agent

                result = guardian._run_quality_gates(
                    source_path="src/example.py",
                    test_path="tests/test_example.py",
                    constitution=mock_constitution
                )

                assert result["overall_passed"] is False
                assert result["tier2"] == mock_mutation_report_fail
                assert any("Tier 2不合格" in v for v in result["violations"])

    def test_review_with_quality_gates_reject_on_quality_fail(
        self,
        setup_guardian,
        mock_constitution,
        mock_quality_report_fail,
        mock_mutation_report_pass
    ):
        """品質ゲート不合格時にREJECTを返す"""
        guardian = GuardianAgent()

        with patch.object(guardian, '_run_quality_gates') as mock_run_qg:
            mock_run_qg.return_value = {
                "tier1": mock_quality_report_fail,
                "tier2": mock_mutation_report_pass,
                "overall_passed": False,
                "violations": ["カバレッジ不足", "Pylint不足"]
            }

            result = guardian.review_with_quality_gates(
                source_path="src/example.py",
                test_path="tests/test_example.py",
                code_draft="def foo(): pass",
                test_code="def test_foo(): pass",
                test_result="PASSED",
                testimony="実装しました",
                constitution_dict=mock_constitution,
                task_description="新機能追加"
            )

            assert result["decision"] == "REJECT"
            assert result["reason"] == "品質ゲート不合格"
            assert "カバレッジ不足" in result["feedback_for_coder"]
            assert "quality_gates" in result

    def test_review_with_quality_gates_llm_review_on_pass(
        self,
        setup_guardian,
        mock_constitution,
        mock_quality_report_pass,
        mock_mutation_report_pass
    ):
        """品質ゲート合格時にLLMレビューを実行"""
        guardian = GuardianAgent()

        with patch.object(guardian, '_run_quality_gates') as mock_run_qg:
            with patch.object(guardian, 'execute_llm_task') as mock_llm:
                mock_run_qg.return_value = {
                    "tier1": mock_quality_report_pass,
                    "tier2": mock_mutation_report_pass,
                    "overall_passed": True,
                    "violations": []
                }
                mock_llm.return_value = '{"decision": "APPROVE", "reason": "コードは優れています"}'

                result = guardian.review_with_quality_gates(
                    source_path="src/example.py",
                    test_path="tests/test_example.py",
                    code_draft="def foo(): pass",
                    test_code="def test_foo(): pass",
                    test_result="PASSED",
                    testimony="実装しました",
                    constitution_dict=mock_constitution,
                    task_description="新機能追加"
                )

                assert result["decision"] == "APPROVE"
                assert result["reason"] == "コードは優れています"
                assert "quality_gates" in result
                mock_llm.assert_called_once()

    def test_review_and_commit_with_quality_gates_enabled(
        self,
        setup_guardian,
        mock_constitution
    ):
        """review_and_commitで品質ゲートを有効化"""
        guardian = GuardianAgent()

        with patch.object(guardian, 'review_with_quality_gates') as mock_review_qg:
            mock_review_qg.return_value = {
                "decision": "APPROVE",
                "reason": "全て合格",
                "quality_gates": {"overall_passed": True}
            }

            result = guardian.review_and_commit(
                code_draft="def foo(): pass",
                test_code="def test_foo(): pass",
                test_result="PASSED",
                testimony="実装しました",
                constitution=str(mock_constitution),
                task_description="新機能追加",
                changed_files=["example.py"],
                enable_quality_gates=True,
                source_path="src/example.py",
                test_path="tests/test_example.py",
                allow_commit=False  # コミットはスキップ
            )

            assert result["decision"] == "APPROVE"
            mock_review_qg.assert_called_once()

    def test_review_and_commit_quality_gates_missing_paths(self, setup_guardian):
        """品質ゲート有効時にパスが不足している場合"""
        guardian = GuardianAgent()

        result = guardian.review_and_commit(
            code_draft="def foo(): pass",
            test_code="def test_foo(): pass",
            test_result="PASSED",
            testimony="実装しました",
            constitution="{}",
            task_description="新機能追加",
            changed_files=["example.py"],
            enable_quality_gates=True,
            # source_path と test_path を省略
            allow_commit=False
        )

        assert result["decision"] == "REJECT"
        assert "source_path と test_path が必須" in result["reason"]

    def test_format_quality_gates_summary(
        self,
        setup_guardian,
        mock_quality_report_pass,
        mock_mutation_report_pass
    ):
        """品質ゲート結果のフォーマット"""
        guardian = GuardianAgent()

        quality_gates_result = {
            "tier1": mock_quality_report_pass,
            "tier2": mock_mutation_report_pass,
            "overall_passed": True,
            "violations": []
        }

        summary = guardian._format_quality_gates_summary(quality_gates_result)

        assert "✅ 全ての品質ゲートに合格" in summary
        assert "Tier 1: コード品質" in summary
        assert "カバレッジ: 95.0%" in summary
        assert "Pylint: 8.5/10" in summary
        assert "Tier 2: テスト品質" in summary
        assert "ミューテーションスコア: 85.0%" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
