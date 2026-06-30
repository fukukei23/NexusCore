"""パッケージ import と lazy __getattr__ の検証。"""
import sys

def test_import_brownfield_does_not_load_gradio():
    """import brownfield だけでは gradio を読み込まない（lazy __getattr__）。"""
    sys.modules.pop("gradio", None)
    sys.modules.pop("brownfield", None)
    import brownfield  # noqa: F401
    assert "gradio" not in sys.modules, "lazy __getattr__ 失敗: gradio が読み込まれた"

def test_getattr_main():
    sys.modules.pop("brownfield", None)
    import brownfield
    assert callable(brownfield.main)

def test_getattr_build_ui():
    sys.modules.pop("brownfield", None)
    import brownfield
    assert callable(brownfield.build_ui)

def test_getattr_unknown_raises():
    sys.modules.pop("brownfield", None)
    import brownfield
    import pytest
    with pytest.raises(AttributeError):
        brownfield.nonexistent_attr
