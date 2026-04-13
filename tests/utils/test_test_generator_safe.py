from unittest.mock import patch


def test_test_generator_generate(monkeypatch):
    # _call_minimax をモックして、MiniMax APIの代わりに固定文字列を返す
    with patch("nexuscore.utils.test_generator._call_minimax", return_value="generated tests"):
        from nexuscore.utils.test_generator import generate_unit_tests

        out = generate_unit_tests("def add(x, y): return x + y")
        # generate_unit_tests は文字列を返すはず
        assert isinstance(out, str)
