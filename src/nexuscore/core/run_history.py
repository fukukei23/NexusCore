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
from typing import Any, Dict, Optional, List, Tuple


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

        # 通知を送信（オプション）
        self._send_notification(record)

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

    def get_last_self_healing_runs(self, limit: int = 30) -> List[Dict[str, Any]]:
        """
        Self-Healing 実行履歴のうち、直近 limit 件を返す。

        Args:
            limit: 取得する件数（デフォルト: 30）

        Returns:
            直近の実行履歴のリスト（新しい順）
        """
        all_runs = self.load_runs("self_healing")
        # finished_at でソート（新しい順）
        sorted_runs = sorted(
            all_runs,
            key=lambda r: r.get("finished_at", 0),
            reverse=True,
        )
        return sorted_runs[:limit]

    def calculate_success_rate(self, limit: int = 30) -> Tuple[float, int, int]:
        """
        過去 limit 回の Self-Healing 実行の成功率を計算する。

        Args:
            limit: 対象とする実行回数（デフォルト: 30）

        Returns:
            (success_rate, success_count, total_count)
            - success_rate: 成功率（%）
            - success_count: 成功回数（status == "fixed"）
            - total_count: 総実行回数
        """
        runs = self.get_last_self_healing_runs(limit=limit)
        total = len(runs)
        if total == 0:
            return 0.0, 0, 0

        success = sum(1 for r in runs if r.get("status") == "fixed")
        success_rate = round(success / total * 100, 1) if total > 0 else 0.0

        return success_rate, success, total

    def _send_notification(self, record: RunRecord) -> None:
        """
        実行完了時に通知を送信する（オプション）。
        """
        try:
            from nexuscore.core.notifier import get_notifier

            notifier = get_notifier()
            if not notifier:
                return

            # Self-Healing の場合
            if record.kind == "self_healing":
                notifier.notify_self_healing_complete(
                    repo_full_name=record.repo_full_name or "unknown",
                    pr_number=record.pr_number or 0,
                    status=record.status,
                    summary=record.summary or "",
                    run_id=record.run_id,
                    details=record.details,
                )
            # その他の種類の通知は必要に応じて追加
        except Exception:
            # 通知失敗は致命的ではないので握りつぶす
            pass

