from __future__ import annotations

import json
import os

from flask import Blueprint, jsonify, render_template, request

from nexuscore.webapp.auth import get_current_user, require_auth
from nexuscore.webapp.db_helpers import (
    paginate_query,
    run_llm_cost,
    run_logs_payload,
    run_patch_files,
    user_project_or_404,
)
from nexuscore.webapp.models import ExecutionLog, Project, Run
from nexuscore.webapp.views_projects import (
    _compute_run_duration,
    _format_duration,
    _render_run_status_badge,
)

bp = Blueprint("views_logs", __name__, url_prefix="/logs")

_USD_JPY_RATE = float(os.getenv("NEXUS_USD_JPY_RATE", "150.0"))


@bp.route("/projects/<int:project_id>")
@require_auth
def project_logs(project_id: int):
    """
    プロジェクト単位のログ一覧
    GET /logs/projects/<project_id>?source=NPE&level=ERROR&page=1&per_page=50

    Data access: Direct DB access (no API call)
    FastAPI equivalent: N/A (internal UI only)
    """
    user = get_current_user()
    project = user_project_or_404(user.id, project_id)

    # クエリパラメータ
    source_filter = request.args.get("source")
    level_filter = request.args.get("level")
    per_page = int(request.args.get("per_page", 50))

    # クエリ構築
    query = ExecutionLog.query.join(Run).filter(Run.project_id == project.id)

    if source_filter:
        query = query.filter(ExecutionLog.source == source_filter)
    if level_filter:
        query = query.filter(ExecutionLog.level == level_filter)

    # ページング
    logs, pagination = paginate_query(query, order_column=ExecutionLog.created_at, per_page=per_page)

    logs_data = [
        {
            "id": log.id,
            "run_id": log.run_id,
            "source": log.source,
            "level": log.level,
            "message": log.message,
            "payload_json": log.payload_json,
            "payload_preview": str(log.payload_json)[:100] if log.payload_json else "",
            "created_at": log.created_at.isoformat(),
        }
        for log in logs.items
    ]

    if request.headers.get("Accept", "").startswith("application/json"):
        return jsonify({"logs": logs_data, "pagination": pagination})

    return render_template(
        "logs/project_logs.html",
        project=project,
        logs_data=logs_data,
        source_filter=source_filter,
        level_filter=level_filter,
    )


def _collect_run_display_data(run: Run) -> dict:
    """Run 表示用のメトリクス・Guardian・Diff データを収集する"""
    from nexuscore.integration.github_pr_comment import _collect_run_metrics
    from nexuscore.integration.run_report_generator import get_markdown_report_path

    metrics = _collect_run_metrics(run)
    duration_sec = _compute_run_duration(run)

    patch_files = run_patch_files(run.id)
    retry_count, last_error_class = run_logs_payload(run.id)
    _, _, llm_breakdown = run_llm_cost(run.id)

    guardian_review = None
    for log in ExecutionLog.query.filter_by(run_id=run.id).all():
        payload = log.payload_json or {}
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except (json.JSONDecodeError, ValueError):
                payload = {}
        if payload.get("guardian_review"):
            guardian_review = payload["guardian_review"]
            break

    diff_summary = ""
    try:
        report_path = get_markdown_report_path(run.run_id)
        if report_path.exists():
            md = report_path.read_text(encoding="utf-8")
            if "## AI Diff Summary" in md:
                start = md.find("## AI Diff Summary")
                end = md.find("##", start + 1)
                if end > 0:
                    diff_summary = md[start:end]
    except (OSError, UnicodeDecodeError):
        pass

    return {
        "metrics": metrics,
        "duration_str": _format_duration(duration_sec) if duration_sec else "N/A",
        "patch_files": patch_files,
        "retry_count": retry_count,
        "last_error_class": last_error_class,
        "model_name": next(iter(llm_breakdown), None),
        "files_changed": len(patch_files),
        "cost_usd": metrics.get("estimated_cost_jpy", 0.0) / _USD_JPY_RATE,
        "guardian_review": guardian_review,
        "diff_summary": diff_summary,
    }


@bp.route("/runs/<string:run_id>")
@require_auth
def run_logs(run_id: str):
    """
    特定のRunのログ一覧（4.5: Self-Healing メトリクス追加）
    GET /logs/runs/<run_id>?source=NPE&level=ERROR&page=1&per_page=50
    """
    user = get_current_user()
    run = Run.query.filter_by(run_id=run_id).first_or_404()
    user_project_or_404(user.id, run.project_id)

    display = _collect_run_display_data(run)

    source_filter = request.args.get("source")
    level_filter = request.args.get("level")
    per_page = int(request.args.get("per_page", 50))

    query = ExecutionLog.query.filter_by(run_id=run.id)
    if source_filter:
        query = query.filter(ExecutionLog.source == source_filter)
    if level_filter:
        query = query.filter(ExecutionLog.level == level_filter)

    logs_paginated, pagination = paginate_query(
        query, order_column=ExecutionLog.created_at, per_page=per_page
    )

    logs_data = [
        {
            "id": log.id,
            "source": log.source,
            "level": log.level,
            "message": log.message,
            "payload_json": log.payload_json,
            "payload_preview": str(log.payload_json)[:100] if log.payload_json else "",
            "created_at": log.created_at.isoformat(),
        }
        for log in logs_paginated.items
    ]

    if request.headers.get("Accept", "").startswith("application/json"):
        return jsonify({
            "run": {
                "run_id": run.run_id,
                "status": run.status,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            },
            "metrics": {
                "duration_str": display["duration_str"],
                "retry_count": display["retry_count"],
                "last_error_class": display["last_error_class"],
                "model": display["model_name"],
                "files_changed": display["files_changed"],
                "cost_usd": display["cost_usd"],
            },
            "logs": logs_data,
            "pagination": pagination,
        })

    return render_template(
        "logs/run_logs.html",
        run_id=run_id,
        run=run,
        project_id=run.project_id,
        status_badge_html=_render_run_status_badge(run.status),
        started_str=run.started_at.isoformat() if run.started_at else "N/A",
        finished_str=run.finished_at.isoformat() if run.finished_at else "N/A",
        model_name=display["model_name"],
        duration_str=display["duration_str"],
        retry_count=display["retry_count"],
        files_changed=display["files_changed"],
        cost_usd=display["cost_usd"],
        last_error_class=display["last_error_class"],
        guardian_review=display["guardian_review"],
        diff_summary=display["diff_summary"],
        logs_data=logs_data,
    )
