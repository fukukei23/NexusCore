"""
Comprehensive tests for stacktrace_mapper module.

Tests extraction of file paths from Python stacktraces for
Self-Healing target file identification.
"""

import pytest
from nexuscore.core.stacktrace_mapper import extract_candidate_files, STACKTRACE_FILE_RE


class TestStacktraceFileRegex:
    """Tests for the STACKTRACE_FILE_RE regular expression."""

    def test_regex_matches_standard_stacktrace_line(self):
        """Test regex matches standard Python stacktrace format."""
        line = '  File "/app/src/foo/bar.py", line 123, in some_function'
        match = STACKTRACE_FILE_RE.search(line)

        assert match is not None
        assert match.group(1) == "/app/src/foo/bar.py"
        assert match.group(2) == "123"
        assert match.group(3) == "some_function"

    def test_regex_matches_windows_path(self):
        """Test regex matches Windows-style paths."""
        line = '  File "C:\\Users\\test\\project\\main.py", line 42, in main'
        match = STACKTRACE_FILE_RE.search(line)

        assert match is not None
        assert match.group(1) == "C:\\Users\\test\\project\\main.py"
        assert match.group(2) == "42"

    def test_regex_matches_relative_path(self):
        """Test regex matches relative paths."""
        line = '  File "./src/utils.py", line 5, in helper'
        match = STACKTRACE_FILE_RE.search(line)

        assert match is not None
        assert match.group(1) == "./src/utils.py"

    def test_regex_does_not_match_non_file_lines(self):
        """Test regex does not match lines without File pattern."""
        lines = [
            "Traceback (most recent call last):",
            "    return foo()",
            "ValueError: invalid value",
            "    raise Exception('error')",
        ]

        for line in lines:
            assert STACKTRACE_FILE_RE.search(line) is None


class TestExtractCandidateFiles:
    """Tests for extract_candidate_files function."""

    def test_extract_from_simple_stacktrace(self):
        """Test extracting files from simple single-level stacktrace."""
        error_log = '''Traceback (most recent call last):
  File "/app/test.py", line 10, in test_function
    result = divide(10, 0)
ZeroDivisionError: division by zero
'''
        result = extract_candidate_files(error_log)

        assert result == ["/app/test.py"]

    def test_extract_from_multi_level_stacktrace(self):
        """Test extracting files from multi-level stacktrace."""
        error_log = '''Traceback (most recent call last):
  File "/app/main.py", line 5, in <module>
    run_tests()
  File "/app/runner.py", line 20, in run_tests
    execute_test()
  File "/app/executor.py", line 100, in execute_test
    assert False
AssertionError
'''
        result = extract_candidate_files(error_log)

        assert result == ["/app/main.py", "/app/runner.py", "/app/executor.py"]

    def test_extract_maintains_order(self):
        """Test extraction maintains order of appearance in stacktrace."""
        error_log = '''  File "/first.py", line 1, in func1
  File "/second.py", line 2, in func2
  File "/third.py", line 3, in func3
'''
        result = extract_candidate_files(error_log)

        assert result == ["/first.py", "/second.py", "/third.py"]

    def test_extract_removes_duplicates(self):
        """Test duplicate file paths are removed."""
        error_log = '''  File "/app/util.py", line 10, in helper1
  File "/app/main.py", line 20, in process
  File "/app/util.py", line 30, in helper2
  File "/app/main.py", line 40, in validate
'''
        result = extract_candidate_files(error_log)

        # Should keep first occurrence only
        assert result == ["/app/util.py", "/app/main.py"]

    def test_extract_from_pytest_output(self):
        """Test extraction from pytest-style output."""
        error_log = '''=========================== FAILURES ===========================
_______________________ test_something _________________________

    def test_something():
>       assert process_data() == expected
E       AssertionError: assert None == 'expected'

  File "/home/user/project/tests/test_module.py", line 42, in test_something
    assert process_data() == expected
  File "/home/user/project/src/module.py", line 100, in process_data
    return None
'''
        result = extract_candidate_files(error_log)

        assert "/home/user/project/tests/test_module.py" in result
        assert "/home/user/project/src/module.py" in result

    def test_extract_from_empty_string(self):
        """Test extraction from empty error log returns empty list."""
        result = extract_candidate_files("")

        assert result == []

    def test_extract_from_log_without_stacktrace(self):
        """Test extraction from log without stacktrace returns empty list."""
        error_log = '''Running tests...
Test suite completed.
All tests passed.
'''
        result = extract_candidate_files(error_log)

        assert result == []

    def test_extract_with_mixed_content(self):
        """Test extraction ignores non-stacktrace lines."""
        error_log = '''Some debug output
  File "/app/test.py", line 5, in test
    do_something()
More debug output
  File "/app/module.py", line 10, in do_something
    raise ValueError()
Final output
'''
        result = extract_candidate_files(error_log)

        assert result == ["/app/test.py", "/app/module.py"]

    def test_extract_with_library_paths(self):
        """Test extraction includes stdlib and library paths."""
        error_log = '''  File "/usr/lib/python3.11/unittest/case.py", line 100, in run
    self._testFunc()
  File "/home/user/project/test.py", line 20, in test_feature
    process()
  File "/home/user/.venv/lib/python3.11/site-packages/requests/api.py", line 50, in get
    return request('get', url)
'''
        result = extract_candidate_files(error_log)

        # All paths should be extracted, not just project files
        assert "/usr/lib/python3.11/unittest/case.py" in result
        assert "/home/user/project/test.py" in result
        assert "/home/user/.venv/lib/python3.11/site-packages/requests/api.py" in result

    def test_extract_preserves_exact_paths(self):
        """Test extraction preserves exact path strings."""
        error_log = '''  File "/app/src/../lib/util.py", line 5, in func
    pass
  File "./relative/path.py", line 10, in another
    pass
'''
        result = extract_candidate_files(error_log)

        # Should preserve paths as-is, no normalization
        assert "/app/src/../lib/util.py" in result
        assert "./relative/path.py" in result

    def test_extract_handles_unicode_paths(self):
        """Test extraction handles Unicode characters in paths."""
        error_log = '''  File "/home/ユーザー/プロジェクト/main.py", line 1, in test
    pass
'''
        result = extract_candidate_files(error_log)

        assert result == ["/home/ユーザー/プロジェクト/main.py"]

    def test_extract_handles_paths_with_spaces(self):
        """Test extraction handles paths with spaces."""
        error_log = '''  File "/home/user/My Projects/app/main.py", line 10, in run
    execute()
'''
        result = extract_candidate_files(error_log)

        assert result == ["/home/user/My Projects/app/main.py"]

    def test_extract_from_real_pytest_failure(self):
        """Test extraction from realistic pytest failure output."""
        error_log = '''============================= FAILURES =============================
___________________ TestMyClass.test_method ____________________

self = <tests.test_my_class.TestMyClass object at 0x7f8a3c>

    def test_method(self):
        obj = MyClass()
>       result = obj.process(invalid_input)
E       ValueError: Invalid input provided

tests/test_my_class.py:25: ValueError

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/usr/lib/python3.11/unittest/runner.py", line 652, in run
    testMethod()
  File "/home/user/project/tests/test_my_class.py", line 25, in test_method
    result = obj.process(invalid_input)
  File "/home/user/project/src/my_class.py", line 100, in process
    raise ValueError("Invalid input provided")
ValueError: Invalid input provided
'''
        result = extract_candidate_files(error_log)

        assert "/usr/lib/python3.11/unittest/runner.py" in result
        assert "/home/user/project/tests/test_my_class.py" in result
        assert "/home/user/project/src/my_class.py" in result

    def test_extract_handles_lines_with_extra_whitespace(self):
        """Test extraction handles lines with varying whitespace."""
        error_log = '''  File "/app/main.py", line 1, in func1
    File "/app/util.py", line 2, in func2
      File "/app/helper.py", line 3, in func3
'''
        result = extract_candidate_files(error_log)

        # All should be extracted regardless of leading whitespace
        assert "/app/main.py" in result
        assert "/app/util.py" in result
        assert "/app/helper.py" in result
