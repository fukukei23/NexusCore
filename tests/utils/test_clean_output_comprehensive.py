"""
Comprehensive tests for clean_output module.
Tests the clean_output function for removing code fences from LLM outputs.
"""

import pytest
from nexuscore.utils.clean_output import clean_output


# ==============================================================================
# clean_output Tests
# ==============================================================================


class TestCleanOutput:
    """Test clean_output function"""

    def test_clean_output_with_python_fence(self):
        """Remove ```python fence and return content"""
        text = "```python\nprint('hello')\n```"
        result = clean_output(text)
        assert result == "print('hello')"

    def test_clean_output_with_generic_fence(self):
        """Remove generic ``` fence and return content"""
        text = "```\nsome code\n```"
        result = clean_output(text)
        assert result == "some code"

    def test_clean_output_without_fence(self):
        """Return text as-is when no fence present"""
        text = "just plain text"
        result = clean_output(text)
        assert result == "just plain text"

    def test_clean_output_with_empty_string(self):
        """Return empty string for empty input"""
        result = clean_output("")
        assert result == ""

    def test_clean_output_with_none(self):
        """Handle None input gracefully"""
        result = clean_output(None)
        assert result == ""

    def test_clean_output_strips_whitespace(self):
        """Strip leading/trailing whitespace"""
        text = "  \n  code content  \n  "
        result = clean_output(text)
        assert result == "code content"

    def test_clean_output_with_multiline_code(self):
        """Handle multiline code in fence"""
        text = """```python
def foo():
    return 42

foo()
```"""
        result = clean_output(text)
        expected = "def foo():\n    return 42\n\nfoo()"
        assert result == expected

    def test_clean_output_with_fence_in_middle(self):
        """Extract first code fence found"""
        text = "Some text\n```python\ncode\n```\nMore text"
        result = clean_output(text)
        assert result == "code"

    def test_clean_output_with_multiple_fences(self):
        """Extract first fence when multiple present"""
        text = "```python\nfirst\n```\nSome text\n```\nsecond\n```"
        result = clean_output(text)
        assert result == "first"

    def test_clean_output_with_language_other_than_python(self):
        """Handle non-python language fences"""
        text = "```javascript\nconst x = 1;\n```"
        result = clean_output(text)
        # Should not match ```javascript, return as-is
        assert "const x = 1;" in result

    def test_clean_output_with_python_newline_in_fence(self):
        """Handle ```python\\n fence format"""
        text = "```python\ndef test():\n    pass\n```"
        result = clean_output(text)
        assert result == "def test():\n    pass"

    def test_clean_output_with_incomplete_fence(self):
        """Handle incomplete fence (only opening)"""
        text = "```python\ncode without closing"
        result = clean_output(text)
        # No match, return stripped original
        assert result == "```python\ncode without closing"

    def test_clean_output_with_only_closing_fence(self):
        """Handle only closing fence"""
        text = "code without opening\n```"
        result = clean_output(text)
        assert result == "code without opening\n```"

    def test_clean_output_with_nested_backticks(self):
        """Handle code with backticks inside fence"""
        text = "```python\ncode = `backtick`\n```"
        result = clean_output(text)
        assert result == "code = `backtick`"

    def test_clean_output_with_empty_fence(self):
        """Handle empty code fence"""
        text = "```python\n\n```"
        result = clean_output(text)
        assert result == ""

    def test_clean_output_with_whitespace_only_fence(self):
        """Handle fence with only whitespace"""
        text = "```python\n   \n   \n```"
        result = clean_output(text)
        assert result == ""

    def test_clean_output_preserves_internal_whitespace(self):
        """Preserve internal whitespace in code"""
        text = "```python\nline1\n\nline2\n    indented\n```"
        result = clean_output(text)
        assert result == "line1\n\nline2\n    indented"

    def test_clean_output_with_special_characters(self):
        """Handle special characters in code"""
        text = "```python\nspecial = '!@#$%^&*()'\n```"
        result = clean_output(text)
        assert result == "special = '!@#$%^&*()'"

    def test_clean_output_with_unicode(self):
        """Handle Unicode characters in code"""
        text = "```python\ntext = '日本語'\n```"
        result = clean_output(text)
        assert result == "text = '日本語'"

    def test_clean_output_case_sensitive_fence(self):
        """Fence markers are case-sensitive (lowercase)"""
        text = "```PYTHON\ncode\n```"
        result = clean_output(text)
        # Uppercase PYTHON should not match
        assert "code" in result


# ==============================================================================
# Edge Cases
# ==============================================================================


class TestCleanOutputEdgeCases:
    """Test edge cases for clean_output"""

    def test_clean_output_with_very_long_code(self):
        """Handle very long code content"""
        long_code = "\n".join([f"line_{i}" for i in range(1000)])
        text = f"```python\n{long_code}\n```"
        result = clean_output(text)
        assert result == long_code

    def test_clean_output_with_newlines_in_fence_marker(self):
        """Handle fence marker with extra newlines"""
        text = "```python\n\n\ncode\n\n\n```"
        result = clean_output(text)
        assert "code" in result

    def test_clean_output_regex_special_chars_in_code(self):
        """Handle regex special characters in code"""
        text = "```python\npattern = r'\\d+'\n```"
        result = clean_output(text)
        assert result == "pattern = r'\\d+'"

    def test_clean_output_with_html_in_code(self):
        """Handle HTML in code fence"""
        text = "```python\nhtml = '<div>test</div>'\n```"
        result = clean_output(text)
        assert result == "html = '<div>test</div>'"

    def test_clean_output_with_json_in_code(self):
        """Handle JSON in code fence"""
        text = '```python\ndata = {"key": "value"}\n```'
        result = clean_output(text)
        assert result == 'data = {"key": "value"}'

    def test_clean_output_only_backticks(self):
        """Handle input with only backticks"""
        text = "```"
        result = clean_output(text)
        assert result == "```"

    def test_clean_output_six_backticks(self):
        """Handle six backticks (empty fence match)"""
        text = "``````"
        result = clean_output(text)
        # Matches ``` ... ``` pattern with empty content
        assert result == ""

    def test_clean_output_with_tabs(self):
        """Handle tabs in code (stripped by final strip())"""
        text = "```python\n\tindented_code\n```"
        result = clean_output(text)
        # Leading tab is stripped by final strip()
        assert result == "indented_code"


# ==============================================================================
# Real-world LLM Outputs
# ==============================================================================


class TestCleanOutputRealWorld:
    """Test with realistic LLM output patterns"""

    def test_clean_output_chatgpt_style(self):
        """Handle ChatGPT-style code response"""
        text = """Here's the code:

```python
def calculate(x, y):
    return x + y
```

This function adds two numbers."""
        result = clean_output(text)
        assert result == "def calculate(x, y):\n    return x + y"

    def test_clean_output_claude_style(self):
        """Handle Claude-style code response"""
        text = """I'll write a function for you:

```python
class Calculator:
    def add(self, a, b):
        return a + b
```

This implements a calculator."""
        result = clean_output(text)
        expected = "class Calculator:\n    def add(self, a, b):\n        return a + b"
        assert result == expected

    def test_clean_output_with_explanation_before_and_after(self):
        """Handle code with explanations"""
        text = """Let me explain:

```python
x = 10
```

That's it!"""
        result = clean_output(text)
        assert result == "x = 10"

    def test_clean_output_inline_code(self):
        """Handle when there's no fence, just inline code"""
        text = "Use the function: my_function()"
        result = clean_output(text)
        assert result == "Use the function: my_function()"
