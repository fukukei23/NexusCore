"""brownfield orchestrator パッケージ。

import 時に gradio を引かないよう lazy 読み込みする。
"""
from typing import TYPE_CHECKING

__all__ = ["main", "build_ui"]

def __getattr__(name):
    if name == "main":
        from .__main__ import main
        return main
    if name == "build_ui":
        from .ui import build_ui
        return build_ui
    raise AttributeError(f"module 'brownfield' has no attribute {name!r}")

if TYPE_CHECKING:
    from .__main__ import main as main  # noqa: F401
    from .ui import build_ui as build_ui  # noqa: F401
