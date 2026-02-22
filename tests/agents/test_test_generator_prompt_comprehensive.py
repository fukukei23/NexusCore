"""
============================================================================
Comprehensive Tests for test_generator_prompt module
============================================================================
高品質テストの原則:
- プロンプト生成ロジックをすべてテスト
- 各オプションの組み合わせをカバー
- エッジケースを含める
============================================================================
"""

from nexuscore.agents.test_generator_prompt import (
    build_specification_based_test_prompt,
    build_test_generation_prompt,
)

# ============================================================================
# Tests: build_test_generation_prompt
# ============================================================================


class TestBuildTestGenerationPrompt:
    def test_minimal_prompt(self):
        """最小限のパラメータでプロンプトを生成"""
        prompt = build_test_generation_prompt(
            target_file_path="src/example.py",
            target_code="def hello(): return 'world'",
        )

        assert "src/example.py" in prompt
        assert "def hello(): return 'world'" in prompt
        assert "テスト生成タスク" in prompt
        assert "```python" in prompt

    def test_with_existing_tests(self):
        """既存テストコードが含まれる"""
        prompt = build_test_generation_prompt(
            target_file_path="src/example.py",
            target_code="def add(a, b): return a + b",
            existing_tests="def test_add(): assert add(1, 2) == 3",
        )

        assert "既存テスト" in prompt
        assert "def test_add()" in prompt

    def test_with_unit_test_level(self):
        """ユニットテストレベルの指示が含まれる"""
        prompt = build_test_generation_prompt(
            target_file_path="src/example.py",
            target_code="code",
            test_level="unit",
        )

        assert "ユニットテスト" in prompt
        assert "各関数の入出力の検証" in prompt
        assert "外部依存（LLM API、ファイルシステム、サブプロセス）はモック化してください" in prompt

    def test_with_component_test_level(self):
        """コンポーネントテストレベルの指示が含まれる"""
        prompt = build_test_generation_prompt(
            target_file_path="src/example.py",
            target_code="code",
            test_level="component",
        )

        assert "コンポーネントテスト" in prompt
        assert "モジュール全体の振る舞いの検証" in prompt

    def test_with_e2e_test_level(self):
        """E2Eテストレベルの指示が含まれる"""
        prompt = build_test_generation_prompt(
            target_file_path="src/example.py",
            target_code="code",
            test_level="e2e",
        )

        assert "E2E / シナリオテスト" in prompt
        assert "エンドツーエンドのワークフローの検証" in prompt

    def test_with_risk_level_s(self):
        """リスクランクSの指示が含まれる"""
        prompt = build_test_generation_prompt(
            target_file_path="src/example.py",
            target_code="code",
            risk_level="S",
        )

        assert "クリティカルモジュール" in prompt
        assert "安全性に関するテストを必ず含める" in prompt
        assert "人間によるレビューが必須です" in prompt

    def test_with_risk_level_a(self):
        """リスクランクAの指示が含まれる"""
        prompt = build_test_generation_prompt(
            target_file_path="src/example.py",
            target_code="code",
            risk_level="A",
        )

        assert "重要モジュール" in prompt
        assert "人間によるレビューを推奨します" in prompt

    def test_with_risk_level_b(self):
        """リスクランクBの指示が含まれる"""
        prompt = build_test_generation_prompt(
            target_file_path="src/example.py",
            target_code="code",
            risk_level="B",
        )

        assert "非クリティカルモジュール" in prompt

    def test_with_webapp_module(self):
        """webappモジュールの特別な指示が含まれる"""
        prompt = build_test_generation_prompt(
            target_file_path="src/example.py",
            target_code="code",
            module_name="webapp.views",
        )

        assert "Web/API テストの特別な要件" in prompt
        assert "Flask" in prompt
        assert "HTTP エンドポイント" in prompt
        assert "ステータスコード" in prompt
        assert "認証が必要なエンドポイント" in prompt

    def test_with_non_webapp_module(self):
        """非webappモジュールではWeb指示が含まれない"""
        prompt = build_test_generation_prompt(
            target_file_path="src/example.py",
            target_code="code",
            module_name="agents.base_agent",
        )

        assert "Web/API テストの特別な要件" not in prompt
        assert "Flask" not in prompt

    def test_with_additional_requirements_string(self):
        """追加要件（文字列）が含まれる"""
        prompt = build_test_generation_prompt(
            target_file_path="src/example.py",
            target_code="code",
            additional_requirements="必ずタイムゾーンを考慮すること",
        )

        assert "追加要件" in prompt
        assert "必ずタイムゾーンを考慮すること" in prompt

    def test_with_requirements_list(self):
        """追加要件（リスト）が含まれる"""
        prompt = build_test_generation_prompt(
            target_file_path="src/example.py",
            target_code="code",
            requirements=["並列処理のテスト", "エラーハンドリングの確認"],
        )

        assert "追加要件・懸念事項" in prompt
        assert "1. 並列処理のテスト" in prompt
        assert "2. エラーハンドリングの確認" in prompt

    def test_with_min_coverage(self):
        """目標カバレッジが指定される"""
        prompt = build_test_generation_prompt(
            target_file_path="src/example.py",
            target_code="code",
            min_coverage=85,
        )

        assert "目標カバレッジ" in prompt
        assert "85% 以上" in prompt

    def test_includes_output_format(self):
        """出力形式の指示が含まれる"""
        prompt = build_test_generation_prompt(
            target_file_path="src/example.py",
            target_code="code",
        )

        assert "出力形式" in prompt
        assert "import pytest" in prompt
        assert "from unittest.mock import Mock, patch, MagicMock" in prompt

    def test_includes_cautions(self):
        """注意事項が含まれる"""
        prompt = build_test_generation_prompt(
            target_file_path="src/example.py",
            target_code="code",
        )

        assert "注意事項" in prompt
        assert "`time.sleep` は使わない" in prompt
        assert "外部API依存は必ずモック化" in prompt
        assert "実ファイル削除は行わない" in prompt

    def test_full_options(self):
        """すべてのオプションを指定"""
        prompt = build_test_generation_prompt(
            target_file_path="src/webapp/views.py",
            target_code="def index(): return render_template('index.html')",
            existing_tests="def test_index(): pass",
            test_level="component",
            risk_level="A",
            strategy="ai_first_only",
            requirements=["CSRF保護", "XSS対策"],
            min_coverage=90,
            module_name="webapp.views",
            additional_requirements="認証必須エンドポイントのテストを含めること",
        )

        assert "src/webapp/views.py" in prompt
        assert "既存テスト" in prompt
        assert "コンポーネントテスト" in prompt
        assert "重要モジュール" in prompt
        assert "1. CSRF保護" in prompt
        assert "2. XSS対策" in prompt
        assert "90% 以上" in prompt
        assert "Web/API テストの特別な要件" in prompt
        assert "認証必須エンドポイントのテストを含めること" in prompt


# ============================================================================
# Tests: build_specification_based_test_prompt
# ============================================================================


class TestBuildSpecificationBasedTestPrompt:
    def test_minimal_prompt(self):
        """最小限のパラメータでプロンプトを生成"""
        prompt = build_specification_based_test_prompt(
            module_name="auth.service",
            specifications=["ユーザーはログインできる", "無効なパスワードは拒否される"],
        )

        assert "auth.service" in prompt
        assert "仕様ベーステスト生成タスク" in prompt
        assert "1. ユーザーはログインできる" in prompt
        assert "2. 無効なパスワードは拒否される" in prompt

    def test_with_existing_code(self):
        """既存コードが含まれる"""
        prompt = build_specification_based_test_prompt(
            module_name="auth.service",
            specifications=["仕様1"],
            existing_code="def login(username, password): ...",
        )

        assert "既存コード" in prompt
        assert "def login(username, password): ..." in prompt

    def test_with_multiple_specifications(self):
        """複数の仕様が番号付きリストで含まれる"""
        specs = [
            "APIキーは必ずSHA-256でハッシュ化される",
            "同じAPIキーを複数回登録できない",
            "削除されたAPIキーは使用できない",
        ]
        prompt = build_specification_based_test_prompt(
            module_name="api.keys",
            specifications=specs,
        )

        assert "1. APIキーは必ずSHA-256でハッシュ化される" in prompt
        assert "2. 同じAPIキーを複数回登録できない" in prompt
        assert "3. 削除されたAPIキーは使用できない" in prompt

    def test_includes_output_format(self):
        """出力形式の指示が含まれる"""
        prompt = build_specification_based_test_prompt(
            module_name="module",
            specifications=["spec"],
        )

        assert "出力形式" in prompt
        assert "def test_<仕様の要約>():" in prompt
        assert "仕様: <元の仕様文>" in prompt

    def test_includes_cautions(self):
        """注意事項が含まれる"""
        prompt = build_specification_based_test_prompt(
            module_name="module",
            specifications=["spec"],
        )

        assert "注意事項" in prompt
        assert "仕様の意図を正確に反映したテストを書く" in prompt
        assert "仕様が破られた場合にテストが失敗することを確認する" in prompt

    def test_empty_specifications_list(self):
        """空の仕様リストでもエラーにならない"""
        prompt = build_specification_based_test_prompt(
            module_name="module",
            specifications=[],
        )

        assert "module" in prompt
        assert "仕様ベーステスト生成タスク" in prompt


# ============================================================================
# Tests: Integration scenarios
# ============================================================================


class TestIntegrationScenarios:
    def test_webapp_module_with_high_risk(self):
        """Webappモジュール + 高リスクの組み合わせ"""
        prompt = build_test_generation_prompt(
            target_file_path="src/webapp/auth.py",
            target_code="def login_view(): ...",
            test_level="component",
            risk_level="S",
            module_name="webapp.auth",
            min_coverage=95,
        )

        assert "Web/API テストの特別な要件" in prompt
        assert "クリティカルモジュール" in prompt
        assert "95% 以上" in prompt

    def test_agent_module_with_unit_tests(self):
        """Agentモジュール + ユニットテスト"""
        prompt = build_test_generation_prompt(
            target_file_path="src/agents/base_agent.py",
            target_code="class BaseAgent: ...",
            test_level="unit",
            risk_level="A",
            requirements=["LLM呼び出しは必ずモック化", "タイムアウト処理"],
        )

        assert "ユニットテスト" in prompt
        assert "重要モジュール" in prompt
        assert "LLM呼び出しは必ずモック化" in prompt
        # Webapp指示は含まれない
        assert "Web/API テストの特別な要件" not in prompt
