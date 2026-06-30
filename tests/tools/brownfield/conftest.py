"""brownfield テスト用 path 調整。

pytest の prepend import mode は tests/tools/__init__.py 不在のため
tests/tools/ を sys.path に挿入し、空の tests/tools/brownfield/__init__.py が
実パッケージ tools/brownfield/ を隠蔽してしまう。spec 3.2 の shim と同じく
tools/ を sys.path 先頭に置き、実パッケージを優先させる。
"""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_TOOLS_DIR = _REPO_ROOT / "tools"
_tools_str = str(_TOOLS_DIR)
if _tools_str not in sys.path:
    sys.path.insert(0, _tools_str)
