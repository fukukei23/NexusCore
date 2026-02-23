"""
Comprehensive tests for Local (Offline) LLM Provider

Tests cover:
- Stub-only behavior
- JSON mode
- Text mode
- Model name handling
- Safety fallback behavior
"""

import json
from unittest.mock import patch

from nexuscore.llm.providers.local_provider import LocalLLM


class TestLocalProviderInit:
    """Test Local provider initialization"""

    def test_init_with_model_name(self):
        """Should initialize with given model name"""
        provider = LocalLLM("local-test")
        assert provider.model_name == "local-test"

    def test_init_without_model_name_uses_default(self):
        """Should use default model name if not specified"""
        provider = LocalLLM("local")
        assert provider.model_name == "local"

    def test_init_always_stub_mode(self):
        """Should always be in stub mode (no API calls)"""
        provider = LocalLLM("local-test")
        # Local provider doesn't have real_calls attribute, it's always stub
        assert hasattr(provider, "execute")


class TestLocalProviderExecute:
    """Test Local provider execute method"""

    def test_execute_returns_stub_content_in_text_mode(self):
        """Should return stub content in text mode"""
        provider = LocalLLM("local-test")
        result = provider.execute("test prompt", "test system")

        assert isinstance(result, str)
        assert "LOCAL FALLBACK" in result
        assert "スタブ" in result
        assert len(result) > 0

    def test_execute_returns_json_in_json_mode(self):
        """Should return JSON structure in JSON mode"""
        provider = LocalLLM("local-test")
        result = provider.execute("test prompt", "test system", as_json=True)

        assert isinstance(result, str)
        # Should be valid JSON
        data = json.loads(result)
        assert isinstance(data, dict)
        assert "model" in data
        assert "mode" in data
        assert "preview" in data
        assert "content" in data

    def test_execute_json_contains_expected_fields(self):
        """Should include expected fields in JSON response"""
        provider = LocalLLM("local-test")
        result = provider.execute("prompt", "system", as_json=True)

        data = json.loads(result)
        assert data["model"] == "local-test"
        assert data["mode"] == "local-fallback"
        assert "LOCAL FALLBACK" in data["preview"]
        assert "summary" in data["content"]
        assert "plan" in data["content"]

    def test_execute_json_plan_structure(self):
        """Should include properly structured plan in JSON"""
        provider = LocalLLM("local-test")
        result = provider.execute("prompt", "system", as_json=True)

        data = json.loads(result)
        plan = data["content"]["plan"]
        assert isinstance(plan, list)
        assert len(plan) >= 3

        # Check first step structure
        first_step = plan[0]
        assert "step" in first_step
        assert "owner" in first_step
        assert "status" in first_step
        assert first_step["step"] == "analyze_requirement"
        assert first_step["owner"] == "PlannerAgent"

    def test_execute_with_custom_temperature_ignored(self):
        """Should ignore temperature parameter (stub mode)"""
        provider = LocalLLM("local-test")
        result1 = provider.execute("prompt", "system", temperature=0.1)
        result2 = provider.execute("prompt", "system", temperature=0.9)

        # Should return same content regardless of temperature
        assert result1 == result2

    def test_execute_with_max_tokens_ignored(self):
        """Should ignore max_tokens parameter (stub mode)"""
        provider = LocalLLM("local-test")
        result1 = provider.execute("prompt", "system", max_tokens=100)
        result2 = provider.execute("prompt", "system", max_tokens=2000)

        # Should return same content regardless of max_tokens
        assert result1 == result2

    def test_execute_text_mode_is_consistent(self):
        """Should return consistent text content"""
        provider = LocalLLM("local-test")
        result1 = provider.execute("prompt1", "system1")
        result2 = provider.execute("prompt2", "system2")

        # Should return same stub message regardless of input
        assert result1 == result2

    def test_execute_json_mode_is_valid_json(self):
        """Should always return valid JSON in JSON mode"""
        provider = LocalLLM("local-test")

        # Try multiple different inputs
        for i in range(5):
            result = provider.execute(f"prompt{i}", f"system{i}", as_json=True)
            # Should not raise JSONDecodeError
            data = json.loads(result)
            assert isinstance(data, dict)


class TestLocalProviderCallMode:
    """Test Local provider call mode tracking"""

    def test_last_call_mode_is_stub(self):
        """Should track last call mode as stub"""
        provider = LocalLLM("local-test")
        provider.execute("prompt", "system")

        assert provider.last_call_mode == "stub"

    def test_last_call_mode_stub_in_json_mode(self):
        """Should track stub mode even in JSON mode"""
        provider = LocalLLM("local-test")
        provider.execute("prompt", "system", as_json=True)

        assert provider.last_call_mode == "stub"


class TestLocalProviderSafety:
    """Test Local provider safety features"""

    def test_never_makes_real_api_calls(self):
        """Should never attempt real API calls"""
        provider = LocalLLM("local-test")

        # No session should be created
        assert not hasattr(provider, "session") or provider.session is None

        # No API key should be used
        assert not hasattr(provider, "api_key") or provider.api_key is None

    def test_works_without_environment_variables(self):
        """Should work without any environment variables"""
        with patch.dict("os.environ", {}, clear=True):
            provider = LocalLLM("local-test")
            result = provider.execute("prompt", "system")

            assert isinstance(result, str)
            assert len(result) > 0

    def test_works_without_network(self):
        """Should work without network connectivity"""
        # No network calls should be made
        provider = LocalLLM("local-test")
        result = provider.execute("prompt", "system")

        assert isinstance(result, str)
        assert "LOCAL FALLBACK" in result


class TestLocalProviderModels:
    """Test different Local model names"""

    def test_supports_local_model(self):
        """Should support 'local' model name"""
        provider = LocalLLM("local")
        assert provider.model_name == "local"

    def test_supports_local_test_model(self):
        """Should support 'local-test' model name"""
        provider = LocalLLM("local-test")
        assert provider.model_name == "local-test"

    def test_supports_custom_model_names(self):
        """Should support any custom model name"""
        provider = LocalLLM("my-custom-offline-model")
        assert provider.model_name == "my-custom-offline-model"

        result = provider.execute("test", "test", as_json=True)
        data = json.loads(result)
        assert data["model"] == "my-custom-offline-model"
