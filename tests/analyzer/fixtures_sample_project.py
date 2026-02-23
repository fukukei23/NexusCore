"""
テスト用ミニプロジェクトのフィクスチャ

graph_builder / unified_analyzer / test_generator 用の
最小限のサンプル Python プロジェクトを作る。
"""

import textwrap
from pathlib import Path

import pytest


@pytest.fixture
def sample_project_dir(tmp_path: Path) -> Path:
    """
    graph_builder / unified_analyzer / test_generator 用の
    最小限のサンプル Python プロジェクトを作る。
    """
    root = tmp_path / "sample_project"
    root.mkdir()

    # __init__.py
    (root / "__init__.py").write_text("", encoding="utf-8")

    # module_a.py
    (root / "module_a.py").write_text(
        textwrap.dedent(
            """
            from .module_b import add_one


            def main(x: int) -> int:
                return add_one(x)
            """
        ).lstrip(),
        encoding="utf-8",
    )

    # module_b.py
    (root / "module_b.py").write_text(
        textwrap.dedent(
            """
            def add_one(x: int) -> int:
                return x + 1
            """
        ).lstrip(),
        encoding="utf-8",
    )

    return root
