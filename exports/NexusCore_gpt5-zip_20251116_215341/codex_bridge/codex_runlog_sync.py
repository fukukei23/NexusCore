"""
Codex RunLog ⇔ NexusCore Postmortem ブリッジ
================================================

Codex が保持する実行ログを NexusCore の Postmortem Agent に同期する。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Tuple

from nexuscore.agents.postmortem_agent import PostmortemAgent

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNLOG_DIR = REPO_ROOT / "codex_bridge" / "runlogs"
RUNLOG_DIR.mkdir(parents=True, exist_ok=True)


def _timestamp() -> str:
    jst = timezone(timedelta(hours=9))
    return datetime.now(jst).strftime("%Y%m%d-%H%M%S")


def save_runlog(runlog_payload: dict | str, run_context: str) -> Tuple[Path, Path]:
    """
    RunLog と実行時コンテキストをファイルに保存する。

    Args:
        runlog_payload: dict もしくは JSON 文字列。
        run_context: Codex が持つ追加情報（テキスト）。
    Returns:
        (json_path, context_path)
    """
    ts = _timestamp()
    json_path = RUNLOG_DIR / f"{ts}_runlog.json"
    context_path = RUNLOG_DIR / f"{ts}_run_context.txt"

    if isinstance(runlog_payload, str):
        try:
            data = json.loads(runlog_payload)
        except json.JSONDecodeError:
            data = {"raw": runlog_payload}
    else:
        data = runlog_payload

    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    context_path.write_text(run_context.strip(), encoding="utf-8")
    return json_path, context_path


def send_runlog_to_postmortem(runlog_path: str) -> None:
    """
    保存済み RunLog を PostmortemAgent へ送信する。

    Args:
        runlog_path: JSON ファイルのパス。
    """
    path = Path(runlog_path)
    if not path.exists():
        raise FileNotFoundError(f"RunLog file not found: {runlog_path}")

    runlog_text = path.read_text(encoding="utf-8")
    agent = PostmortemAgent()
    agent.record_failure(runlog_text, source="codex")


if __name__ == "__main__":
    sample_json, sample_txt = save_runlog({"status": "ok"}, "manual trigger")
    send_runlog_to_postmortem(str(sample_json))
