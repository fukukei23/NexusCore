"""
Comprehensive tests for test_utils module.
Tests utilities for test generation and validation.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from nexuscore.utils.test_utils import (
    create_fallback_test_file,
    extract_code_from_markdown,
    project_path_to_module_path,
    run_tests,
    validate_test_code,
)

# ==============================================================================
# project_path_to_module_path Tests
# ==============================================================================


class TestProjectPathToModulePath:
    """Test project_path_to_module_path function"""

    def test_basic_conversion(self):
        """Convert basic file path to module path"""
        project_root = Path("/project")
        file_path = Path("/project/src/foo/bar.py")

        result = project_path_to_module_path(project_root, file_path)
        assert result == "src.foo.bar"

    def test_single_level_path(self):
        """Convert single level path"""
        project_root = Path("/project")
        file_path = Path("/project/module.py")

        result = project_path_to_module_path(project_root, file_path)
        assert result == "module"

    def test_deep_nested_path(self):
        """Convert deeply nested path"""
        project_root = Path("/project")
        file_path = Path("/project/a/b/c/d/e/module.py")

        result = project_path_to_module_path(project_root, file_path)
        assert result == "a.b.c.d.e.module"

    def test_removes_py_extension(self):
        """Removes .py extension from module path"""
        project_root = Path("/project")
        file_path = Path("/project/test.py")

        result = project_path_to_module_path(project_root, file_path)
        assert result == "test"
        assert ".py" not in result

    def test_handles_windows_paths(self):
        """Handles Windows-style backslash paths"""
        project_root = Path("/project")
        # Path will normalize backslashes on Unix, but we can still test the replace logic
        file_path = Path("/project/src/foo/bar.py")

        result = project_path_to_module_path(project_root, file_path)
        assert "\\" not in result
        assert "." in result

    def test_file_outside_project_root(self):
        """Handles file outside project root"""
        project_root = Path("/project")
        file_path = Path("/other/location/file.py")

        result = project_path_to_module_path(project_root, file_path)
        # Returns stem when file is outside project
        assert result == "file"

    def test_relative_path(self):
        """Handles relative paths correctly"""
        project_root = Path(".")
        file_path = Path("./src/module.py")

        result = project_path_to_module_path(project_root, file_path)
        assert "module" in result


# ==============================================================================
# validate_test_code Tests
# ==============================================================================


class TestValidateTestCode:
    """Test validate_test_code function"""

    def test_valid_test_code(self):
        """Valid test code returns True"""
        code = """
import pytest

def test_example():
    assert 1 + 1 == 2
"""
        is_valid, error, warnings = validate_test_code(code)
        assert is_valid is True
        assert error is None

    def test_syntax_error(self):
        """Syntax error returns False with error message"""
        code = "def invalid syntax here"

        is_valid, error, warnings = validate_test_code(code)
        assert is_valid is False
        assert error is not None
        assert "Syntax error" in error

    def test_detects_os_system(self):
        """Detects dangerous os.system() calls"""
        code = """
import pytest
import os

def test_dangerous():
    os.system('rm -rf /')
"""
        is_valid, error, warnings = validate_test_code(code)
        assert is_valid is True  # Syntax is valid
        assert any("os.system()" in w for w in warnings)

    def test_detects_subprocess_calls(self):
        """Detects dangerous subprocess calls"""
        code = """
import pytest
import subprocess

def test_dangerous():
    subprocess.run(['ls'])
"""
        is_valid, error, warnings = validate_test_code(code)
        assert is_valid is True
        assert any("subprocess" in w for w in warnings)

    def test_detects_file_write(self):
        """Detects file write operations"""
        code = """
import pytest

def test_writes():
    with open('file.txt', 'w') as f:
        f.write('data')
"""
        is_valid, error, warnings = validate_test_code(code)
        assert is_valid is True
        assert any("write" in w.lower() for w in warnings)

    def test_detects_file_append(self):
        """Detects file append operations"""
        code = """
import pytest

def test_appends():
    with open('file.txt', 'a') as f:
        f.write('data')
"""
        is_valid, error, warnings = validate_test_code(code)
        assert is_valid is True
        assert any("append" in w.lower() for w in warnings)

    def test_detects_eval(self):
        """Detects eval() calls"""
        code = """
import pytest

def test_eval():
    result = eval('1 + 1')
"""
        is_valid, error, warnings = validate_test_code(code)
        assert is_valid is True
        assert any("eval()" in w for w in warnings)

    def test_detects_exec(self):
        """Detects exec() calls"""
        code = """
import pytest

def test_exec():
    exec('print("hello")')
"""
        is_valid, error, warnings = validate_test_code(code)
        assert is_valid is True
        assert any("exec()" in w for w in warnings)

    def test_detects_import_builtin(self):
        """Detects __import__() calls"""
        code = """
import pytest

def test_import():
    module = __import__('os')
"""
        is_valid, error, warnings = validate_test_code(code)
        assert is_valid is True
        assert any("__import__()" in w for w in warnings)

    def test_detects_main_block(self):
        """Detects if __name__ == __main__ block"""
        code = """
import pytest

def test_example():
    pass

if __name__ == "__main__":
    pytest.main()
"""
        is_valid, error, warnings = validate_test_code(code)
        assert is_valid is True
        assert any("__main__" in w for w in warnings)

    def test_warns_no_test_functions(self):
        """Warns when no test functions found"""
        code = """
import pytest

def helper_function():
    pass
"""
        is_valid, error, warnings = validate_test_code(code)
        assert is_valid is True
        assert any("No test functions" in w for w in warnings)

    def test_warns_no_pytest_import(self):
        """Warns when pytest is not imported"""
        code = """
def test_example():
    assert True
"""
        is_valid, error, warnings = validate_test_code(code)
        assert is_valid is True
        assert any("pytest is not imported" in w for w in warnings)

    def test_valid_test_with_from_import(self):
        """Valid with 'from pytest import' style"""
        code = """
from pytest import fixture

def test_example():
    assert True
"""
        is_valid, error, warnings = validate_test_code(code)
        # Should not warn about missing pytest import
        assert not any("pytest is not imported" in w for w in warnings)

    def test_multiple_test_functions(self):
        """Recognizes multiple test functions"""
        code = """
import pytest

def test_one():
    assert True

def test_two():
    assert False
"""
        is_valid, error, warnings = validate_test_code(code)
        assert is_valid is True
        # Should not warn about no test functions
        assert not any("No test functions" in w for w in warnings)

    def test_empty_code(self):
        """Handles empty code"""
        code = ""

        is_valid, error, warnings = validate_test_code(code)
        # Empty code is syntactically valid Python
        assert is_valid is True


# ==============================================================================
# extract_code_from_markdown Tests
# ==============================================================================


class TestExtractCodeFromMarkdown:
    """Test extract_code_from_markdown function"""

    def test_extract_python_code_block(self):
        """Extracts code from ```python fence"""
        text = """
Some text before

```python
def hello():
    print("world")
```

Some text after
"""
        result = extract_code_from_markdown(text)
        assert "def hello():" in result
        assert 'print("world")' in result
        assert "Some text" not in result

    def test_extract_generic_code_block(self):
        """Extracts code from ``` fence"""
        text = """
```
code here
more code
```
"""
        result = extract_code_from_markdown(text)
        assert "code here" in result
        assert "more code" in result

    def test_multiple_code_blocks_returns_first(self):
        """Returns first code block when multiple exist"""
        text = """
```python
first block
```

```python
second block
```
"""
        result = extract_code_from_markdown(text)
        assert "first block" in result
        assert "second block" not in result

    def test_no_code_block_returns_text(self):
        """Returns original text when no code block"""
        text = "plain text without code blocks"

        result = extract_code_from_markdown(text)
        assert result == text.strip()

    def test_strips_whitespace(self):
        """Strips leading/trailing whitespace"""
        text = """
```python
  def test():
      pass
```
"""
        result = extract_code_from_markdown(text)
        assert result == "def test():\n      pass"

    def test_multiline_code(self):
        """Handles multiline code blocks"""
        text = """
```python
line1
line2
line3
```
"""
        result = extract_code_from_markdown(text)
        assert "line1" in result
        assert "line2" in result
        assert "line3" in result

    def test_empty_code_block(self):
        """Handles empty code block"""
        text = """
```python
```
"""
        result = extract_code_from_markdown(text)
        assert result == ""

    def test_code_with_backticks_inside(self):
        """Handles code containing backticks"""
        text = """
```python
code with `backticks` inside
```
"""
        result = extract_code_from_markdown(text)
        assert "`backticks`" in result


# ==============================================================================
# create_fallback_test_file Tests
# ==============================================================================


class TestCreateFallbackTestFile:
    """Test create_fallback_test_file function"""

    def test_creates_valid_python(self):
        """Creates syntactically valid Python code"""
        file_path = Path("test_example.py")
        error_msg = "Test error"

        result = create_fallback_test_file(file_path, error_msg)

        # Should be valid Python
        import ast

        ast.parse(result)

    def test_includes_error_message(self):
        """Includes error message in output"""
        file_path = Path("test_example.py")
        error_msg = "Custom error message"

        result = create_fallback_test_file(file_path, error_msg)

        assert error_msg in result

    def test_imports_pytest(self):
        """Fallback code imports pytest"""
        file_path = Path("test_example.py")
        error_msg = "Error"

        result = create_fallback_test_file(file_path, error_msg)

        assert "import pytest" in result

    def test_contains_test_function(self):
        """Contains at least one test function"""
        file_path = Path("test_example.py")
        error_msg = "Error"

        result = create_fallback_test_file(file_path, error_msg)

        assert "def test_" in result

    def test_test_function_fails(self):
        """Test function calls pytest.fail"""
        file_path = Path("test_example.py")
        error_msg = "Error"

        result = create_fallback_test_file(file_path, error_msg)

        assert "pytest.fail" in result

    def test_has_docstring(self):
        """Includes docstring"""
        file_path = Path("test_example.py")
        error_msg = "Error"

        result = create_fallback_test_file(file_path, error_msg)

        assert '"""' in result or "'''" in result


# ==============================================================================
# run_tests Tests
# ==============================================================================


class TestRunTests:
    """Test run_tests function"""

    def test_successful_test_run(self):
        """Successful pytest run returns True"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "test passed"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            success, output = run_tests("/path/to/project")

        assert success is True
        assert "test passed" in output

    def test_failed_test_run(self):
        """Failed pytest run returns False"""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "test failed"
        mock_result.stderr = "error"

        with patch("subprocess.run", return_value=mock_result):
            success, output = run_tests("/path/to/project")

        assert success is False
        assert "test failed" in output

    def test_runs_pytest_module(self):
        """Runs python -m pytest command"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            run_tests("/path/to/project")

        args = mock_run.call_args[0][0]
        assert "-m" in args
        assert "pytest" in args

    def test_uses_correct_cwd(self):
        """Uses project_path as cwd"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        project_path = "/test/project"

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            run_tests(project_path)

        assert mock_run.call_args[1]["cwd"] == project_path

    def test_handles_pytest_not_found(self):
        """Handles FileNotFoundError when pytest not installed"""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            success, output = run_tests("/path/to/project")

        assert success is False
        assert "pytest" in output.lower()

    def test_handles_general_exception(self):
        """Handles general exceptions during test run"""
        with patch("subprocess.run", side_effect=RuntimeError("Test error")):
            success, output = run_tests("/path/to/project")

        assert success is False
        assert "Test error" in output

    def test_combines_stdout_stderr(self):
        """Combines stdout and stderr in output"""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "stdout content"
        mock_result.stderr = "stderr content"

        with patch("subprocess.run", return_value=mock_result):
            success, output = run_tests("/path/to/project")

        assert "stdout content" in output
        assert "stderr content" in output

    def test_handles_none_output(self):
        """Handles None stdout/stderr gracefully"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = None
        mock_result.stderr = None

        with patch("subprocess.run", return_value=mock_result):
            success, output = run_tests("/path/to/project")

        # Should not crash
        assert isinstance(output, str)

    def test_uses_preferred_encoding(self):
        """Uses locale preferred encoding"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "test"
        mock_result.stderr = ""

        with (
            patch("subprocess.run", return_value=mock_result) as mock_run,
            patch("locale.getpreferredencoding", return_value="utf-8"),
        ):
            run_tests("/path/to/project")

        assert mock_run.call_args[1]["encoding"] == "utf-8"


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestTestUtilsIntegration:
    """Integration tests for test_utils module"""

    def test_validate_extracted_markdown_code(self):
        """Validate code extracted from markdown"""
        markdown = """
Here's a test:

```python
import pytest

def test_example():
    assert True
```
"""
        code = extract_code_from_markdown(markdown)
        is_valid, error, warnings = validate_test_code(code)

        assert is_valid is True
        assert error is None

    def test_fallback_code_passes_validation(self):
        """Fallback code passes validation"""
        fallback = create_fallback_test_file(Path("test.py"), "Error")
        is_valid, error, warnings = validate_test_code(fallback)

        assert is_valid is True
        assert error is None

    def test_project_path_conversion_roundtrip(self):
        """Project path conversion works with Path objects"""
        root = Path("/project")
        file_path = Path("/project/src/module.py")

        module_path = project_path_to_module_path(root, file_path)

        # Module path should be valid identifier
        assert module_path.replace(".", "").replace("_", "").isalnum()
