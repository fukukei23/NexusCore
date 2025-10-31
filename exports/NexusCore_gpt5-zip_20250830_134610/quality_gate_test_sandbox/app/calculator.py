def add_two_numbers(a: int, b: int) -> int:
    """
    Create a function 'add' that takes two integers 'a' and 'b' and returns their sum.
    """
    return a + b


def test_add_two_numbers():
    """Test cases for add_two_numbers function."""
    assert add_two_numbers(2, 3) == 5
    assert add_two_numbers(-2, 3) == 1
    assert add_two_numbers(2, -3) == -1
    assert add_two_numbers(0, 0) == 0
    assert add_two_numbers(100, 200) == 300