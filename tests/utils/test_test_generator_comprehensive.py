"""
Comprehensive tests for test_generator module.
Tests pytest test code generation engine with LLM and template modes.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nexuscore.utils.test_generator import (
    DEFAULT_CONFIG,
    TestGenConfig,
    _env_flag,
    _get_client,
    _try_generate_tests_with_llm,
    generate_and_validate_test_code,
    generate_template_tests,
    generate_tests_for_module,
    generate_unit_tests,
)

# ==============================================================================
# TestGenConfig Tests
# ==============================================================================


class TestTestGenConfig:
    """Test TestGenConfig dataclass"""

    def test_config_creation_defaults(self):
        """Create config with defaults"""
        config = TestGenConfig()
        assert config.use_llm is True
        assert config.max_functions == 20
        assert config.seed is None

    def test_config_creation_custom(self):
        """Create config with custom values"""
        config = TestGenConfig(use_llm=False, max_functions=10, seed=42)
        assert config.use_llm is False
        assert config.max_functions == 10
        assert config.seed == 42

    def test_config_is_dataclass(self):
        """TestGenConfig is a dataclass"""
        assert hasattr(TestGenConfig, "__dataclass_fields__")


# ==============================================================================
# _env_flag Tests
# ==============================================================================


class TestEnvFlag:
    """Test _env_flag function"""

    def test_env_flag_not_set_returns_default(self):
        """Returns default when env var not set"""
        with patch.dict(os.environ, {}, clear=True):
            result = _env_flag("TEST_VAR", True)
            assert result is True

            result = _env_flag("TEST_VAR", False)
            assert result is False

    def test_env_flag_zero_returns_false(self):
        """Returns False for '0'"""
        with patch.dict(os.environ, {"TEST_VAR": "0"}):
            result = _env_flag("TEST_VAR", True)
            assert result is False

    def test_env_flag_false_returns_false(self):
        """Returns False for 'false'"""
        with patch.dict(os.environ, {"TEST_VAR": "false"}):
            result = _env_flag("TEST_VAR", True)
            assert result is False

        with patch.dict(os.environ, {"TEST_VAR": "FALSE"}):
            result = _env_flag("TEST_VAR", True)
            assert result is False

    def test_env_flag_no_returns_false(self):
        """Returns False for 'no'"""
        with patch.dict(os.environ, {"TEST_VAR": "no"}):
            result = _env_flag("TEST_VAR", True)
            assert result is False

        with patch.dict(os.environ, {"TEST_VAR": "NO"}):
            result = _env_flag("TEST_VAR", True)
            assert result is False

    def test_env_flag_one_returns_true(self):
        """Returns True for '1'"""
        with patch.dict(os.environ, {"TEST_VAR": "1"}):
            result = _env_flag("TEST_VAR", False)
            assert result is True

    def test_env_flag_true_returns_true(self):
        """Returns True for 'true'"""
        with patch.dict(os.environ, {"TEST_VAR": "true"}):
            result = _env_flag("TEST_VAR", False)
            assert result is True

    def test_env_flag_yes_returns_true(self):
        """Returns True for 'yes'"""
        with patch.dict(os.environ, {"TEST_VAR": "yes"}):
            result = _env_flag("TEST_VAR", False)
            assert result is True

    def test_env_flag_empty_string_returns_true(self):
        """Returns True for empty string"""
        with patch.dict(os.environ, {"TEST_VAR": ""}):
            result = _env_flag("TEST_VAR", False)
            assert result is True


# ==============================================================================
# _get_client Tests
# ==============================================================================


class TestGetClient:
    """Test _get_client function"""

    @pytest.fixture(autouse=True)
    def reset_client(self):
        """Reset global _client before each test"""
        import nexuscore.utils.test_generator as tg

        tg._client = None
        yield
        tg._client = None

    @patch("nexuscore.utils.test_generator.HAS_OPENAI", True)
    @patch("nexuscore.utils.test_generator.OpenAI")
    def test_get_client_creates_client(self, mock_openai_class):
        """Creates OpenAI client with API key"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            client = _get_client()

        assert client == mock_client
        mock_openai_class.assert_called_once_with(api_key="test-key")

    @patch("nexuscore.utils.test_generator.HAS_OPENAI", True)
    @patch("nexuscore.utils.test_generator.OpenAI")
    def test_get_client_lazy_initialization(self, mock_openai_class):
        """Client is only created once (lazy initialization)"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            client1 = _get_client()
            client2 = _get_client()

        assert client1 == client2
        # OpenAI should only be called once
        assert mock_openai_class.call_count == 1

    @patch("nexuscore.utils.test_generator.HAS_OPENAI", False)
    def test_get_client_no_openai_package(self):
        """Raises ImportError when openai package not installed"""
        with pytest.raises(ImportError, match="openai package is not installed"):
            _get_client()

    @patch("nexuscore.utils.test_generator.HAS_OPENAI", True)
    def test_get_client_no_api_key(self):
        """Raises ValueError when API key not set"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                _get_client()


# ==============================================================================
# generate_template_tests Tests
# ==============================================================================


class TestGenerateTemplateTests:
    """Test generate_template_tests function"""

    def test_generate_template_simple_function(self, tmp_path):
        """Generate template for simple function"""
        module_file = tmp_path / "simple.py"
        module_file.write_text(
            """
def add(a, b):
    return a + b
"""
        )

        result = generate_template_tests(module_file)

        assert "import pytest" in result
        assert "def test_add():" in result
        assert "not implemented" in result

    def test_generate_template_multiple_functions(self, tmp_path):
        """Generate template for multiple functions"""
        module_file = tmp_path / "multi.py"
        module_file.write_text(
            """
def func1():
    pass

def func2():
    pass

def func3():
    pass
"""
        )

        result = generate_template_tests(module_file)

        assert "def test_func1():" in result
        assert "def test_func2():" in result
        assert "def test_func3():" in result

    def test_generate_template_with_class(self, tmp_path):
        """Generate template for class methods"""
        module_file = tmp_path / "with_class.py"
        module_file.write_text(
            """
class Calculator:
    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b
"""
        )

        result = generate_template_tests(module_file)

        assert "def test_Calculator_add():" in result
        assert "def test_Calculator_subtract():" in result

    def test_generate_template_max_functions(self, tmp_path):
        """Respects max_functions limit"""
        module_file = tmp_path / "many_funcs.py"
        funcs = "\n".join([f"def func{i}(): pass" for i in range(30)])
        module_file.write_text(funcs)

        result = generate_template_tests(module_file, max_functions=5)

        # Should only have 5 test functions
        test_count = result.count("def test_func")
        assert test_count == 5

    def test_generate_template_no_functions(self, tmp_path):
        """Generate fallback when no functions found"""
        module_file = tmp_path / "empty.py"
        module_file.write_text("# Just a comment")

        result = generate_template_tests(module_file)

        assert "def test_auto_generated_test_scaffold_no_functions():" in result
        assert "No functions found" in result

    def test_generate_template_syntax_error(self, tmp_path):
        """Handle syntax error gracefully"""
        module_file = tmp_path / "invalid.py"
        module_file.write_text("def invalid syntax here")

        result = generate_template_tests(module_file)

        assert "pytest.skip" in result
        assert "Failed to parse" in result

    def test_generate_template_file_not_found(self):
        """Handle file not found gracefully"""
        result = generate_template_tests(Path("/nonexistent/file.py"))

        assert "pytest.skip" in result
        assert "Failed to read" in result

    def test_generate_template_with_project_root(self, tmp_path):
        """Uses project root for import path"""
        project_root = tmp_path
        module_file = project_root / "src" / "mymodule.py"
        module_file.parent.mkdir(parents=True)
        module_file.write_text("def test_func(): pass")

        result = generate_template_tests(module_file, project_root=project_root)

        assert "from src.mymodule import" in result

    def test_generate_template_excludes_private_methods(self, tmp_path):
        """Excludes private methods starting with _"""
        module_file = tmp_path / "private.py"
        module_file.write_text(
            """
class MyClass:
    def public_method(self):
        pass

    def _private_method(self):
        pass

    def __dunder_method__(self):
        pass
"""
        )

        result = generate_template_tests(module_file)

        assert "test_MyClass_public_method" in result
        assert "test_MyClass__private_method" not in result
        assert "test_MyClass___dunder_method__" not in result


# ==============================================================================
# _try_generate_tests_with_llm Tests
# ==============================================================================


class TestTryGenerateTestsWithLLM:
    """Test _try_generate_tests_with_llm function"""

    @pytest.fixture(autouse=True)
    def reset_client(self):
        """Reset global _client"""
        import nexuscore.utils.test_generator as tg

        tg._client = None
        yield
        tg._client = None

    def test_llm_disabled_returns_template(self):
        """Returns template when LLM disabled"""
        config = TestGenConfig(use_llm=False)
        template = "# template code"
        code = "def test(): pass"

        result = _try_generate_tests_with_llm(template, code, config)

        assert result == template

    @patch("nexuscore.utils.test_generator.HAS_OPENAI", True)
    @patch("nexuscore.utils.test_generator.OpenAI")
    def test_llm_success(self, mock_openai_class):
        """Successfully generates tests with LLM"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "# generated test code"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        config = TestGenConfig(use_llm=True)
        template = "# template"
        code = "def test(): pass"

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            result = _try_generate_tests_with_llm(template, code, config)

        assert result == "# generated test code"

    @patch("nexuscore.utils.test_generator.HAS_OPENAI", True)
    @patch("nexuscore.utils.test_generator.OpenAI")
    def test_llm_empty_response_returns_template(self, mock_openai_class):
        """Returns template when LLM returns empty response"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        config = TestGenConfig(use_llm=True)
        template = "# template"
        code = "def test(): pass"

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            result = _try_generate_tests_with_llm(template, code, config)

        assert result == template

    @patch("nexuscore.utils.test_generator.HAS_OPENAI", False)
    def test_llm_import_error_returns_template(self):
        """Returns template when openai not available"""
        config = TestGenConfig(use_llm=True)
        template = "# template"
        code = "def test(): pass"

        result = _try_generate_tests_with_llm(template, code, config)

        assert result == template

    @patch("nexuscore.utils.test_generator.HAS_OPENAI", True)
    def test_llm_no_api_key_returns_template(self):
        """Returns template when API key not set"""
        config = TestGenConfig(use_llm=True)
        template = "# template"
        code = "def test(): pass"

        with patch.dict(os.environ, {}, clear=True):
            result = _try_generate_tests_with_llm(template, code, config)

        assert result == template

    @patch("nexuscore.utils.test_generator.HAS_OPENAI", True)
    @patch("nexuscore.utils.test_generator.OpenAI")
    def test_llm_exception_returns_template(self, mock_openai_class):
        """Returns template when LLM raises exception"""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API error")
        mock_openai_class.return_value = mock_client

        config = TestGenConfig(use_llm=True)
        template = "# template"
        code = "def test(): pass"

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            result = _try_generate_tests_with_llm(template, code, config)

        assert result == template


# ==============================================================================
# generate_unit_tests Tests
# ==============================================================================


class TestGenerateUnitTests:
    """Test generate_unit_tests function"""

    @pytest.fixture(autouse=True)
    def reset_client(self):
        """Reset global _client"""
        import nexuscore.utils.test_generator as tg

        tg._client = None
        yield
        tg._client = None

    def test_generate_unit_tests_with_file_path(self, tmp_path):
        """Generate tests with file path"""
        module_file = tmp_path / "module.py"
        module_file.write_text("def add(a, b): return a + b")

        config = TestGenConfig(use_llm=False)
        result = generate_unit_tests("", file_path=module_file, config=config)

        assert "import pytest" in result
        assert "test_add" in result

    def test_generate_unit_tests_without_file_path(self):
        """Generate tests without file path (direct code)"""
        code = "def multiply(a, b): return a * b"

        config = TestGenConfig(use_llm=False)
        result = generate_unit_tests(code, config=config)

        assert "import pytest" in result
        assert "test_multiply" in result

    def test_generate_unit_tests_uses_default_config(self, tmp_path):
        """Uses DEFAULT_CONFIG when config not provided"""
        module_file = tmp_path / "module.py"
        module_file.write_text("def func(): pass")

        result = generate_unit_tests("", file_path=module_file)

        # Should not raise exception
        assert "import pytest" in result

    def test_generate_unit_tests_invalid_code(self):
        """Handles invalid code gracefully"""
        code = "invalid python syntax here"

        config = TestGenConfig(use_llm=False)
        result = generate_unit_tests(code, config=config)

        assert "pytest.skip" in result
        assert "Failed to parse" in result


# ==============================================================================
# generate_and_validate_test_code Tests
# ==============================================================================


class TestGenerateAndValidateTestCode:
    """Test generate_and_validate_test_code function"""

    @pytest.fixture(autouse=True)
    def reset_client(self):
        """Reset global _client"""
        import nexuscore.utils.test_generator as tg

        tg._client = None
        yield
        tg._client = None

    def test_validate_generates_valid_code(self, tmp_path):
        """Generates and validates valid test code"""
        module_file = tmp_path / "module.py"
        module_file.write_text("def add(a, b): return a + b")

        with patch("nexuscore.utils.test_generator.DEFAULT_CONFIG.use_llm", False):
            test_code, is_valid, error, warnings = generate_and_validate_test_code(
                "def add(a, b): return a + b", file_path=module_file
            )

        assert is_valid is True
        assert error is None

    def test_validate_extracts_markdown(self, tmp_path):
        """Extracts code from markdown fences"""
        code_with_fence = """
```python
import pytest

def test_example():
    assert True
```
"""
        with patch(
            "nexuscore.utils.test_generator.generate_unit_tests", return_value=code_with_fence
        ):
            test_code, is_valid, error, warnings = generate_and_validate_test_code(
                "def func(): pass"
            )

        assert "```" not in test_code
        assert "import pytest" in test_code

    def test_validate_handles_invalid_code_with_fallback(self, tmp_path):
        """Uses fallback for invalid code"""
        module_file = tmp_path / "module.py"
        module_file.write_text("def func(): pass")

        # Mock to return invalid code
        invalid_code = "def invalid syntax"

        with patch("nexuscore.utils.test_generator.generate_unit_tests", return_value=invalid_code):
            test_code, is_valid, error, warnings = generate_and_validate_test_code(
                "def func(): pass", file_path=module_file
            )

        # Should use fallback, making it valid
        assert is_valid is True
        assert "pytest.fail" in test_code


# ==============================================================================
# generate_tests_for_module Tests
# ==============================================================================


class TestGenerateTestsForModule:
    """Test generate_tests_for_module function"""

    @pytest.fixture(autouse=True)
    def reset_client(self):
        """Reset global _client"""
        import nexuscore.utils.test_generator as tg

        tg._client = None
        yield
        tg._client = None

    def test_generate_creates_test_file(self, tmp_path):
        """Creates test file for module"""
        module_file = tmp_path / "mymodule.py"
        module_file.write_text("def add(a, b): return a + b")

        config = TestGenConfig(use_llm=False)
        output_path = generate_tests_for_module(module_file, config=config)

        assert output_path.exists()
        assert output_path.name == "test_mymodule.py"

    def test_generate_uses_custom_output_path(self, tmp_path):
        """Uses custom output path"""
        module_file = tmp_path / "mymodule.py"
        module_file.write_text("def add(a, b): return a + b")

        custom_output = tmp_path / "custom_test.py"

        config = TestGenConfig(use_llm=False)
        output_path = generate_tests_for_module(
            module_file, output_path=custom_output, config=config
        )

        assert output_path == custom_output
        assert output_path.exists()

    def test_generate_handles_read_error(self, tmp_path):
        """Handles file read error gracefully"""
        nonexistent_file = tmp_path / "nonexistent.py"

        config = TestGenConfig(use_llm=False)
        output_path = generate_tests_for_module(nonexistent_file, config=config)

        # Should still create a fallback test file
        assert output_path.exists()
        content = output_path.read_text()
        assert "Failed to read module" in content

    def test_generate_writes_extracted_code(self, tmp_path):
        """Writes extracted code (not markdown)"""
        module_file = tmp_path / "module.py"
        module_file.write_text("def func(): pass")

        config = TestGenConfig(use_llm=False)
        output_path = generate_tests_for_module(module_file, config=config)

        content = output_path.read_text()
        # Should not contain markdown fences
        assert "```" not in content


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestTestGeneratorIntegration:
    """Integration tests for test_generator module"""

    @pytest.fixture(autouse=True)
    def reset_client(self):
        """Reset global _client"""
        import nexuscore.utils.test_generator as tg

        tg._client = None
        yield
        tg._client = None

    def test_end_to_end_template_mode(self, tmp_path):
        """End-to-end test in template mode"""
        # Create module
        module_file = tmp_path / "calculator.py"
        module_file.write_text(
            """
class Calculator:
    def add(self, a, b):
        return a + b

    def multiply(self, a, b):
        return a * b

def standalone_function():
    return 42
"""
        )

        # Generate tests
        config = TestGenConfig(use_llm=False)
        output_path = generate_tests_for_module(module_file, project_root=tmp_path, config=config)

        # Verify output
        assert output_path.exists()
        content = output_path.read_text()

        assert "import pytest" in content
        assert "test_Calculator_add" in content
        assert "test_Calculator_multiply" in content
        assert "test_standalone_function" in content

    def test_config_respects_max_functions(self, tmp_path):
        """Config max_functions is respected"""
        # Create module with many functions
        module_file = tmp_path / "many.py"
        funcs = "\n".join([f"def func{i}(): pass" for i in range(30)])
        module_file.write_text(funcs)

        config = TestGenConfig(use_llm=False, max_functions=5)
        output_path = generate_tests_for_module(module_file, config=config)

        content = output_path.read_text()
        test_count = content.count("def test_func")

        assert test_count == 5

    def test_default_config_is_used(self):
        """DEFAULT_CONFIG is properly initialized"""
        assert DEFAULT_CONFIG is not None
        assert isinstance(DEFAULT_CONFIG, TestGenConfig)
        assert hasattr(DEFAULT_CONFIG, "use_llm")
        assert hasattr(DEFAULT_CONFIG, "max_functions")

    def test_fallback_chain(self, tmp_path):
        """Fallback chain works: LLM -> template"""
        module_file = tmp_path / "module.py"
        module_file.write_text("def func(): pass")

        # Disable LLM, should use template mode
        config = TestGenConfig(use_llm=False)

        # Template mode should work
        result = generate_unit_tests("def func(): pass", file_path=module_file, config=config)

        # Should get valid output
        assert isinstance(result, str)
        assert len(result) > 0
        assert "import pytest" in result

    def test_module_path_determination(self, tmp_path):
        """Module path is determined correctly with project root"""
        project_root = tmp_path
        module_file = project_root / "src" / "mymodule.py"
        module_file.parent.mkdir(parents=True)
        module_file.write_text("def func(): pass")

        config = TestGenConfig(use_llm=False)

        # Should use project_path_to_module_path
        with patch("nexuscore.utils.test_generator._try_generate_tests_with_llm") as mock_llm:
            mock_llm.return_value = "# test code"
            result = generate_unit_tests(
                "def func(): pass", file_path=module_file, project_root=project_root, config=config
            )

        assert isinstance(result, str)

    def test_warning_logging_on_validation(self, tmp_path, caplog):
        """Logs warnings during validation"""
        import logging

        caplog.set_level(logging.WARNING)

        # Generate code that will have warnings
        code = "def test_example():\n    import os\n    os.system('ls')"

        with patch("nexuscore.utils.test_generator.generate_unit_tests", return_value=code):
            test_code, is_valid, error, warnings = generate_and_validate_test_code(
                "def func(): pass"
            )

        # Should log warnings
        assert len(warnings) > 0

    def test_error_logging_on_invalid_code(self, tmp_path, caplog):
        """Logs error when generated code is invalid"""
        import logging

        caplog.set_level(logging.ERROR)

        module_file = tmp_path / "module.py"
        module_file.write_text("def func(): pass")

        # Generate invalid code
        invalid_code = "def invalid syntax"

        with patch("nexuscore.utils.test_generator.generate_unit_tests", return_value=invalid_code):
            test_code, is_valid, error, warnings = generate_and_validate_test_code(
                "def func(): pass", file_path=module_file
            )

        # Should use fallback
        assert is_valid is True


# ==============================================================================
# Edge Cases
# ==============================================================================


class TestTestGeneratorEdgeCases:
    """Test edge cases for test_generator module"""

    @pytest.fixture(autouse=True)
    def reset_client(self):
        """Reset global _client"""
        import nexuscore.utils.test_generator as tg

        tg._client = None
        yield
        tg._client = None

    def test_empty_module(self, tmp_path):
        """Handle completely empty module"""
        module_file = tmp_path / "empty.py"
        module_file.write_text("")

        config = TestGenConfig(use_llm=False)
        result = generate_unit_tests("", file_path=module_file, config=config)

        assert "import pytest" in result

    def test_unicode_in_code(self, tmp_path):
        """Handle Unicode characters in code"""
        module_file = tmp_path / "unicode.py"
        module_file.write_text(
            """
def 日本語関数():
    '''日本語のコメント'''
    return "こんにちは"
""",
            encoding="utf-8",
        )

        TestGenConfig(use_llm=False)
        result = generate_template_tests(module_file)

        assert "import pytest" in result

    def test_very_long_function_name(self, tmp_path):
        """Handle very long function names"""
        long_name = "a" * 100
        module_file = tmp_path / "long.py"
        module_file.write_text(f"def {long_name}(): pass")

        TestGenConfig(use_llm=False)
        result = generate_template_tests(module_file)

        assert f"test_{long_name}" in result

    def test_nested_classes(self, tmp_path):
        """Handle nested classes"""
        module_file = tmp_path / "nested.py"
        module_file.write_text(
            """
class Outer:
    class Inner:
        def method(self):
            pass
"""
        )

        TestGenConfig(use_llm=False)
        result = generate_template_tests(module_file)

        # Should generate tests for methods
        assert "import pytest" in result
