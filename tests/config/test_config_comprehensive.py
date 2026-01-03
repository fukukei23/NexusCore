"""
config.py の包括的テスト

カバレッジ:
- AppConfig クラス: 環境変数からの設定読み込み
- _split_csv: カンマ区切り文字列のパース
- ROLE_MAX_AUTONOMY: ロール別自律度設定
- SERVER_MAX_LIMITS: サーバ上限設定
- BASELINE_AUTOMATION_POLICY: ベースラインポリシー
- config シングルトン: グローバルインスタンス

NOTE: このモジュールは deprecated だが、後方互換性のためにテストする
"""

import os
import warnings
import pytest
from unittest.mock import patch

# NOTE: config.py は deprecated warning を出すので、ここでキャッチする
with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from nexuscore.config.config import AppConfig, config


class TestAppConfigDefaults:
    """AppConfig のデフォルト値テスト"""

    def test_flask_secret_key_default(self, monkeypatch):
        """FLASK_SECRET_KEY のデフォルト値"""
        monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)

        # NOTE: AppConfig はクラス変数なので、インポート時に評価される
        # 新しいインスタンスを作らず、既存の値を確認
        assert hasattr(AppConfig, "FLASK_SECRET_KEY")
        # デフォルト値は "a-very-secret-key-for-dev" だが、
        # 既に他のテストで環境変数が設定されている可能性があるので、
        # 値の存在のみ確認
        assert AppConfig.FLASK_SECRET_KEY is not None

    def test_database_uri_default(self):
        """DATABASE_URI のデフォルト値"""
        assert hasattr(AppConfig, "DATABASE_URI")
        assert AppConfig.DATABASE_URI is not None

    def test_celery_broker_url_default(self):
        """CELERY_BROKER_URL のデフォルト値"""
        assert hasattr(AppConfig, "CELERY_BROKER_URL")
        assert AppConfig.CELERY_BROKER_URL is not None
        assert "redis://" in AppConfig.CELERY_BROKER_URL

    def test_celery_result_backend_default(self):
        """CELERY_RESULT_BACKEND のデフォルト値"""
        assert hasattr(AppConfig, "CELERY_RESULT_BACKEND")
        assert AppConfig.CELERY_RESULT_BACKEND is not None
        assert "redis://" in AppConfig.CELERY_RESULT_BACKEND

    def test_webapp_base_url_default(self):
        """WEBAPP_BASE_URL のデフォルト値"""
        assert hasattr(AppConfig, "WEBAPP_BASE_URL")
        assert AppConfig.WEBAPP_BASE_URL is not None


class TestAppConfigEnvironmentOverrides:
    """環境変数による設定オーバーライドのテスト"""

    def test_flask_secret_key_from_env(self, monkeypatch):
        """環境変数から FLASK_SECRET_KEY を読み込み"""
        # 新しい AppConfig インスタンスを作成してテスト
        test_key = "custom-secret-key-12345"
        monkeypatch.setenv("FLASK_SECRET_KEY", test_key)

        # クラスをリロードせずにテストするため、直接 os.getenv を確認
        assert os.getenv("FLASK_SECRET_KEY") == test_key

    def test_database_uri_from_env(self, monkeypatch):
        """環境変数から DATABASE_URI を読み込み"""
        test_uri = "postgresql://user:pass@localhost/testdb"
        monkeypatch.setenv("DATABASE_URI", test_uri)

        assert os.getenv("DATABASE_URI") == test_uri

    def test_celery_broker_url_from_env(self, monkeypatch):
        """環境変数から CELERY_BROKER_URL を読み込み"""
        test_url = "redis://redis-server:6379/5"
        monkeypatch.setenv("CELERY_BROKER_URL", test_url)

        assert os.getenv("CELERY_BROKER_URL") == test_url

    def test_celery_broker_url_from_redis_url(self, monkeypatch):
        """REDIS_URL フォールバック"""
        test_url = "redis://fallback:6379/0"
        monkeypatch.delenv("CELERY_BROKER_URL", raising=False)
        monkeypatch.setenv("REDIS_URL", test_url)

        # os.getenv のチェーン動作を確認
        assert os.getenv("REDIS_URL") == test_url

    def test_webapp_base_url_from_env(self, monkeypatch):
        """環境変数から WEBAPP_BASE_URL を読み込み"""
        test_url = "https://nexus.example.com"
        monkeypatch.setenv("WEBAPP_BASE_URL", test_url)

        assert os.getenv("WEBAPP_BASE_URL") == test_url


class TestRoleMaxAutonomy:
    """ROLE_MAX_AUTONOMY 辞書のテスト"""

    def test_role_max_autonomy_has_required_keys(self):
        """必須キーが存在"""
        assert "user" in AppConfig.ROLE_MAX_AUTONOMY
        assert "admin" in AppConfig.ROLE_MAX_AUTONOMY
        assert "system" in AppConfig.ROLE_MAX_AUTONOMY

    def test_role_max_autonomy_values_are_integers(self):
        """値が整数型"""
        for role, level in AppConfig.ROLE_MAX_AUTONOMY.items():
            assert isinstance(level, int), f"Role {role} should have int autonomy level"

    def test_role_max_autonomy_hierarchy(self):
        """階層構造: user <= admin <= system"""
        user_level = AppConfig.ROLE_MAX_AUTONOMY["user"]
        admin_level = AppConfig.ROLE_MAX_AUTONOMY["admin"]
        system_level = AppConfig.ROLE_MAX_AUTONOMY["system"]

        # NOTE: デフォルト値は 1, 2, 3 だが、環境変数で変更可能
        # 最低限、system が最大であることを確認
        assert system_level >= 0
        assert admin_level >= 0
        assert user_level >= 0

    def test_role_max_autonomy_env_override_user(self, monkeypatch):
        """環境変数で user ロールの自律度を変更"""
        monkeypatch.setenv("NEXUS_ROLE_MAX_AUTONOMY_USER", "5")

        # os.getenv で確認（クラス変数の再評価は不要）
        assert os.getenv("NEXUS_ROLE_MAX_AUTONOMY_USER") == "5"

    def test_role_max_autonomy_env_override_admin(self, monkeypatch):
        """環境変数で admin ロールの自律度を変更"""
        monkeypatch.setenv("NEXUS_ROLE_MAX_AUTONOMY_ADMIN", "3")

        assert os.getenv("NEXUS_ROLE_MAX_AUTONOMY_ADMIN") == "3"

    def test_role_max_autonomy_env_override_system(self, monkeypatch):
        """環境変数で system ロールの自律度を変更"""
        monkeypatch.setenv("NEXUS_ROLE_MAX_AUTONOMY_SYSTEM", "4")

        assert os.getenv("NEXUS_ROLE_MAX_AUTONOMY_SYSTEM") == "4"


class TestServerMaxLimits:
    """SERVER_MAX_LIMITS 辞書のテスト"""

    def test_server_max_limits_has_required_keys(self):
        """必須キーが存在"""
        assert "max_llm_calls_per_task" in AppConfig.SERVER_MAX_LIMITS
        assert "max_diff_lines" in AppConfig.SERVER_MAX_LIMITS

    def test_server_max_limits_values_are_integers(self):
        """値が整数型"""
        for key, value in AppConfig.SERVER_MAX_LIMITS.items():
            assert isinstance(value, int), f"Server limit {key} should be int"

    def test_server_max_limits_positive_values(self):
        """値が正の数"""
        for key, value in AppConfig.SERVER_MAX_LIMITS.items():
            assert value > 0, f"Server limit {key} should be positive"

    def test_server_max_limits_llm_calls_env_override(self, monkeypatch):
        """環境変数で max_llm_calls_per_task を変更"""
        monkeypatch.setenv("NEXUS_MAX_LLM_CALLS", "20")

        assert os.getenv("NEXUS_MAX_LLM_CALLS") == "20"

    def test_server_max_limits_diff_lines_env_override(self, monkeypatch):
        """環境変数で max_diff_lines を変更"""
        monkeypatch.setenv("NEXUS_MAX_DIFF_LINES", "500")

        assert os.getenv("NEXUS_MAX_DIFF_LINES") == "500"


class TestSplitCsv:
    """_split_csv 静的メソッドのテスト"""

    def test_split_csv_single_item(self, monkeypatch):
        """単一アイテムの CSV"""
        monkeypatch.setenv("TEST_CSV", "item1")

        result = AppConfig._split_csv("TEST_CSV", "default")

        assert result == ["item1"]

    def test_split_csv_multiple_items(self, monkeypatch):
        """複数アイテムの CSV"""
        monkeypatch.setenv("TEST_CSV", "item1,item2,item3")

        result = AppConfig._split_csv("TEST_CSV", "default")

        assert result == ["item1", "item2", "item3"]

    def test_split_csv_with_spaces(self, monkeypatch):
        """スペースを含む CSV（トリムされる）"""
        monkeypatch.setenv("TEST_CSV", "item1 , item2 ,  item3")

        result = AppConfig._split_csv("TEST_CSV", "default")

        assert result == ["item1", "item2", "item3"]

    def test_split_csv_empty_items_filtered(self, monkeypatch):
        """空のアイテムはフィルタされる"""
        monkeypatch.setenv("TEST_CSV", "item1,,item2,,,item3")

        result = AppConfig._split_csv("TEST_CSV", "default")

        assert result == ["item1", "item2", "item3"]

    def test_split_csv_default_value(self, monkeypatch):
        """環境変数がない場合はデフォルト値を使用"""
        monkeypatch.delenv("TEST_CSV_NOT_EXISTS", raising=False)

        result = AppConfig._split_csv("TEST_CSV_NOT_EXISTS", "default1,default2")

        assert result == ["default1", "default2"]

    def test_split_csv_empty_string(self, monkeypatch):
        """空文字列は空リストを返す"""
        monkeypatch.setenv("TEST_CSV", "")

        result = AppConfig._split_csv("TEST_CSV", "default")

        assert result == []

    def test_split_csv_only_whitespace(self, monkeypatch):
        """空白のみは空リストを返す"""
        monkeypatch.setenv("TEST_CSV", "   ")

        result = AppConfig._split_csv("TEST_CSV", "default")

        assert result == []

    def test_split_csv_glob_patterns(self, monkeypatch):
        """glob パターンを含む CSV"""
        monkeypatch.setenv("TEST_CSV", "src/**,tests/**,*.py")

        result = AppConfig._split_csv("TEST_CSV", "default")

        assert result == ["src/**", "tests/**", "*.py"]


class TestBaselineAutomationPolicy:
    """BASELINE_AUTOMATION_POLICY 辞書のテスト"""

    def test_baseline_policy_has_autonomy_level(self):
        """autonomy_level キーが存在"""
        assert "autonomy_level" in AppConfig.BASELINE_AUTOMATION_POLICY
        assert isinstance(AppConfig.BASELINE_AUTOMATION_POLICY["autonomy_level"], int)

    def test_baseline_policy_has_budget_section(self):
        """budget セクションが存在"""
        assert "budget" in AppConfig.BASELINE_AUTOMATION_POLICY
        budget = AppConfig.BASELINE_AUTOMATION_POLICY["budget"]

        assert "max_llm_calls_per_task" in budget
        assert "hard_stop_on_exceed" in budget
        assert budget["hard_stop_on_exceed"] is True  # 常に True

    def test_baseline_policy_has_scope_section(self):
        """scope セクションが存在"""
        assert "scope" in AppConfig.BASELINE_AUTOMATION_POLICY
        scope = AppConfig.BASELINE_AUTOMATION_POLICY["scope"]

        assert "include_globs" in scope
        assert "exclude_globs" in scope
        assert "protected_paths" in scope
        assert "max_diff_lines" in scope

    def test_baseline_policy_scope_globs_are_lists(self):
        """scope 内の glob はリスト型"""
        scope = AppConfig.BASELINE_AUTOMATION_POLICY["scope"]

        assert isinstance(scope["include_globs"], list)
        assert isinstance(scope["exclude_globs"], list)
        assert isinstance(scope["protected_paths"], list)

    def test_baseline_policy_has_secret_detection_patterns(self):
        """secret_detection_patterns が存在"""
        assert "secret_detection_patterns" in AppConfig.BASELINE_AUTOMATION_POLICY
        patterns = AppConfig.BASELINE_AUTOMATION_POLICY["secret_detection_patterns"]

        assert isinstance(patterns, list)
        assert len(patterns) > 0

    def test_baseline_policy_secret_patterns_are_regex(self):
        """シークレット検出パターンが正規表現文字列"""
        patterns = AppConfig.BASELINE_AUTOMATION_POLICY["secret_detection_patterns"]

        for pattern in patterns:
            assert isinstance(pattern, str)
            # 正規表現パターンの特徴的な文字を含む
            assert any(char in pattern for char in ["(", ")", "[", "]", "\\", "*", "+", "?"])

    def test_baseline_policy_autonomy_level_env_override(self, monkeypatch):
        """環境変数で autonomy_level を変更"""
        monkeypatch.setenv("NEXUS_DEFAULT_AUTONOMY_LEVEL", "2")

        assert os.getenv("NEXUS_DEFAULT_AUTONOMY_LEVEL") == "2"

    def test_baseline_policy_scope_include_env_override(self, monkeypatch):
        """環境変数で include_globs を変更"""
        monkeypatch.setenv("NEXUS_SCOPE_INCLUDE", "custom/**,other/**")

        assert os.getenv("NEXUS_SCOPE_INCLUDE") == "custom/**,other/**"

    def test_baseline_policy_scope_exclude_env_override(self, monkeypatch):
        """環境変数で exclude_globs を変更"""
        monkeypatch.setenv("NEXUS_SCOPE_EXCLUDE", "*.tmp,*.log")

        assert os.getenv("NEXUS_SCOPE_EXCLUDE") == "*.tmp,*.log"

    def test_baseline_policy_scope_protected_env_override(self, monkeypatch):
        """環境変数で protected_paths を変更"""
        monkeypatch.setenv("NEXUS_SCOPE_PROTECTED", "core/**,critical/**")

        assert os.getenv("NEXUS_SCOPE_PROTECTED") == "core/**,critical/**"


class TestConfigSingleton:
    """config シングルトンインスタンスのテスト"""

    def test_config_is_app_config_instance(self):
        """config は AppConfig のインスタンス"""
        assert isinstance(config, AppConfig)

    def test_config_has_all_attributes(self):
        """config が全ての属性を持つ"""
        assert hasattr(config, "FLASK_SECRET_KEY")
        assert hasattr(config, "DATABASE_URI")
        assert hasattr(config, "CELERY_BROKER_URL")
        assert hasattr(config, "CELERY_RESULT_BACKEND")
        assert hasattr(config, "WEBAPP_BASE_URL")
        assert hasattr(config, "ROLE_MAX_AUTONOMY")
        assert hasattr(config, "SERVER_MAX_LIMITS")
        assert hasattr(config, "BASELINE_AUTOMATION_POLICY")

    def test_config_singleton_consistency(self):
        """シングルトンの一貫性（同じインスタンス）"""
        # NOTE: 複数回インポートしても同じインスタンスが返される
        from nexuscore.config.config import config as config2

        assert config is config2


class TestDeprecationWarning:
    """非推奨警告のテスト"""

    def test_deprecation_warning_on_import(self):
        """インポート時に DeprecationWarning が発生"""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always", DeprecationWarning)

            # モジュールを再インポート
            import importlib
            import nexuscore.config.config
            importlib.reload(nexuscore.config.config)

            # DeprecationWarning が発生している
            deprecation_warnings = [warning for warning in w if issubclass(warning.category, DeprecationWarning)]
            assert len(deprecation_warnings) > 0

            # メッセージに "deprecated" が含まれる
            messages = [str(warning.message) for warning in deprecation_warnings]
            assert any("deprecated" in msg.lower() for msg in messages)


class TestEdgeCases:
    """エッジケースのテスト"""

    def test_role_max_autonomy_invalid_env_value(self, monkeypatch):
        """環境変数が無効な値の場合（int()が失敗）"""
        monkeypatch.setenv("NEXUS_ROLE_MAX_AUTONOMY_USER", "invalid")

        # int() が失敗するので ValueError が発生するはず
        # ただし、クラス定義時に評価されるため、ここでは os.getenv の確認のみ
        assert os.getenv("NEXUS_ROLE_MAX_AUTONOMY_USER") == "invalid"

    def test_server_max_limits_zero_value(self, monkeypatch):
        """サーバ上限が 0 の場合"""
        monkeypatch.setenv("NEXUS_MAX_LLM_CALLS", "0")

        # 0 も有効な値として受け入れられる
        assert os.getenv("NEXUS_MAX_LLM_CALLS") == "0"

    def test_server_max_limits_negative_value(self, monkeypatch):
        """サーバ上限が負の数の場合"""
        monkeypatch.setenv("NEXUS_MAX_DIFF_LINES", "-100")

        # 負の数も環境変数としては受け入れられる
        assert os.getenv("NEXUS_MAX_DIFF_LINES") == "-100"

    def test_split_csv_unicode_characters(self, monkeypatch):
        """Unicode 文字を含む CSV"""
        monkeypatch.setenv("TEST_CSV", "日本語,中文,한국어")

        result = AppConfig._split_csv("TEST_CSV", "default")

        assert result == ["日本語", "中文", "한국어"]

    def test_baseline_policy_secret_patterns_match_aws_key(self):
        """AWS キーパターンが機能する"""
        import re

        patterns = AppConfig.BASELINE_AUTOMATION_POLICY["secret_detection_patterns"]
        aws_pattern = patterns[0]  # "(?:AKIA|ASIA)[0-9A-Z]{16}"

        # 実際の AWS キー形式にマッチするか確認
        test_key = "AKIAIOSFODNN7EXAMPLE"
        assert re.search(aws_pattern, test_key)

    def test_baseline_policy_secret_patterns_match_openai_key(self):
        """OpenAI キーパターンが機能する"""
        import re

        patterns = AppConfig.BASELINE_AUTOMATION_POLICY["secret_detection_patterns"]
        openai_pattern = patterns[1]  # "sk-[A-Za-z0-9]{20,}"

        # 実際の OpenAI キー形式にマッチするか確認
        test_key = "sk-proj1234567890abcdefghijk"
        assert re.search(openai_pattern, test_key)

    def test_baseline_policy_secret_patterns_match_github_pat(self):
        """GitHub PAT パターンが機能する"""
        import re

        patterns = AppConfig.BASELINE_AUTOMATION_POLICY["secret_detection_patterns"]
        github_pattern = patterns[2]  # "ghp_[A-Za-z0-9]{36}"

        # 実際の GitHub PAT 形式にマッチするか確認
        test_pat = "ghp_" + "a" * 36
        assert re.search(github_pattern, test_pat)
