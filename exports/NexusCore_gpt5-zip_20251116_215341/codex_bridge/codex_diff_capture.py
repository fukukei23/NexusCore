"""
Codex ⇔ NexusCore クリティカル差分ブリッジ
================================================

Codex が Apply Patch などで致命的な修正を行った際に、
その diff と要約をローカルファイルへ保存し、必要に応じて
Git コミットまで自動実行するユーティリティ。

WSL / Windows いずれのパス環境でも動作するよう pathlib を採用。
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
DIFF_DIR = REPO_ROOT / "codex_bridge" / "diffs"
DIFF_DIR.mkdir(parents=True, exist_ok=True)


def _timestamp() -> str:
    """JST ベースの timestamp を生成（例: 20251115-075047）。"""
    jst = timezone(timedelta(hours=9))
    return datetime.now(jst).strftime("%Y%m%d-%H%M%S")


def save_critical_diff(diff_text: str, summary_text: str) -> Tuple[Path, Path]:
    """
    Codex のクリティカル diff を patch/txt に保存する。

    Returns:
        (patch_path, summary_path)
    """
    if not diff_text.strip():
        raise ValueError("diff_text is empty; nothing to store.")

    ts = _timestamp()
    patch_path = DIFF_DIR / f"{ts}_critical.patch"
    summary_path = DIFF_DIR / f"{ts}_codex_summary.txt"

    patch_path.write_text(diff_text, encoding="utf-8")
    summary_path.write_text(summary_text.strip() or "No summary provided.", encoding="utf-8")

    return patch_path, summary_path


def commit_diff_to_git(message: str, repo_path: Path | None = None) -> None:
    """
    codex_bridge/diffs 以下を Git コミットする。

    Args:
        message: Codex から渡される短い要約。コミットメッセージに挿入される。
        repo_path: リポジトリルート。未指定なら REPO_ROOT を利用。
    """
    repo_path = repo_path or REPO_ROOT
    commit_msg = f"[CodexCriticalFix] {message.strip() or 'Auto patch'}"

    subprocess.run(["git", "add", "codex_bridge/diffs"], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", commit_msg], cwd=repo_path, check=True)


if __name__ == "__main__":
    # 簡易テスト
    p, s = save_critical_diff("--- sample diff ---\n", "Sample summary")
    print("Saved:", p, s)
