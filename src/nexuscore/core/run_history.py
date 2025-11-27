"""
run_history.py

Self-Healing や Orchestrator など、NexusCore の長時間タスクについて
1 実行ごとに JSONL 形式で履歴を記録するユーティリティ。

- 保存先: <project_root>/.nexus/history/{kind}.log.jsonl
- 1 行 = 1 実行の RunRecord (JSON)
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, Optional, List


@dataclass
class RunRecord:
    """
    1 回の実行（Self-Healing / Full Project Run など）を表すデータ構造。
    """
    run_id: str
    session_id: str
    kind: str              # 例: "self_healing", "full_project"
    status: str            # "fixed" / "not_fixed" / "no_issues" / "error" / etc.
    started_at: float
    finished_at: float
    repo_full_name: Optional[str] = None
    pr_number: Optional[int] = None
    head_sha: Optional[str] = None
    summary: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


class RunHistoryLogger:
    """
    実行履歴を .nexus/history/{kind}.log.jsonl に追記していくロガー。

    - ログの書き込みに失敗しても、メインロジックは止めない
    - 「あとからダッシュボードで見るためのデータ」を蓄える役割
    """

    def __init__(self, project_root: str) -> None:
        self.project_root = Path(project_root)
        self.history_dir = self.project_root / ".nexus" / "history"
        self.history_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # ログ書き込み
    # ------------------------------------------------------------------
    def log_run(self, record: RunRecord) -> None:
        """
        RunRecord を JSONL として追記保存する。
        """
        path = self.history_dir / f"{record.kind}.log.jsonl"
        data = asdict(record)
        try:
            with path.open("a", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
                f.write("\n")
        except Exception:
            # ログ書き込みに失敗しても致命的ではないので握りつぶす
            # （必要ならここで logging.error を出してもよい）
            pass

    # ------------------------------------------------------------------
    # Self-Healing 用のヘルパー
    # ------------------------------------------------------------------
    def new_self_healing_record(
        self,
        *,
        run_id: str,
        session_id: str,
        repo_full_name: str,
        pr_number: int,
        head_sha: str,
        status: str,
        summary: str,
        details: Dict[str, Any],
        started_at: float,
        finished_at: float,
    ) -> RunRecord:
        """
        Self-Healing 用 RunRecord を生成するショートカット。
        """
        return RunRecord(
            run_id=run_id,
            session_id=session_id,
            kind="self_healing",
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            repo_full_name=repo_full_name,
            pr_number=pr_number,
            head_sha=head_sha,
            summary=summary,
            details=details,
        )

    # ------------------------------------------------------------------
    # 読み出し (将来のダッシュボード用)
    # ------------------------------------------------------------------
    def load_runs(self, kind: str) -> List[Dict[str, Any]]:
        """
        JSONL ファイルから履歴を読み出して list[dict] として返す。
        （今は使わなくても、ダッシュボード実装時に役立つ）
        """
        path = self.history_dir / f"{kind}.log.jsonl"
        if not path.exists():
            return []

        records: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except Exception:
                    # 1行壊れていても全体は読み出せるようにする
                    continue
        return records

