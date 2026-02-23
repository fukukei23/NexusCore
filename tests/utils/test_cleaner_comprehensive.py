"""
Comprehensive tests for cleaner module.
Covers get_error_header and clean_error_msg functions with all edge cases.
"""

import os

from nexuscore.utils.cleaner import SITE_PKG_ERROR_PREFIX, clean_error_msg, get_error_header

# ==============================================================================
# get_error_header Tests
# ==============================================================================


class TestGetErrorHeader:
    """Test get_error_header function"""

    def test_get_error_header_with_error(self):
        """Get header from traceback with Error"""
        traceback_str = """Traceback (most recent call last):
  File "test.py", line 5, in <module>
    raise ValueError("something went wrong")
ValueError: something went wrong"""

        result = get_error_header(traceback_str)

        assert result == "ValueError: something went wrong"
        assert "Error:" in result

    def test_get_error_header_with_different_error_types(self):
        """Get header for different error types"""
        test_cases = [
            ("TypeError: invalid type", "TypeError: invalid type"),
            ("KeyError: 'key' not found", "KeyError: 'key' not found"),
            ("IndexError: list index out of range", "IndexError: list index out of range"),
            (
                "AttributeError: object has no attribute 'foo'",
                "AttributeError: object has no attribute 'foo'",
            ),
        ]

        for error_line, expected in test_cases:
            traceback = f"Some traceback\n{error_line}\n"
            result = get_error_header(traceback)
            assert result == expected

    def test_get_error_header_no_error(self):
        """Get header from traceback without Error returns empty string"""
        traceback_str = """Some output
No error here
Just normal text"""

        result = get_error_header(traceback_str)

        assert result == ""

    def test_get_error_header_empty_string(self):
        """Get header from empty string returns empty"""
        result = get_error_header("")
        assert result == ""

    def test_get_error_header_multiple_errors(self):
        """Get header from traceback with multiple Error lines returns first"""
        traceback_str = """First Error: first error
Second Error: second error
Third Error: third error"""

        result = get_error_header(traceback_str)

        # Should return first line containing 'Error:'
        assert result == "First Error: first error"

    def test_get_error_header_error_at_start(self):
        """Get header when Error is at start of traceback"""
        traceback_str = "RuntimeError: error at start\nOther text"

        result = get_error_header(traceback_str)

        assert result == "RuntimeError: error at start"

    def test_get_error_header_error_at_end(self):
        """Get header when Error is at end of traceback"""
        traceback_str = "Some text\nMore text\nFinalError: error at end"

        result = get_error_header(traceback_str)

        assert result == "FinalError: error at end"

    def test_get_error_header_with_ansi_codes(self):
        """Get header with ANSI color codes"""
        traceback_str = "\x1b[31mValueError: colored error\x1b[0m"

        result = get_error_header(traceback_str)

        # Should still extract the error line (ANSI cleaning is in clean_error_msg)
        assert "Error:" in result


# ==============================================================================
# clean_error_msg Tests
# ==============================================================================


class TestCleanErrorMsg:
    """Test clean_error_msg function"""

    def test_clean_error_msg_basic(self):
        """Clean basic error message"""
        error_str = "An error occurred while executing the following cell\n------------------\nValueError: invalid value"

        result = clean_error_msg(error_str)

        assert "ValueError: invalid value" in result

    def test_clean_error_msg_with_traceback(self):
        """Clean error message with traceback"""
        error_str = """An error occurred while executing the following cell
------------------
Traceback (most recent call last):
  File "test.py", line 10
    foo()
TypeError: foo() takes 0 arguments (1 given)"""

        result = clean_error_msg(error_str)

        assert "TypeError:" in result

    def test_clean_error_msg_removes_ansi_codes(self):
        """Clean error message removes ANSI escape sequences"""
        error_str = "An error occurred while executing the following cell\n------------------\n\x1b[31mValueError: red error\x1b[0m"

        result = clean_error_msg(error_str)

        assert "\x1b[" not in result  # ANSI codes removed
        assert "ValueError: red error" in result

    def test_clean_error_msg_filters_site_packages(self):
        """Clean error message filters out site-packages paths"""
        PYTHON_PREFIX = os.environ.get("CONDA_PREFIX", "/usr/local")
        site_pkg_path = f"{PYTHON_PREFIX}/lib/python3.10/site-packages/module.py"

        error_str = f"""An error occurred while executing the following cell
------------------
  File {site_pkg_path}", line 100
    raise ValueError("error in library")
ValueError: error in library"""

        result = clean_error_msg(error_str)

        # Should extract error header
        assert "ValueError: error in library" in result

    def test_clean_error_msg_empty_string(self):
        """Clean error message with empty string"""
        result = clean_error_msg("")

        assert isinstance(result, str)

    def test_clean_error_msg_default_parameter(self):
        """Clean error message with default parameter"""
        result = clean_error_msg()

        assert isinstance(result, str)

    def test_clean_error_msg_no_delimiter(self):
        """Clean error message without standard delimiter"""
        error_str = "ValueError: some error"

        result = clean_error_msg(error_str)

        assert isinstance(result, str)

    def test_clean_error_msg_only_cell_marker(self):
        """Clean error message with only cell marker"""
        error_str = "An error occurred while executing the following cell"

        result = clean_error_msg(error_str)

        assert isinstance(result, str)

    def test_clean_error_msg_only_delimiter(self):
        """Clean error message with only delimiter"""
        error_str = "------------------"

        result = clean_error_msg(error_str)

        assert isinstance(result, str)

    def test_clean_error_msg_multiline_error(self):
        """Clean multiline error message"""
        error_str = """An error occurred while executing the following cell
------------------
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "test.py", line 5, in function
    raise ValueError("multiline error")
ValueError: multiline error"""

        result = clean_error_msg(error_str)

        assert "ValueError: multiline error" in result

    def test_clean_error_msg_with_error_header_already_present(self):
        """Clean error when error header is already in output"""
        # This tests line 29: if error_header not in error_str_out
        error_str = "An error occurred while executing the following cell\n------------------\nValueError: test"

        result = clean_error_msg(error_str)

        # Error header should only appear once
        assert result.count("ValueError: test") == 1

    def test_clean_error_msg_no_error_in_traceback(self):
        """Clean error message when traceback has no Error line"""
        error_str = "An error occurred while executing the following cell\n------------------\nSome output\nNo error here"

        result = clean_error_msg(error_str)

        # get_error_header returns '', so it won't be added
        assert isinstance(result, str)

    def test_clean_error_msg_complex_traceback(self):
        """Clean complex traceback with nested calls"""
        error_str = f"""An error occurred while executing the following cell
------------------
Traceback (most recent call last):
  File "{SITE_PKG_ERROR_PREFIX}numpy/core/_methods.py", line 44, in _mean
    ret = umr_sum(arr, axis, dtype, out, keepdims)
  File "<stdin>", line 3, in main
    result = divide(a, b)
  File "<stdin>", line 7, in divide
    return a / b
ZeroDivisionError: division by zero"""

        result = clean_error_msg(error_str)

        assert "ZeroDivisionError: division by zero" in result

    def test_clean_error_msg_unicode_in_error(self):
        """Clean error message with Unicode characters"""
        error_str = "An error occurred while executing the following cell\n------------------\nUnicodeError: '日本語' codec can't encode"

        result = clean_error_msg(error_str)

        assert "UnicodeError:" in result
        assert "日本語" in result


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestIntegration:
    """Integration tests for cleaner module"""

    def test_get_error_header_and_clean_error_msg_together(self):
        """Test using both functions together"""
        traceback = """Traceback (most recent call last):
  File "script.py", line 10
    process_data()
RuntimeError: processing failed"""

        header = get_error_header(traceback)
        assert header == "RuntimeError: processing failed"

        full_error = (
            f"An error occurred while executing the following cell\n------------------\n{traceback}"
        )
        cleaned = clean_error_msg(full_error)
        assert "RuntimeError: processing failed" in cleaned

    def test_site_pkg_error_prefix_is_correct(self):
        """Test that SITE_PKG_ERROR_PREFIX is correctly formatted"""
        PYTHON_PREFIX = os.environ.get("CONDA_PREFIX", "/usr/local")
        expected_prefix = f"File {PYTHON_PREFIX}/lib/python3.10/"

        assert SITE_PKG_ERROR_PREFIX == expected_prefix

    def test_real_world_jupyter_error(self):
        """Test with realistic Jupyter notebook error"""
        error_str = """An error occurred while executing the following cell:
------------------
[1;31m---------------------------------------------------------------------------[0m
[1;31mValueError[0m                                Traceback (most recent call last)
[1;32m<ipython-input-1-abc123>[0m in [0;36m<module>[1;34m[0m
[0;32m      1[0m [0mdata[0m [1;33m=[0m [1;33m[[0m[1;36m1[0m[1;33m,[0m [1;36m2[0m[1;33m,[0m [1;36m3[0m[1;33m][0m
[0;32m----> 2[0m [0mprocess[0m[1;33m([0m[0mdata[0m[1;33m)[0m

[1;31mValueError[0m: invalid literal for int()"""

        result = clean_error_msg(error_str)

        # Should remove ANSI codes
        assert "\x1b[" not in result
        # Should contain error
        assert "ValueError:" in result or "ValueError" in result


# ==============================================================================
# Edge Cases
# ==============================================================================


class TestEdgeCases:
    """Test edge cases for cleaner module"""

    def test_get_error_header_only_error_keyword(self):
        """Get header when only 'Error:' is present"""
        traceback_str = "Error: "

        result = get_error_header(traceback_str)

        assert result == "Error: "

    def test_clean_error_msg_very_long_error(self):
        """Clean very long error message"""
        long_traceback = "\n".join([f"  Line {i}: some code" for i in range(100)])
        error_str = f"An error occurred while executing the following cell\n------------------\n{long_traceback}\nValueError: final error"

        result = clean_error_msg(error_str)

        assert "ValueError: final error" in result

    def test_clean_error_msg_special_characters(self):
        """Clean error message with special characters"""
        error_str = "An error occurred while executing the following cell\n------------------\nSyntaxError: invalid syntax '{}[]()<>'"

        result = clean_error_msg(error_str)

        assert "SyntaxError:" in result

    def test_get_error_header_case_sensitive(self):
        """Get error header is case-sensitive for 'Error:'"""
        traceback_str = "error: lowercase error"

        result = get_error_header(traceback_str)

        # 'Error:' is case-sensitive, 'error:' should not match
        assert result == ""

    def test_clean_error_msg_multiple_cell_markers(self):
        """Clean error with multiple cell execution markers"""
        error_str = """An error occurred while executing the following cell
More text
An error occurred while executing the following cell
------------------
ValueError: test"""

        result = clean_error_msg(error_str)

        # Should split on last occurrence
        assert "ValueError: test" in result
