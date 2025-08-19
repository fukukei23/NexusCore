import pytest
from app.main import add

class TestAdd:
    def test_add_positive_integers(self):
        assert add(1, 2) == 3

    def test_add_negative_integers(self):
        assert add(-1, -2) == -3

    def test_add_positive_float_and_integer(self):
        assert add(1.5, 2) == 3.5

    def test_add_negative_float_and_integer(self):
        assert add(-1.5, 2) == 0.5

    def test_add_zero(self):
        assert add(0, 0) == 0

    def test_add_large_numbers(self):
        assert add(1000000000, 2000000000) == 3000000000

    def test_add_small_numbers(self):
        assert add(0.000000001, 0.000000002) == 0.000000003

    def test_add_invalid_input_type_string(self):
        with pytest.raises(TypeError):
            add("1", 2)

    def test_add_invalid_input_type_list(self):
        with pytest.raises(TypeError):
            add([1], 2)