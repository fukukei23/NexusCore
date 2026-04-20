"""
Tests for config/secrets.py — Secrets class attribute access and structure.
Does NOT assert actual secret values (security).
"""

from nexuscore.config.secrets import Secrets


class TestSecretsClassStructure:
    """Secrets クラスの構造と属性アクセスを検証"""

    def test_secrets_is_class(self):
        """Secrets はクラスとして定義されている"""
        assert isinstance(Secrets, type)

    def test_secrets_has_openai_api_key(self):
        assert hasattr(Secrets, "OPENAI_API_KEY")
        assert isinstance(Secrets.OPENAI_API_KEY, str)
        assert len(Secrets.OPENAI_API_KEY) > 0

    def test_secrets_has_openai_project(self):
        assert hasattr(Secrets, "OPENAI_PROJECT")
        assert isinstance(Secrets.OPENAI_PROJECT, str)

    def test_secrets_has_gemini_api_key(self):
        assert hasattr(Secrets, "GEMINI_API_KEY")
        assert isinstance(Secrets.GEMINI_API_KEY, str)

    def test_secrets_has_perplexity_api_key(self):
        assert hasattr(Secrets, "PERPLEXITY_API_KEY")
        assert isinstance(Secrets.PERPLEXITY_API_KEY, str)

    def test_secrets_has_deepseek_api_key(self):
        assert hasattr(Secrets, "DEEPSEEK_API_KEY")
        assert isinstance(Secrets.DEEPSEEK_API_KEY, str)

    def test_secrets_has_kimi_api_key(self):
        assert hasattr(Secrets, "KIMI_API_KEY")
        assert isinstance(Secrets.KIMI_API_KEY, str)

    def test_secrets_has_minimax_api_key(self):
        assert hasattr(Secrets, "MINIMAX_API_KEY")
        assert isinstance(Secrets.MINIMAX_API_KEY, str)

    def test_secrets_has_glm_api_key(self):
        assert hasattr(Secrets, "GLM_API_KEY")
        assert isinstance(Secrets.GLM_API_KEY, str)

    def test_secrets_has_flask_secret_key(self):
        assert hasattr(Secrets, "FLASK_SECRET_KEY")
        assert isinstance(Secrets.FLASK_SECRET_KEY, str)

    def test_secrets_has_redis_url(self):
        assert hasattr(Secrets, "REDIS_URL")
        assert isinstance(Secrets.REDIS_URL, str)
        assert "redis" in Secrets.REDIS_URL

    def test_secrets_has_database_url(self):
        assert hasattr(Secrets, "DATABASE_URL")
        assert isinstance(Secrets.DATABASE_URL, str)

    def test_secrets_has_llm_dry_run(self):
        assert hasattr(Secrets, "LLM_DRY_RUN")
        assert isinstance(Secrets.LLM_DRY_RUN, str)

    def test_secrets_has_nexus_llm_mode(self):
        assert hasattr(Secrets, "NEXUS_LLM_MODE")
        assert isinstance(Secrets.NEXUS_LLM_MODE, str)

    def test_secrets_has_nexus_llm_daily_cap(self):
        assert hasattr(Secrets, "NEXUS_LLM_DAILY_CAP_USD")
        assert isinstance(Secrets.NEXUS_LLM_DAILY_CAP_USD, str)

    def test_secrets_has_slack_webhook_url(self):
        assert hasattr(Secrets, "SLACK_WEBHOOK_URL")
        assert isinstance(Secrets.SLACK_WEBHOOK_URL, str)


class TestSecretsNumericConfigs:
    """数値設定の文字列表現を検証"""

    def test_max_input_token_length_is_numeric_string(self):
        assert Secrets.MAX_INPUT_TOKEN_LENGTH.isdigit()

    def test_deepseek_prepaid_usd_is_numeric_string(self):
        assert Secrets.DEEPSEEK_PREPAID_USD.replace(".", "", 1).isdigit()

    def test_nexus_light_output_threshold_is_numeric_string(self):
        assert Secrets.NEXUS_LIGHT_OUTPUT_THRESHOLD.isdigit()

    def test_nexus_long_prompt_threshold_is_numeric_string(self):
        assert Secrets.NEXUS_LONG_PROMPT_THRESHOLD.isdigit()


class TestSecretsModelConfigs:
    """モデル名設定の検証"""

    def test_nexus_classifier_model_is_set(self):
        assert hasattr(Secrets, "NEXUS_CLASSIFIER_MODEL")
        assert len(Secrets.NEXUS_CLASSIFIER_MODEL) > 0

    def test_nexus_task_model_coding_is_set(self):
        assert hasattr(Secrets, "NEXUS_TASK_MODEL_CODING")
        assert len(Secrets.NEXUS_TASK_MODEL_CODING) > 0

    def test_nexus_task_model_review_is_set(self):
        assert hasattr(Secrets, "NEXUS_TASK_MODEL_REVIEW")
        assert len(Secrets.NEXUS_TASK_MODEL_REVIEW) > 0

    def test_minimax_model_is_set(self):
        assert hasattr(Secrets, "MINIMAX_MODEL")
        assert len(Secrets.MINIMAX_MODEL) > 0

    def test_glm_model_is_set(self):
        assert hasattr(Secrets, "GLM_MODEL")
        assert len(Secrets.GLM_MODEL) > 0

    def test_glm_api_base_is_url(self):
        assert hasattr(Secrets, "GLM_API_BASE")
        assert Secrets.GLM_API_BASE.startswith("https://")

    def test_minimax_api_base_is_url(self):
        assert hasattr(Secrets, "MINIMAX_API_BASE")
        assert Secrets.MINIMAX_API_BASE.startswith("https://")
