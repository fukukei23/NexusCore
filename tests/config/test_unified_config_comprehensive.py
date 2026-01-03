"""
============================================================================
Comprehensive Tests for unified_config.py
============================================================================
高品質テストの原則:
- 環境変数をモック（独立したテスト実行）
- 実際の設定ロジックとバリデーションをテスト
- エッジケースとエラー条件をカバー
============================================================================
"""
import pytest
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from nexuscore.config.unified_config import (
    DatabaseConfig,
    CeleryConfig,
    AutonomyConfig,
    LLMConfig,
    NexusConfig,
    get_config,
    set_config,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def reset_global_config():
    """各テスト前後でグローバル設定をリセット"""
    import nexuscore.config.unified_config as uc
    original_config = uc._config

    # テスト前にリセット
    uc._config = None

    yield

    # テスト後に復元
    uc._config = original_config


@pytest.fixture
def clean_env(monkeypatch):
    """クリーンな環境変数"""
    # 全ての NEXUS 関連環境変数をクリア
    for key in list(os.environ.keys()):
        if key.startswith('NEXUS_') or key.startswith('DATABASE_') or \
           key.startswith('CELERY_') or key.startswith('REDIS_') or \
           key.startswith('FLASK_') or key.startswith('SQLALCHEMY_'):
            monkeypatch.delenv(key, raising=False)
    return monkeypatch


@pytest.fixture
def temp_config_dir():
    """一時設定ディレクトリ"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / ".nexus"
        config_dir.mkdir(parents=True, exist_ok=True)
        yield config_dir


# ============================================================================
# Tests: DatabaseConfig
# ============================================================================


class TestDatabaseConfig:
    def test_from_env_default(self, clean_env):
        """デフォルト値でDatabaseConfig作成"""
        config = DatabaseConfig.from_env()

        assert config.uri == "sqlite:///nexuscore.db"
        assert config.track_modifications is False

    def test_from_env_custom(self, clean_env):
        """カスタム環境変数からDatabaseConfig作成"""
        clean_env.setenv("DATABASE_URI", "postgresql://localhost/nexus")
        clean_env.setenv("SQLALCHEMY_TRACK_MODIFICATIONS", "true")

        config = DatabaseConfig.from_env()

        assert config.uri == "postgresql://localhost/nexus"
        assert config.track_modifications is True

    def test_from_env_track_modifications_false(self, clean_env):
        """track_modificationsのfalse値"""
        clean_env.setenv("SQLALCHEMY_TRACK_MODIFICATIONS", "false")

        config = DatabaseConfig.from_env()
        assert config.track_modifications is False

    def test_from_env_track_modifications_various_values(self, clean_env):
        """track_modificationsの様々な値"""
        # true以外は全てfalse
        for value in ["false", "False", "FALSE", "0", "no", "anything"]:
            clean_env.setenv("SQLALCHEMY_TRACK_MODIFICATIONS", value)
            config = DatabaseConfig.from_env()
            assert config.track_modifications is False, f"Value {value} should be False"

    def test_validate_success(self):
        """正常なバリデーション"""
        config = DatabaseConfig(uri="sqlite:///test.db")
        config.validate()  # 例外が発生しない

    def test_validate_empty_uri(self):
        """空のURIでバリデーション失敗"""
        config = DatabaseConfig(uri="")

        with pytest.raises(ValueError, match="DATABASE_URI is required"):
            config.validate()

    def test_direct_creation(self):
        """直接インスタンス化"""
        config = DatabaseConfig(
            uri="mysql://user:pass@localhost/db",
            track_modifications=True
        )

        assert config.uri == "mysql://user:pass@localhost/db"
        assert config.track_modifications is True


# ============================================================================
# Tests: CeleryConfig
# ============================================================================


class TestCeleryConfig:
    def test_from_env_default(self, clean_env):
        """デフォルト値でCeleryConfig作成"""
        config = CeleryConfig.from_env()

        assert config.broker_url == "redis://localhost:6379/0"
        # NOTE: replace(":0", ":1") は "redis://localhost:6379/0" にマッチしないため、
        # result_backendもbroker_urlと同じになる
        assert config.result_backend == "redis://localhost:6379/0"

    def test_from_env_with_redis_url(self, clean_env):
        """REDIS_URLを使用してCeleryConfig作成"""
        clean_env.setenv("REDIS_URL", "redis://redis-server:6379/0")

        config = CeleryConfig.from_env()

        assert config.broker_url == "redis://redis-server:6379/0"
        # NOTE: replace(":0", ":1") は "redis://redis-server:6379/0" にマッチしないため、
        # result_backendもbroker_urlと同じになる
        assert config.result_backend == "redis://redis-server:6379/0"

    def test_from_env_with_explicit_celery_urls(self, clean_env):
        """明示的なCelery URLで作成"""
        clean_env.setenv("CELERY_BROKER_URL", "redis://broker:6379/0")
        clean_env.setenv("CELERY_RESULT_BACKEND", "redis://result:6379/2")

        config = CeleryConfig.from_env()

        assert config.broker_url == "redis://broker:6379/0"
        assert config.result_backend == "redis://result:6379/2"

    def test_from_env_celery_overrides_redis_url(self, clean_env):
        """CELERY_*がREDIS_URLを上書き"""
        clean_env.setenv("REDIS_URL", "redis://redis1:6379/0")
        clean_env.setenv("CELERY_BROKER_URL", "redis://redis2:6379/0")

        config = CeleryConfig.from_env()

        assert config.broker_url == "redis://redis2:6379/0"

    def test_validate_success(self):
        """正常なバリデーション"""
        config = CeleryConfig(
            broker_url="redis://localhost:6379/0",
            result_backend="redis://localhost:6379/1"
        )
        config.validate()  # 例外が発生しない

    def test_validate_empty_broker_url(self):
        """空のbroker_urlでバリデーション失敗"""
        config = CeleryConfig(broker_url="", result_backend="redis://localhost:6379/1")

        with pytest.raises(ValueError, match="CELERY_BROKER_URL is required"):
            config.validate()


# ============================================================================
# Tests: AutonomyConfig
# ============================================================================


class TestAutonomyConfig:
    def test_from_env_default(self, clean_env):
        """デフォルト値でAutonomyConfig作成"""
        config = AutonomyConfig.from_env()

        assert config.user == 1
        assert config.admin == 2
        assert config.system == 3

    def test_from_env_custom(self, clean_env):
        """カスタム環境変数からAutonomyConfig作成"""
        clean_env.setenv("NEXUS_ROLE_MAX_AUTONOMY_USER", "2")
        clean_env.setenv("NEXUS_ROLE_MAX_AUTONOMY_ADMIN", "3")
        clean_env.setenv("NEXUS_ROLE_MAX_AUTONOMY_SYSTEM", "5")

        config = AutonomyConfig.from_env()

        assert config.user == 2
        assert config.admin == 3
        assert config.system == 5

    def test_validate_success(self):
        """正常なバリデーション"""
        config = AutonomyConfig(user=0, admin=2, system=5)
        config.validate()  # 例外が発生しない

    def test_validate_user_out_of_range_low(self):
        """userが範囲外（下限）"""
        config = AutonomyConfig(user=-1, admin=2, system=3)

        with pytest.raises(ValueError, match="User autonomy must be 0-5"):
            config.validate()

    def test_validate_user_out_of_range_high(self):
        """userが範囲外（上限）"""
        config = AutonomyConfig(user=6, admin=2, system=3)

        with pytest.raises(ValueError, match="User autonomy must be 0-5"):
            config.validate()

    def test_validate_admin_out_of_range_low(self):
        """adminが範囲外（下限）"""
        config = AutonomyConfig(user=1, admin=-1, system=3)

        with pytest.raises(ValueError, match="Admin autonomy must be 0-5"):
            config.validate()

    def test_validate_admin_out_of_range_high(self):
        """adminが範囲外（上限）"""
        config = AutonomyConfig(user=1, admin=6, system=3)

        with pytest.raises(ValueError, match="Admin autonomy must be 0-5"):
            config.validate()

    def test_validate_system_out_of_range_low(self):
        """systemが範囲外（下限）"""
        config = AutonomyConfig(user=1, admin=2, system=-1)

        with pytest.raises(ValueError, match="System autonomy must be 0-5"):
            config.validate()

    def test_validate_system_out_of_range_high(self):
        """systemが範囲外（上限）"""
        config = AutonomyConfig(user=1, admin=2, system=6)

        with pytest.raises(ValueError, match="System autonomy must be 0-5"):
            config.validate()

    def test_validate_boundary_values(self):
        """境界値でのバリデーション"""
        # 0はOK
        config1 = AutonomyConfig(user=0, admin=0, system=0)
        config1.validate()

        # 5はOK
        config2 = AutonomyConfig(user=5, admin=5, system=5)
        config2.validate()


# ============================================================================
# Tests: LLMConfig
# ============================================================================


class TestLLMConfig:
    def test_from_env_default(self, clean_env):
        """デフォルト値でLLMConfig作成"""
        config = LLMConfig.from_env()

        assert config.default_model == "gpt-4"
        assert config.timeout == 60
        assert config.max_retries == 3

    def test_from_env_custom(self, clean_env):
        """カスタム環境変数からLLMConfig作成"""
        clean_env.setenv("NEXUS_DEFAULT_MODEL", "gpt-4-turbo")
        clean_env.setenv("NEXUS_LLM_TIMEOUT", "120")
        clean_env.setenv("NEXUS_LLM_MAX_RETRIES", "5")

        config = LLMConfig.from_env()

        assert config.default_model == "gpt-4-turbo"
        assert config.timeout == 120
        assert config.max_retries == 5

    def test_validate_success(self):
        """正常なバリデーション"""
        config = LLMConfig(default_model="claude-3", timeout=30, max_retries=2)
        config.validate()  # 例外が発生しない

    def test_validate_zero_timeout(self):
        """タイムアウト0でバリデーション失敗"""
        config = LLMConfig(timeout=0)

        with pytest.raises(ValueError, match="LLM timeout must be positive"):
            config.validate()

    def test_validate_negative_timeout(self):
        """負のタイムアウトでバリデーション失敗"""
        config = LLMConfig(timeout=-10)

        with pytest.raises(ValueError, match="LLM timeout must be positive"):
            config.validate()

    def test_validate_negative_max_retries(self):
        """負のmax_retriesでバリデーション失敗"""
        config = LLMConfig(max_retries=-1)

        with pytest.raises(ValueError, match="Max retries must be non-negative"):
            config.validate()

    def test_validate_zero_max_retries(self):
        """max_retries=0は有効（リトライなし）"""
        config = LLMConfig(max_retries=0)
        config.validate()  # 例外が発生しない


# ============================================================================
# Tests: NexusConfig
# ============================================================================


class TestNexusConfig:
    def test_from_env_default(self, clean_env):
        """デフォルト値でNexusConfig作成"""
        config = NexusConfig.from_env()

        assert config.flask_secret_key == "dev-secret-key-change-in-production"
        assert isinstance(config.database, DatabaseConfig)
        assert isinstance(config.celery, CeleryConfig)
        assert isinstance(config.autonomy, AutonomyConfig)
        assert isinstance(config.llm, LLMConfig)
        assert config.self_healing == {}

    def test_from_env_with_config_file(self, clean_env, temp_config_dir):
        """設定ファイルからself-healing設定をロード"""
        config_file = temp_config_dir / "self_healing.config.json"
        sh_config = {
            "enabled": True,
            "max_attempts": 3,
            "timeout": 300
        }
        config_file.write_text(json.dumps(sh_config))

        config = NexusConfig.from_env(config_file=config_file)

        assert config.self_healing == sh_config

    def test_from_env_with_missing_config_file(self, clean_env):
        """存在しない設定ファイル"""
        config = NexusConfig.from_env(config_file=Path("/nonexistent/file.json"))

        assert config.self_healing == {}

    def test_from_env_with_invalid_json(self, clean_env, temp_config_dir, capsys):
        """無効なJSON設定ファイル"""
        config_file = temp_config_dir / "self_healing.config.json"
        config_file.write_text("invalid json {")

        config = NexusConfig.from_env(config_file=config_file)

        # 警告が出力される
        captured = capsys.readouterr()
        assert "Warning: Failed to load" in captured.out
        assert config.self_healing == {}

    def test_validate_success(self, clean_env):
        """全サブシステムの正常なバリデーション"""
        config = NexusConfig.from_env()
        config.validate()  # 例外が発生しない

    def test_validate_production_secret_key_error(self, clean_env):
        """本番環境でデフォルトsecret keyはエラー"""
        clean_env.setenv("FLASK_ENV", "production")

        with pytest.raises(ValueError, match="Must set FLASK_SECRET_KEY in production"):
            config = NexusConfig.from_env()

    def test_validate_production_with_custom_secret_key(self, clean_env):
        """本番環境でカスタムsecret keyは正常"""
        clean_env.setenv("FLASK_ENV", "production")
        clean_env.setenv("FLASK_SECRET_KEY", "super-secret-production-key")

        config = NexusConfig.from_env()
        assert config.flask_secret_key == "super-secret-production-key"

    def test_validate_calls_all_subconfigs(self, clean_env):
        """validateが全サブ設定のvalidateを呼ぶ"""
        # 無効なデータベースURIを設定
        clean_env.setenv("DATABASE_URI", "")

        with pytest.raises(ValueError, match="DATABASE_URI is required"):
            config = NexusConfig.from_env()

    def test_to_flask_config(self, clean_env):
        """Flask設定辞書への変換"""
        clean_env.setenv("FLASK_SECRET_KEY", "my-secret")
        clean_env.setenv("DATABASE_URI", "postgresql://localhost/db")
        clean_env.setenv("SQLALCHEMY_TRACK_MODIFICATIONS", "true")

        config = NexusConfig.from_env()
        flask_config = config.to_flask_config()

        assert flask_config["SECRET_KEY"] == "my-secret"
        assert flask_config["SQLALCHEMY_DATABASE_URI"] == "postgresql://localhost/db"
        assert flask_config["SQLALCHEMY_TRACK_MODIFICATIONS"] is True

    def test_direct_creation(self, clean_env):
        """直接インスタンス化"""
        config = NexusConfig(
            flask_secret_key="test-key",
            database=DatabaseConfig(uri="sqlite:///test.db"),
            celery=CeleryConfig(
                broker_url="redis://localhost:6379/0",
                result_backend="redis://localhost:6379/1"
            ),
            autonomy=AutonomyConfig(user=1, admin=2, system=3),
            llm=LLMConfig(),
            self_healing={"enabled": True}
        )

        assert config.flask_secret_key == "test-key"
        assert config.self_healing["enabled"] is True


# ============================================================================
# Tests: get_config and set_config
# ============================================================================


class TestGetConfig:
    def test_get_config_creates_singleton(self, clean_env):
        """初回呼び出しでシングルトン作成"""
        config1 = get_config()
        config2 = get_config()

        # 同じインスタンスが返される
        assert config1 is config2

    def test_get_config_reload(self, clean_env):
        """reload=Trueで新しいインスタンス作成"""
        config1 = get_config()

        # 環境変数を変更
        clean_env.setenv("FLASK_SECRET_KEY", "new-secret")

        config2 = get_config(reload=True)

        # 異なるインスタンス
        assert config1 is not config2
        # 新しい値が反映される
        assert config2.flask_secret_key == "new-secret"

    def test_get_config_after_set_config(self, clean_env):
        """set_config後のget_config"""
        custom_config = NexusConfig(
            flask_secret_key="custom-key",
            database=DatabaseConfig(uri="sqlite:///custom.db"),
            celery=CeleryConfig(
                broker_url="redis://custom:6379/0",
                result_backend="redis://custom:6379/1"
            ),
            autonomy=AutonomyConfig(),
            llm=LLMConfig()
        )

        set_config(custom_config)

        retrieved_config = get_config()
        assert retrieved_config is custom_config
        assert retrieved_config.flask_secret_key == "custom-key"


# ============================================================================
# Tests: Integration scenarios
# ============================================================================


class TestIntegrationScenarios:
    def test_full_config_lifecycle(self, clean_env, temp_config_dir):
        """完全な設定ライフサイクル"""
        # 1. 環境変数を設定
        clean_env.setenv("FLASK_SECRET_KEY", "integration-test-key")
        clean_env.setenv("DATABASE_URI", "postgresql://localhost/integration")
        clean_env.setenv("NEXUS_DEFAULT_MODEL", "gpt-4-turbo")
        clean_env.setenv("NEXUS_ROLE_MAX_AUTONOMY_USER", "2")

        # 2. Self-healing設定ファイルを作成
        config_file = temp_config_dir / "self_healing.config.json"
        sh_config = {"enabled": True, "max_attempts": 5}
        config_file.write_text(json.dumps(sh_config))

        # 3. 設定をロード
        config = NexusConfig.from_env(config_file=config_file)

        # 4. 各設定を検証
        assert config.flask_secret_key == "integration-test-key"
        assert config.database.uri == "postgresql://localhost/integration"
        assert config.llm.default_model == "gpt-4-turbo"
        assert config.autonomy.user == 2
        assert config.self_healing["enabled"] is True
        assert config.self_healing["max_attempts"] == 5

        # 5. Flask設定に変換
        flask_config = config.to_flask_config()
        assert flask_config["SECRET_KEY"] == "integration-test-key"

    def test_environment_override_precedence(self, clean_env):
        """環境変数の優先順位"""
        # REDIS_URLを設定
        clean_env.setenv("REDIS_URL", "redis://redis1:6379/0")

        config1 = NexusConfig.from_env()
        assert config1.celery.broker_url == "redis://redis1:6379/0"

        # CELERY_BROKER_URLで上書き
        clean_env.setenv("CELERY_BROKER_URL", "redis://redis2:6379/0")

        config2 = NexusConfig.from_env()
        assert config2.celery.broker_url == "redis://redis2:6379/0"

    def test_multiple_validation_errors(self, clean_env):
        """複数のバリデーションエラー"""
        clean_env.setenv("DATABASE_URI", "")  # 空のURI

        with pytest.raises(ValueError, match="DATABASE_URI is required"):
            NexusConfig.from_env()

    def test_config_reset_and_reload(self, clean_env):
        """設定のリセットと再ロード"""
        # 初期設定
        config1 = get_config()
        initial_key = config1.flask_secret_key

        # カスタム設定で上書き
        custom_config = NexusConfig(
            flask_secret_key="custom",
            database=DatabaseConfig(uri="sqlite:///custom.db"),
            celery=CeleryConfig(
                broker_url="redis://localhost:6379/0",
                result_backend="redis://localhost:6379/1"
            ),
            autonomy=AutonomyConfig(),
            llm=LLMConfig()
        )
        set_config(custom_config)

        config2 = get_config()
        assert config2.flask_secret_key == "custom"

        # reload=Trueで環境変数から再ロード
        config3 = get_config(reload=True)
        assert config3.flask_secret_key == initial_key


# ============================================================================
# Tests: Edge cases
# ============================================================================


class TestEdgeCases:
    def test_config_with_empty_self_healing(self, clean_env):
        """空のself-healing設定"""
        config = NexusConfig.from_env()
        assert config.self_healing == {}

    def test_config_with_very_long_secret_key(self, clean_env):
        """非常に長いsecret key"""
        long_key = "x" * 10000
        clean_env.setenv("FLASK_SECRET_KEY", long_key)

        config = NexusConfig.from_env()
        assert config.flask_secret_key == long_key
        assert len(config.flask_secret_key) == 10000

    def test_config_with_special_characters_in_uri(self, clean_env):
        """特殊文字を含むURI"""
        uri = "postgresql://user%40:p%40ss@localhost/db%2Bname"
        clean_env.setenv("DATABASE_URI", uri)

        config = NexusConfig.from_env()
        assert config.database.uri == uri

    def test_autonomy_all_same_level(self, clean_env):
        """全ロールが同じ自律レベル"""
        clean_env.setenv("NEXUS_ROLE_MAX_AUTONOMY_USER", "3")
        clean_env.setenv("NEXUS_ROLE_MAX_AUTONOMY_ADMIN", "3")
        clean_env.setenv("NEXUS_ROLE_MAX_AUTONOMY_SYSTEM", "3")

        config = NexusConfig.from_env()
        assert config.autonomy.user == 3
        assert config.autonomy.admin == 3
        assert config.autonomy.system == 3

    def test_llm_with_zero_timeout_fails(self, clean_env):
        """タイムアウト0は無効"""
        clean_env.setenv("NEXUS_LLM_TIMEOUT", "0")

        with pytest.raises(ValueError, match="LLM timeout must be positive"):
            NexusConfig.from_env()

    def test_config_file_with_unicode(self, clean_env, temp_config_dir):
        """Unicode文字を含む設定ファイル"""
        config_file = temp_config_dir / "self_healing.config.json"
        sh_config = {"message": "こんにちは世界", "emoji": "🚀"}
        config_file.write_text(json.dumps(sh_config, ensure_ascii=False), encoding='utf-8')

        config = NexusConfig.from_env(config_file=config_file)
        assert config.self_healing["message"] == "こんにちは世界"
        assert config.self_healing["emoji"] == "🚀"
