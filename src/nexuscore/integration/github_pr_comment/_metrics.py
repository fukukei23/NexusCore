"""
PR comment metrics collection and URL construction.

Extracted from github_pr_comment.py for single-responsibility.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

# Webapp モデルはオプショナルインポート（webapp が利用可能な場合のみ）
try:
    from nexuscore.webapp import db
    from nexuscore.webapp.models import ExecutionLog, PatchRecord, Run

    HAS_WEBAPP = True
except ImportError:
    HAS_WEBAPP = False
    Run = None
    PatchRecord = None
    ExecutionLog = None
    db = None

try:
    from nexuscore.config.unified_config import get_config as _get_config

    _webapp_base_url = _get_config().webapp_base_url
except ImportError:
    import os

    _webapp_base_url = os.getenv("WEBAPP_BASE_URL", "http://localhost:5000")


def _format_duration(run: object) -> str:
    """実行時間をフォーマットする"""
    if not HAS_WEBAPP or not hasattr(run, "started_at") or not hasattr(run, "finished_at"):
        return "N/A"

    if not run.started_at or not run.finished_at:
        return "N/A"

    delta = run.finished_at - run.started_at
    total_seconds = int(delta.total_seconds())

    if total_seconds < 60:
        return f"{total_seconds}s"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}m {seconds}s"
    else:
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours}h {minutes}m"


def _estimate_diff_lines(diff_text: str) -> int:
    """diff テキストから変更行数を推定（簡易版）"""
    if not diff_text:
        return 0

    lines = diff_text.splitlines()
    count = 0
    for line in lines:
        if line.startswith("+") or line.startswith("-"):
            if not line.startswith("+++") and not line.startswith("---"):
                count += 1

    return count


def _estimate_diff_lines_separated(diff_text: str) -> tuple[int, int]:
    """diff テキストから追加行数と削除行数を分けて推定（CR-E3）"""
    if not diff_text:
        return (0, 0)

    lines = diff_text.splitlines()
    added = 0
    removed = 0

    for line in lines:
        if line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            removed += 1

    return (added, removed)


def _collect_run_metrics(run: object) -> dict:
    """
    Run からメトリクスを収集する（CR-E3: 追加行数/削除行数を分けて収集）

    Returns:
        dict with keys: duration_str, patch_files_count, patch_lines,
        added_lines, removed_lines, model_call_counts, estimated_cost_jpy,
        start_time, end_time, duration_seconds
    """
    if not HAS_WEBAPP:
        return {
            "duration_str": "N/A",
            "patch_files_count": 0,
            "patch_lines": 0,
            "added_lines": 0,
            "removed_lines": 0,
            "model_call_counts": {},
            "estimated_cost_jpy": 0.0,
            "start_time": None,
            "end_time": None,
            "duration_seconds": 0.0,
        }

    patch_files = set()
    total_patch_lines = 0
    total_added_lines = 0
    total_removed_lines = 0

    try:
        if hasattr(run, "id") and PatchRecord:
            patches = PatchRecord.query.filter_by(run_id=run.id).all()
            for p in patches:
                patch_files.add(p.file_path)
                diff_text = p.diff_text or ""
                total_patch_lines += _estimate_diff_lines(diff_text)
                added, removed = _estimate_diff_lines_separated(diff_text)
                total_added_lines += added
                total_removed_lines += removed
    except Exception as e:
        logger.warning(f"Failed to collect patch metrics: {e}", exc_info=True)

    models: defaultdict[str, int] = defaultdict(int)
    total_cost = 0.0

    try:
        if hasattr(run, "id") and ExecutionLog:
            logs = ExecutionLog.query.filter_by(run_id=run.id, source="NPE").all()
            for lg in logs:
                payload = lg.payload_json or {}
                if isinstance(payload, str):
                    try:
                        payload = json.loads(payload)
                    except Exception:
                        payload = {}

                model = payload.get("model") or payload.get("model_name") or "unknown"
                models[model] += 1

                cost = (
                    payload.get("estimated_cost")
                    or payload.get("cost_jpy")
                    or payload.get("usage", {}).get("cost_jpy", 0.0)
                )
                try:
                    total_cost += float(cost)
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"Failed to collect LLM metrics: {e}", exc_info=True)

    start_time = None
    end_time = None
    duration_seconds = 0.0

    if hasattr(run, "started_at") and run.started_at:
        start_time = run.started_at
    if hasattr(run, "finished_at") and run.finished_at:
        end_time = run.finished_at

    if start_time and end_time:
        delta = end_time - start_time
        duration_seconds = delta.total_seconds()

    return {
        "duration_str": _format_duration(run),
        "patch_files_count": len(patch_files),
        "patch_lines": total_patch_lines,
        "added_lines": total_added_lines,
        "removed_lines": total_removed_lines,
        "model_call_counts": dict(models),
        "estimated_cost_jpy": total_cost,
        "start_time": start_time,
        "end_time": end_time,
        "duration_seconds": duration_seconds,
    }


def _compute_recent_success_rate(project_id: int, limit: int = 30) -> float:
    """過去N回の成功率を計算する"""
    if not HAS_WEBAPP or not Run:
        return 0.0

    try:
        q = (
            Run.query.filter(Run.project_id == project_id)
            .order_by(Run.started_at.desc().nullslast())
            .limit(limit)
        )
        runs = q.all()

        if not runs:
            return 0.0

        success = sum(1 for r in runs if hasattr(r, "status") and r.status == "SUCCESS")
        return success / len(runs)
    except Exception as e:
        logger.warning(f"Failed to compute success rate: {e}", exc_info=True)
        return 0.0


def build_run_logs_url(project_id: int, run: object) -> str:
    """Run ログの URL を構築する"""
    base = _webapp_base_url.rstrip("/")
    if hasattr(run, "run_id"):
        return f"{base}/logs/runs/{run.run_id}"
    elif hasattr(run, "id"):
        return f"{base}/logs/runs/{run.id}"
    else:
        return f"{base}/logs/runs/unknown"


def build_project_logs_url(project_id: int) -> str:
    """プロジェクトログの URL を構築する"""
    base = _webapp_base_url.rstrip("/")
    return f"{base}/logs/projects/{project_id}"


def build_project_dashboard_url(project_id: int) -> str:
    """プロジェクトダッシュボードの URL を構築する"""
    base = _webapp_base_url.rstrip("/")
    return f"{base}/dashboard/projects/{project_id}"
