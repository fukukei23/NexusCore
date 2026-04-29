"""
test_test_generator_prompt.py

テスト生成プロンプトテンプレートのテスト。
"""

from __future__ import annotations

from nexuscore.utils.test_generator_prompt import (
    build_specification_based_test_prompt,
    build_test_generation_prompt,
)


class TestBuildTestGenerationPrompt:
    """build_test_generation_prompt() のテスト"""

    def test_basic_prompt(self):
        """基本的なプロンプト生成"""
        prompt = build_test_generation_prompt(
            target_file_path="src/nexuscore/utils/file_utils.py",
            target_code="def hello(): return 'world'",
            test_level="unit",
            risk_level="B",
            strategy="ai_first_only",
            min_coverage=70,
        )

        assert "file_utils.py" in prompt
        assert "def hello()" in prompt
        assert "ユニットテスト" in prompt or "unit" in prompt.lower()
        assert "70%" in prompt
        assert "pytest" in prompt.lower()

    def test_with_existing_tests(self):
        """既存テストを含むプロンプト"""
        prompt = build_test_generation_prompt(
            target_file_path="src/example.py",
            target_code="def func(): pass",
            existing_tests="def test_func(): assert func() is None",
            test_level="unit",
            risk_level="B",
            strategy="ai_first_only",
        )

        assert "既存テスト" in prompt
        assert "test_func" in prompt

    def test_risk_level_s(self):
        """リスクランクSのプロンプト"""
        prompt = build_test_generation_prompt(
            target_file_path="src/sandbox_runner.py",
            target_code="def run(): pass",
            test_level="component",
            risk_level="S",
            strategy="human_design + ai_augment",
        )

        assert "クリティカル" in prompt or "critical" in prompt.lower()
        assert "安全性" in prompt or "safety" in prompt.lower()

    def test_with_requirements(self):
        """追加要件を含むプロンプト"""
        requirements = [
            "絶対に外部ファイルを削除してはいけない",
            "サンドボックス内でのみ実行されること",
        ]

        prompt = build_test_generation_prompt(
            target_file_path="src/sandbox_runner.py",
            target_code="def run(): pass",
            test_level="component",
            risk_level="S",
            strategy="human_design + ai_augment",
            requirements=requirements,
        )

        assert "追加要件" in prompt
        assert "絶対に外部ファイルを削除してはいけない" in prompt
        assert "サンドボックス内でのみ実行されること" in prompt

    def test_e2e_level(self):
        """E2E レベルのプロンプト"""
        prompt = build_test_generation_prompt(
            target_file_path="src/orchestrator.py",
            target_code="def run(): pass",
            test_level="e2e",
            risk_level="A",
            strategy="ai_first + human_review",
        )

        assert "E2E" in prompt or "シナリオ" in prompt or "scenario" in prompt.lower()


class TestBuildSpecificationBasedTestPrompt:
    """build_specification_based_test_prompt() のテスト"""

    def test_basic_spec_prompt(self):
        """基本的な仕様ベースプロンプト"""
        specifications = [
            "絶対に外部ファイルを削除してはいけない",
            "実行時間は5秒以内であること",
        ]

        prompt = build_specification_based_test_prompt(
            module_name="sandbox_runner",
            specifications=specifications,
        )

        assert "sandbox_runner" in prompt
        assert "絶対に外部ファイルを削除してはいけない" in prompt
        assert "実行時間は5秒以内であること" in prompt
        assert "仕様" in prompt

    def test_with_existing_code(self):
        """既存コードを含む仕様ベースプロンプト"""
        prompt = build_specification_based_test_prompt(
            module_name="file_utils",
            specifications=["ファイルパスは正規化されること"],
            existing_code="def normalize_path(p): return p",
        )

        assert "file_utils" in prompt
        assert "normalize_path" in prompt
        assert "ファイルパスは正規化されること" in prompt
