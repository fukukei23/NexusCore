import pytest
from sample import add_two_integers

def test_add_two_integers():
    assert add_two_integers(1, 2) == 3
    assert add_two_integers(-1, -2) == -3
    assert add_two_integers(0, 0) == 0

    with pytest.raises(TypeError):
        add_two_integers("1", 2)

    with pytest.raises(TypeError):
        add_two_integers(1, "2")