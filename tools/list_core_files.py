"""
重要ファイルリスト生成ツール
--------------------------------
Git 管理下のファイルから、開発でよく参照するパスだけを抽出し、
シークレット (.env など) や巨大ログを自動的に除外する。
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Sequence


DEFAULT_INCLUDES: List[str] = [
    "README.md",
    "pyproject.toml",
    "requirements*.txt",
    "main_cli.py",
    "src/nexuscore",
    "tools",
    "tests",
]

DEFAULT_EXCLUDES: List[str] = [
    ".env",
    ".env.*",
    "logs/**",
    "exports/**",
    "codex_history/**",
    "*.log",
    "*.tmp",
    "*.bak",
    "__pycache__/**",
]


def _git_tracked_files(repo_root: Path) -> List[str]:
    """git ls-files でトラッキングされているファイルを取得する。"""
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _matches_any(path: str, patterns: Sequence[str]) -> bool:
    return any(
        path == pattern
        or path.startswith(pattern.rstrip("/") + "/")
        or fnmatch.fnmatch(path, pattern)
        for pattern in patterns
    )


def filter_paths(
    paths: Iterable[str],
    includes: Sequence[str],
    excludes: Sequence[str],
) -> List[str]:
    """include / exclude パターンでファイルリストをフィルタリングする。"""
    includes = [p for p in includes if p]
    excludes = [p for p in excludes if p]

    filtered: List[str] = []
    for path in paths:
        if includes and not _matches_any(path, includes):
            continue
        if excludes and _matches_any(path, excludes):
            continue
        filtered.append(path)
    return filtered


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="NexusCore: 開発で重要なファイル一覧を抽出するツール"
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="リポジトリのルートパス (デフォルト: カレントディレクトリ)",
    )
    parser.add_argument(
        "--include",
        nargs="*",
        default=DEFAULT_INCLUDES,
        help=f"含めるパターン (デフォルト: {', '.join(DEFAULT_INCLUDES)})",
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=DEFAULT_EXCLUDES,
        help=f"除外パターン (デフォルト: {', '.join(DEFAULT_EXCLUDES)})",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="出力形式 (text or json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/core_files.txt"),
        help="書き出すファイルパス（既定: output/core_files.txt）",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    repo_root = args.root.resolve()

    try:
        tracked = _git_tracked_files(repo_root)
    except subprocess.CalledProcessError as exc:
        parser.error(f"git ls-files 実行に失敗しました: {exc.stderr or exc}")
        return 1

    filtered = filter_paths(tracked, args.include, args.exclude)

    if args.format == "json":
        payload = {"root": str(repo_root), "files": filtered}
        output_text = json.dumps(payload, ensure_ascii=False, indent=2)
    else:
        header = f"# NexusCore tracked files ({len(filtered)} entries)"
        body = "\n".join(filtered)
        output_text = f"{header}\n{body}"

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output_text, encoding="utf-8")
    else:
        print(output_text)

    return 0


if __name__ == "__main__":
    sys.exit(main())
