"""shim 経由起動と main(argv) のテスト。"""
import sys
import pytest

def test_main_help_exits_zero(capsys):
    """main(['--help']) は SystemExit(0)。"""
    from brownfield.__main__ import main
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    assert "--ui" in capsys.readouterr().out

def test_shim_module_loads_main():
    """shim ファイル経由で main が解決できる（sys.path 注入経路）。"""
    from pathlib import Path
    tools_dir = str(Path(__file__).resolve().parents[3] / "tools")
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    import importlib
    mod = importlib.import_module("brownfield.__main__")
    assert callable(mod.main)
