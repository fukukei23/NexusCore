"""
Comprehensive tests for math_ops module.
Tests basic mathematical operations.
"""

import pytest
from nexuscore.utils.math_ops import add


# ==============================================================================
# add Function Tests
# ==============================================================================


class TestAdd:
    """Test add function"""

    def test_add_positive_integers(self):
        """Add two positive integers"""
        result = add(2, 3)
        assert result == 5

    def test_add_negative_integers(self):
        """Add two negative integers"""
        result = add(-5, -3)
        assert result == -8

    def test_add_mixed_sign_integers(self):
        """Add positive and negative integers"""
        result = add(10, -3)
        assert result == 7

    def test_add_with_zero(self):
        """Add with zero"""
        assert add(5, 0) == 5
        assert add(0, 5) == 5
        assert add(0, 0) == 0

    def test_add_floats(self):
        """Add floating point numbers"""
        result = add(2.5, 3.7)
        assert result == pytest.approx(6.2)

    def test_add_negative_floats(self):
        """Add negative floating point numbers"""
        result = add(-2.5, -1.5)
        assert result == pytest.approx(-4.0)

    def test_add_mixed_float_int(self):
        """Add float and integer"""
        result = add(2.5, 3)
        assert result == pytest.approx(5.5)

    def test_add_large_numbers(self):
        """Add large numbers"""
        result = add(1000000, 2000000)
        assert result == 3000000

    def test_add_very_small_numbers(self):
        """Add very small floating point numbers"""
        result = add(0.0001, 0.0002)
        assert result == pytest.approx(0.0003)

    def test_add_commutative_property(self):
        """Add is commutative: a + b = b + a"""
        assert add(3, 5) == add(5, 3)
        assert add(2.5, 7.3) == add(7.3, 2.5)

    def test_add_associative_property(self):
        """Add is associative: (a + b) + c = a + (b + c)"""
        a, b, c = 2, 3, 5
        assert add(add(a, b), c) == add(a, add(b, c))

    def test_add_identity_element(self):
        """Zero is the identity element: a + 0 = a"""
        assert add(42, 0) == 42
        assert add(0, 42) == 42

    def test_add_negative_result(self):
        """Addition resulting in negative number"""
        result = add(5, -10)
        assert result == -5

    def test_add_strings_concatenation(self):
        """Add strings (concatenation)"""
        result = add("hello", "world")
        assert result == "helloworld"

    def test_add_empty_strings(self):
        """Add empty strings"""
        assert add("", "") == ""
        assert add("test", "") == "test"
        assert add("", "test") == "test"

    def test_add_lists_concatenation(self):
        """Add lists (concatenation)"""
        result = add([1, 2], [3, 4])
        assert result == [1, 2, 3, 4]

    def test_add_empty_lists(self):
        """Add empty lists"""
        assert add([], []) == []
        assert add([1, 2], []) == [1, 2]
        assert add([], [1, 2]) == [1, 2]

    def test_add_tuples(self):
        """Add tuples (concatenation)"""
        result = add((1, 2), (3, 4))
        assert result == (1, 2, 3, 4)
