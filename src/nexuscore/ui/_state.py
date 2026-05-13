from __future__ import annotations

import glob
from dataclasses import dataclass, field
from pathlib import Path


def list_test_files() -> list[str]:
    """sandbox_output/, tests/, ルート直下の .py ファイル一覧を返す"""
    files: list[str] = []
    for pattern in [
        "sandbox_output/**/*.py",
        "tests/**/*.py",
        "*.py",
    ]:
        for p in glob.glob(pattern, recursive=True):
            files.append(p)
    return sorted(set(files))


def list_dirs_with_py() -> list[str]:
    """.py ファイルを含むディレクトリ一覧を返す"""
    dirs: set[str] = set()
    for p in list_test_files():
        dirs.add(str(Path(p).parent))
    return sorted(dirs)


def list_files_in_dir(directory: str) -> list[str]:
    """指定ディレクトリ内の .py ファイル一覧"""
    if not directory:
        return []
    return sorted(
        str(Path(p).name) for p in list_test_files() if str(Path(p).parent) == directory
    )


@dataclass
class AppState:
    """アプリケーション全体で共有する State"""

    current_file_path: str | None = None
    generated_code: str | None = None
    latest_test_result: str | None = None
    latest_run_id: str | None = None
    before_code: dict[str, str] = field(default_factory=dict)
    after_code: dict[str, str] = field(default_factory=dict)
