from app.calculator import add_two_numbers as add


class TestAdd:
    def test_positive_numbers(self):
        assert add(2, 3) == 5

    def test_negative_numbers(self):
        assert add(-2, -3) == -5

    def test_positive_and_negative(self):
        assert add(2, -3) == -1

    def test_zero(self):
        assert add(0, 0) == 0
        assert add(2, 0) == 2
        assert add(0, -3) == -3

    def test_large_numbers(self):
        assert add(1000000000, 2000000000) == 3000000000

    def test_type_error(self):
        with pytest.raises(TypeError):
            add("string", 2)
        with pytest.raises(TypeError):
            add(2, "string")
        with pytest.raises(TypeError):
            add(2.5, 2)
        with pytest.raises(TypeError):
            add(2, 2.5)