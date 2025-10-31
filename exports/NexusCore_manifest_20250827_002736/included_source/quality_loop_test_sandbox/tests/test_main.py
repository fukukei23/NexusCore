import pytest
from app.main import greet

# 正常系テスト
@pytest.mark.parametrize("name, expected", [
    ("Alice", "Hello, Alice!"),
    ("Bob", "Hello, Bob!"),
    ("", "Hello, !")  # 空文字列のテスト
])
def test_greet_normal(name, expected):
    assert greet(name) == expected

# 異常系テスト
@pytest.mark.parametrize("name", [
    None,  # Noneを渡した場合
    123,   # 数値を渡した場合
    [],    # リストを渡した場合
    {}     # 辞書を渡した場合
])
def test_greet_invalid_input(name):
    with pytest.raises(TypeError):
        greet(name)

# エッジケーステスト
@pytest.mark.parametrize("name, expected", [
    (" ", "Hello,  !"),  # スペースのみ
    ("A" * 1000, "Hello, " + "A" * 1000 + "!")  # 非常に長い名前
])
def test_greet_edge_cases(name, expected):
    assert greet(name) == expected