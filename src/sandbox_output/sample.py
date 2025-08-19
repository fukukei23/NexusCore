# encoding: utf-8
import sys
import os
import pytest
from pathlib import Path

# --- sandbox_output をインポートパスに追加 ---
sandbox_path = Path(__file__).parent.parent / "sandbox_output"
if str(sandbox_path) not in sys.path:
    sys.path.append(str(sandbox_path))

try:
    from sample import add_two_integers
except ImportError:
    add_two_integers = None


# --- テストスイート ---
@pytest.mark.skipif(add_two_integers is None, reason="sample.py が見つかりません")
class TestAddTwoIntegers:

    @pytest.mark.parametrize(
        "a, b, expected",
        [(1, 2, 3), (-1, 2, 1), (0, 0, 0), (-5, -10, -15), (10000, 20000, 30000)]
    )
    def test_add_normally(self, a, b, expected):
        assert add_two_integers(a, b) == expected

    @pytest.mark.parametrize(
        "a, b",
        [("1", 2), (1, "2"), (1.5, 2), (1, None)]
    )
    def test_raises_error_with_invalid_types(self, a, b):
        with pytest.raises(ValueError, match=r"入力は整数である必要があります"):
            add_two_integers(a, b)
