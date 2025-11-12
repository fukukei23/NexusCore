# =============================================================================
# FILE: tests/generated/test_add_generated.py
# DATE: 2025-11-02 (JST)
# ORIGIN: NexusCore TesterAgent (LLM生成テスト)
#
# PURPOSE:
#   - 関数 add(a, b) の振る舞いを網羅的に検証する自動テストスイート。
#   - pytest を使って正常系・異常系・エッジケースをチェックする。
#   - hypothesis を使った property-based test も含む。
#
# REQUIREMENTS:
#   pip install pytest hypothesis
#
# テスト対象:
#   src/nexuscore/utils/math_ops.py
#   def add(a, b):
#       return a + b
#
# 実行コマンド例（PowerShell / プロジェクトルートで）:
#   pytest -v tests/generated/test_add_generated.py
# =============================================================================

import math
import pytest
from hypothesis import given, strategies as st

# 実装対象の関数をインポート
# NOTE: プロジェクトルートから pytest を実行する想定（C:\Users\USER\tools\NexusCore）
# その場合、src/ が import path に入るようにするか、pytest.ini 等で PYTHONPATH を通してください。
from nexuscore.utils.math_ops import add


class TestAddBasicBehavior:
    """
    add(a, b) が Python の `a + b` と同じように振る舞うことを検証する基本セット。
    """

    @pytest.mark.parametrize(
        "a,b,expected",
        [
            (0, 0, 0),
            (1, 2, 3),
            (-1, 1, 0),
            (-5, -7, -12),
            (100, 200, 300),
        ],
    )
    def test_int_addition(self, a, b, expected):
        """整数どうしの通常加算"""
        assert add(a, b) == expected

    @pytest.mark.parametrize(
        "a,b,expected",
        [
            (0.0, 0.0, 0.0),
            (1.5, 2.5, 4.0),
            (-1.1, 1.1, 0.0),
            (0.1, 0.2, 0.3),
        ],
    )
    def test_float_addition(self, a, b, expected):
        """浮動小数点同士の加算は pytest.approx で比較"""
        assert add(a, b) == pytest.approx(expected)

    @pytest.mark.parametrize(
        "a,b,expected",
        [
            ("", "", ""),
            ("a", "b", "ab"),
            ("hello ", "world", "hello world"),
        ],
    )
    def test_str_concatenation(self, a, b, expected):
        """文字列は連結されること"""
        assert add(a, b) == expected

    @pytest.mark.parametrize(
        "a,b,expected",
        [
            ([], [], []),
            ([1], [2], [1, 2]),
            ([1, 2], [3, 4], [1, 2, 3, 4]),
        ],
    )
    def test_list_concatenation(self, a, b, expected):
        """リストは連結されること"""
        assert add(a, b) == expected

    def test_tuple_concatenation(self):
        """タプル同士も + で結合できる"""
        assert add((1, 2), (3,)) == (1, 2, 3)

    def test_large_integers(self):
        """
        非常に大きな整数でオーバーフローせず動作すること。
        (Python int は任意精度整数なので理論上OK)
        """
        big = 10**18
        assert add(big, big) == 2 * big

    def test_special_floats(self):
        """inf / -inf / 巨大数 などの挙動を確認"""
        assert add(float("inf"), 1.0) == float("inf")
        assert add(float("-inf"), 1.0) == float("-inf")

        # 巨大数どうし。結果が inf になることを想定
        # 1e308 + 1e308 は Python では inf になることがある
        huge_sum = add(1e308, 1e308)
        assert math.isinf(huge_sum)


class TestAddErrorAndEdgeCases:
    """
    想定外入力や例外系を確認するテスト。
    “安全に失敗する” 振る舞いを保証する。
    """

    @pytest.mark.parametrize(
        "a,b",
        [
            (1, "2"),
            ("1", 2),
            ([1], 2),
            (1, [2]),
            (None, 1),
            (1, None),
            ({}, []),
        ],
    )
    def test_type_mismatch_raises(self, a, b):
        """
        型が合わないペアは TypeError になることを期待。
        ※ ただし、実際の add 実装が単純な `return a + b` の場合、
          Python がそのまま連結/加算しちゃうケース（str+strなど）は
          エラーにならない。上のパラメータはエラーになりそうなものを列挙。
        """
        with pytest.raises(TypeError):
            _ = add(a, b)

    def test_custom_object_add(self):
        """
        __add__ を実装したカスタムクラス同士の加算もサポートできることを確認。
        """
        class Number:
            def __init__(self, value):
                self.value = value

            def __add__(self, other):
                # 互いに Number 同士なら Number を返す
                if isinstance(other, Number):
                    return Number(self.value + other.value)
                return NotImplemented

            def __eq__(self, other):
                return isinstance(other, Number) and self.value == other.value

        n1 = Number(5)
        n2 = Number(3)
        result = add(n1, n2)
        assert result == Number(8)


# -----------------------------------------------------------------------------
# Property-based tests
# -----------------------------------------------------------------------------

@given(st.integers(), st.integers())
def test_add_commutative_for_ints(x, y):
    """
    交換法則: a + b == b + a
    整数どうしでは常に成り立つはず。
    """
    assert add(x, y) == add(y, x)


@given(
    st.floats(
        allow_nan=False,
        allow_infinity=False
    ),
    st.floats(
        allow_nan=False,
        allow_infinity=False
    ),
)
def test_add_floats_approximate(x, y):
    """
    浮動小数点数の加算結果が x + y と近似的に一致すること。
    （丸め誤差は pytest.approx で吸収）
    """
    assert add(x, y) == pytest.approx(x + y)
