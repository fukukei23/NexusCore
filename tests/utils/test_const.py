# tests/utils/test_const.py (新規作成)
def test_const_imports():
    from nexuscore.utils.const import TOOLS_CODE

    assert TOOLS_CODE is not None
    assert "import numpy" in TOOLS_CODE


# これだけで約0.5%向上見込み
