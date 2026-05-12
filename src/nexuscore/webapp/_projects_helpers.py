"""
Run表示ユーティリティ（ヘルパー関数）

views_projects.py から抽出。Run一覧テーブル描画に使用。
"""

from __future__ import annotations

from collections.abc import Sequence

from flask import render_template

from nexuscore.webapp.models import Project, Run


def _format_duration(duration_sec: float | None) -> str:
    """
    実行時間をフォーマットする
    """
    if duration_sec is None:
        return "-"

    sec = int(duration_sec)
    if sec < 60:
        return f"{sec}s"

    minutes, s = divmod(sec, 60)
    if minutes < 60:
        return f"{minutes}m {s}s"

    hours, m = divmod(minutes, 60)
    return f"{hours}h {m}m"


def _compute_run_duration(run: Run) -> float | None:
    """
    Run の実行時間を計算する（秒）
    """
    if not run.started_at or not run.finished_at:
        return None
    return (run.finished_at - run.started_at).total_seconds()


def _render_run_status_badge(status: str) -> str:
    """
    ステータスごとに色付きバッジ＋アイコンを返す。

    - PENDING: 灰色・時計アイコン
    - RUNNING: 青・▶（再生）アイコン（点滅風CSS）
    - SUCCESS: 緑・✔
    - FAILED: 赤・✖
    """
    s = (status or "").upper()

    if s == "RUNNING":
        css = "status-badge status-running"
        icon = "▶"
        label = "RUNNING"
    elif s == "SUCCESS":
        css = "status-badge status-success"
        icon = "✔"
        label = "SUCCESS"
    elif s == "FAILED":
        css = "status-badge status-failed"
        icon = "✖"
        label = "FAILED"
    else:
        css = "status-badge status-pending"
        icon = "⏱"
        label = s or "PENDING"

    return f'<span class="{css}">{icon} {label}</span>'


def render_run_table(project: Project, runs: Sequence[Run]) -> str:
    """Run一覧テーブルをテンプレートで生成する。"""
    runs_ctx = []
    for r in runs:
        duration_sec = _compute_run_duration(r)
        runs_ctx.append({
            "run_id": r.run_id,
            "status": r.status,
            "_duration_str": _format_duration(duration_sec),
            "_started_str": r.started_at.isoformat(sep=" ", timespec="seconds") if r.started_at else "-",
            "_finished_str": r.finished_at.isoformat(sep=" ", timespec="seconds") if r.finished_at else "-",
        })
    return render_template("components/run_table.html", runs=runs_ctx)
