"""
Comprehensive tests for json_sanitizer module.
Covers all edge cases, fence removal, JSON extraction, and error handling.
"""

import json

from nexuscore.utils.json_sanitizer import sanitize_json_like

# ==============================================================================
# Dict/List Pass-Through Tests
# ==============================================================================


class TestDictListPassThrough:
    """Test that dict and list are returned unchanged"""

    def test_sanitize_dict_unchanged(self):
        """Dict is returned unchanged"""
        input_dict = {"key": "value", "number": 42}
        result = sanitize_json_like(input_dict)

        assert result == input_dict
        assert result is input_dict  # Same object

    def test_sanitize_empty_dict_unchanged(self):
        """Empty dict is returned unchanged"""
        input_dict = {}
        result = sanitize_json_like(input_dict)

        assert result == {}
        assert result is input_dict

    def test_sanitize_nested_dict_unchanged(self):
        """Nested dict is returned unchanged"""
        input_dict = {"level1": {"level2": {"level3": "deep"}}}
        result = sanitize_json_like(input_dict)

        assert result == input_dict
        assert result is input_dict

    def test_sanitize_list_unchanged(self):
        """List is returned unchanged"""
        input_list = [1, 2, 3, "four"]
        result = sanitize_json_like(input_list)

        assert result == input_list
        assert result is input_list

    def test_sanitize_empty_list_unchanged(self):
        """Empty list is returned unchanged"""
        input_list = []
        result = sanitize_json_like(input_list)

        assert result == []
        assert result is input_list

    def test_sanitize_nested_list_unchanged(self):
        """Nested list is returned unchanged"""
        input_list = [1, [2, [3, [4]]]]
        result = sanitize_json_like(input_list)

        assert result == input_list
        assert result is input_list


# ==============================================================================
# Code Fence Removal Tests
# ==============================================================================


class TestCodeFenceRemoval:
    """Test removal of markdown code fences"""

    def test_sanitize_removes_json_fence(self):
        """Removes ```json fence from JSON object"""
        input_str = '```json\\n{"key": "value"}\\n```'
        result = sanitize_json_like(input_str)

        assert result == {"key": "value"}

    def test_sanitize_removes_plain_fence(self):
        """Removes plain ``` fence from JSON object"""
        input_str = '```\\n{"key": "value"}\\n```'
        result = sanitize_json_like(input_str)

        assert result == {"key": "value"}

    def test_sanitize_removes_fence_with_whitespace(self):
        """Removes fence with extra whitespace"""
        input_str = '  ```json  \\n  {"key": "value"}  \\n  ```  '
        result = sanitize_json_like(input_str)

        assert result == {"key": "value"}

    def test_sanitize_removes_fence_from_array(self):
        """Removes fence from JSON array"""
        input_str = "```json\\n[1, 2, 3]\\n```"
        result = sanitize_json_like(input_str)

        assert result == [1, 2, 3]

    def test_sanitize_removes_fence_with_text_before(self):
        """Removes fence and extracts JSON with text before"""
        input_str = '```json\\nHere is the data:\\n{"key": "value"}\\n```'
        result = sanitize_json_like(input_str)

        assert result == {"key": "value"}


# ==============================================================================
# JSON Extraction Tests
# ==============================================================================


class TestJSONExtraction:
    """Test extraction of JSON from strings with surrounding text"""

    def test_sanitize_extracts_json_with_prefix(self):
        """Extracts JSON object with text before it"""
        input_str = 'The result is: {"success": true, "count": 5}'
        result = sanitize_json_like(input_str)

        assert result == {"success": True, "count": 5}

    def test_sanitize_extracts_json_with_suffix(self):
        """Extracts JSON object with text after it"""
        input_str = '{"data": "value"} - end of output'
        result = sanitize_json_like(input_str)

        assert result == {"data": "value"}

    def test_sanitize_extracts_json_with_both(self):
        """Extracts JSON object with text before and after"""
        input_str = 'Start: {"key": "value"} :End'
        result = sanitize_json_like(input_str)

        assert result == {"key": "value"}

    def test_sanitize_extracts_array_with_prefix(self):
        """Extracts JSON array with text before it"""
        input_str = "The items are: [1, 2, 3, 4, 5]"
        result = sanitize_json_like(input_str)

        assert result == [1, 2, 3, 4, 5]

    def test_sanitize_extracts_nested_json(self):
        """Extracts nested JSON object"""
        input_str = 'Result: {"outer": {"inner": {"deep": "value"}}}'
        result = sanitize_json_like(input_str)

        assert result == {"outer": {"inner": {"deep": "value"}}}

    def test_sanitize_extracts_json_with_arrays(self):
        """Extracts JSON object containing arrays"""
        input_str = '{"items": [1, 2, 3], "names": ["a", "b"]}'
        result = sanitize_json_like(input_str)

        assert result == {"items": [1, 2, 3], "names": ["a", "b"]}

    def test_sanitize_extracts_array_of_objects(self):
        """Extracts array of JSON objects"""
        input_str = '[{"id": 1}, {"id": 2}, {"id": 3}]'
        result = sanitize_json_like(input_str)

        assert result == [{"id": 1}, {"id": 2}, {"id": 3}]


# ==============================================================================
# Complex Cases Tests
# ==============================================================================


class TestComplexCases:
    """Test complex real-world scenarios"""

    def test_sanitize_llm_response_with_explanation(self):
        """Sanitizes typical LLM response with explanation"""
        input_str = """Here's the JSON response you requested:

```json
{
    "status": "success",
    "data": {
        "items": [1, 2, 3],
        "count": 3
    }
}
```

This contains the data you need."""

        result = sanitize_json_like(input_str)

        assert result == {"status": "success", "data": {"items": [1, 2, 3], "count": 3}}

    def test_sanitize_json_with_unicode(self):
        """Sanitizes JSON with Unicode characters"""
        input_str = '{"message": "こんにちは", "emoji": "🎉"}'
        result = sanitize_json_like(input_str)

        assert result == {"message": "こんにちは", "emoji": "🎉"}

    def test_sanitize_json_with_escaped_quotes(self):
        """Sanitizes JSON with escaped quotes"""
        input_str = '{"quote": "She said \\"Hello\\""}'
        result = sanitize_json_like(input_str)

        assert result == {"quote": 'She said "Hello"'}

    def test_sanitize_json_with_numbers(self):
        """Sanitizes JSON with various number types"""
        input_str = '{"int": 42, "float": 3.14, "negative": -10, "exp": 1e5}'
        result = sanitize_json_like(input_str)

        assert result == {"int": 42, "float": 3.14, "negative": -10, "exp": 1e5}

    def test_sanitize_json_with_booleans_and_null(self):
        """Sanitizes JSON with boolean and null values"""
        input_str = '{"active": true, "deleted": false, "value": null}'
        result = sanitize_json_like(input_str)

        assert result == {"active": True, "deleted": False, "value": None}

    def test_sanitize_multiline_json(self):
        """Sanitizes multiline formatted JSON"""
        input_str = """{
    "key1": "value1",
    "key2": "value2",
    "nested": {
        "inner": "data"
    }
}"""
        result = sanitize_json_like(input_str)

        assert result == {"key1": "value1", "key2": "value2", "nested": {"inner": "data"}}


# ==============================================================================
# Error Handling and Edge Cases
# ==============================================================================


class TestErrorHandling:
    """Test error handling for invalid inputs"""

    def test_sanitize_returns_string_for_no_json(self):
        """Returns original string when no JSON found"""
        input_str = "This is just plain text without JSON"
        result = sanitize_json_like(input_str)

        assert result == input_str

    def test_sanitize_returns_string_for_invalid_json(self):
        """Returns original string for invalid JSON"""
        input_str = '{"key": invalid}'
        result = sanitize_json_like(input_str)

        assert result == input_str

    def test_sanitize_returns_string_for_incomplete_json(self):
        """Returns original string for incomplete JSON"""
        input_str = '{"key": "value"'  # Missing closing brace
        result = sanitize_json_like(input_str)

        assert result == input_str

    def test_sanitize_returns_string_for_only_opening_brace(self):
        """Returns original string for only opening brace"""
        input_str = "Some text { more text"
        result = sanitize_json_like(input_str)

        assert result == input_str

    def test_sanitize_returns_string_for_only_closing_brace(self):
        """Returns original string for only closing brace"""
        input_str = "Some text } more text"
        result = sanitize_json_like(input_str)

        assert result == input_str

    def test_sanitize_returns_string_for_reversed_braces(self):
        """Returns original string for reversed braces"""
        input_str = "} text {"
        result = sanitize_json_like(input_str)

        assert result == input_str

    def test_sanitize_empty_string(self):
        """Returns empty string for empty input"""
        result = sanitize_json_like("")

        assert result == ""

    def test_sanitize_whitespace_only(self):
        """Returns whitespace string for whitespace-only input"""
        input_str = "   \\n  \\t  "
        result = sanitize_json_like(input_str)

        # After stripping fences, it will be whitespace
        assert isinstance(result, str)

    def test_sanitize_returns_int_unchanged(self):
        """Returns integer unchanged"""
        result = sanitize_json_like(42)

        assert result == 42

    def test_sanitize_returns_float_unchanged(self):
        """Returns float unchanged"""
        result = sanitize_json_like(3.14)

        assert result == 3.14

    def test_sanitize_returns_none_unchanged(self):
        """Returns None unchanged"""
        result = sanitize_json_like(None)

        assert result is None

    def test_sanitize_returns_bool_unchanged(self):
        """Returns boolean unchanged"""
        assert sanitize_json_like(True) is True
        assert sanitize_json_like(False) is False


# ==============================================================================
# Bracket Priority Tests
# ==============================================================================


class TestBracketPriority:
    """Test handling when both { and [ are present"""

    def test_sanitize_multiple_json_structures_returns_original(self):
        """Returns original when multiple separate JSON structures present"""
        # { comes first, but combined extraction creates invalid JSON
        input_str = '{"obj": "data"} and [1, 2, 3]'
        result = sanitize_json_like(input_str)

        # Cannot parse two separate structures, returns original
        assert result == input_str

    def test_sanitize_array_and_object_returns_original(self):
        """Returns original when array and object are separate"""
        input_str = '[1, 2, 3] and {"key": "value"}'
        result = sanitize_json_like(input_str)

        # Cannot parse two separate structures, returns original
        assert result == input_str

    def test_sanitize_nested_mixed_structures(self):
        """Handles nested mixed structures"""
        input_str = '{"array": [1, 2, 3], "value": "test"}'
        result = sanitize_json_like(input_str)

        assert result == {"array": [1, 2, 3], "value": "test"}


# ==============================================================================
# Real-World LLM Output Tests
# ==============================================================================


class TestRealWorldLLMOutputs:
    """Test with realistic LLM outputs"""

    def test_sanitize_chatgpt_style_response(self):
        """Sanitizes ChatGPT-style response"""
        input_str = """Sure! Here's the JSON:

```json
{
    "name": "John Doe",
    "age": 30,
    "email": "john@example.com"
}
```

Is there anything else you need?"""

        result = sanitize_json_like(input_str)

        assert result == {"name": "John Doe", "age": 30, "email": "john@example.com"}

    def test_sanitize_claude_style_response(self):
        """Sanitizes Claude-style response"""
        input_str = """I'll provide the data in JSON format:

```json
{
    "status": "complete",
    "results": ["item1", "item2", "item3"]
}
```"""

        result = sanitize_json_like(input_str)

        assert result == {"status": "complete", "results": ["item1", "item2", "item3"]}

    def test_sanitize_inline_json_response(self):
        """Sanitizes inline JSON without fences"""
        input_str = 'The API response is {"code": 200, "message": "OK"} as shown above.'
        result = sanitize_json_like(input_str)

        assert result == {"code": 200, "message": "OK"}

    def test_sanitize_json_with_code_fence_and_prefix(self):
        """Sanitizes JSON with fence and explanatory text"""
        input_str = """Based on your request, here's the configuration:

```json
{
    "debug": false,
    "timeout": 30,
    "retries": 3
}
```

This should work for your use case."""

        result = sanitize_json_like(input_str)

        assert result == {"debug": False, "timeout": 30, "retries": 3}


# ==============================================================================
# Special Characters Tests
# ==============================================================================


class TestSpecialCharacters:
    """Test handling of special characters in JSON"""

    def test_sanitize_json_with_newlines_in_string(self):
        """Sanitizes JSON with newlines in string values"""
        input_str = '{"text": "Line1\\\\nLine2\\\\nLine3"}'
        result = sanitize_json_like(input_str)

        assert result == {"text": "Line1\\nLine2\\nLine3"}

    def test_sanitize_json_with_tabs(self):
        """Sanitizes JSON with tab characters"""
        input_str = '{"text": "Column1\\\\tColumn2"}'
        result = sanitize_json_like(input_str)

        assert result == {"text": "Column1\\tColumn2"}

    def test_sanitize_json_with_special_chars(self):
        """Sanitizes JSON with special characters"""
        input_str = '{"symbols": "!@#$%^&*()_+-=[]{}|;:,.<>?/"}'
        result = sanitize_json_like(input_str)

        assert result == {"symbols": "!@#$%^&*()_+-=[]{}|;:,.<>?/"}

    def test_sanitize_json_with_backslashes(self):
        """Sanitizes JSON with backslashes"""
        input_str = '{"path": "C:\\\\\\\\Users\\\\\\\\file.txt"}'
        result = sanitize_json_like(input_str)

        assert result == {"path": "C:\\\\Users\\\\file.txt"}


# ==============================================================================
# Performance and Size Tests
# ==============================================================================


class TestPerformanceAndSize:
    """Test with large and complex inputs"""

    def test_sanitize_large_json_object(self):
        """Sanitizes large JSON object"""
        large_dict = {f"key_{i}": f"value_{i}" for i in range(100)}
        input_str = json.dumps(large_dict)
        result = sanitize_json_like(input_str)

        assert result == large_dict

    def test_sanitize_large_json_array(self):
        """Sanitizes large JSON array"""
        large_array = list(range(1000))
        input_str = json.dumps(large_array)
        result = sanitize_json_like(input_str)

        assert result == large_array

    def test_sanitize_deeply_nested_structure(self):
        """Sanitizes deeply nested JSON structure"""
        nested = {"level": 1}
        current = nested
        for i in range(2, 11):
            current["nested"] = {"level": i}
            current = current["nested"]

        input_str = json.dumps(nested)
        result = sanitize_json_like(input_str)

        assert result == nested
