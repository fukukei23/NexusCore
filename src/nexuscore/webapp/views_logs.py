"""
NexusCore SaaS基盤 - ログビューア

WebApp HTML UI view.

データ取得は FastAPI 経由ではなく、services / DB direct access を使用する。
本画面は FastAPI API migration の対象外（責務分離のため）。

既存の Orchestrator / NPE とは独立して動作する。
"""

from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request
from sqlalchemy import desc

from nexuscore.webapp.auth import get_current_user, require_auth
from nexuscore.webapp.models import ExecutionLog, Project, Run

bp = Blueprint("views_logs", __name__, url_prefix="/logs")


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
    project = Project.query.filter_by(id=project_id, owner_id=user.id).first_or_404()

    # クエリパラメータ
    source_filter = request.args.get("source")
    level_filter = request.args.get("level")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))

    # クエリ構築
    query = ExecutionLog.query.join(Run).filter(Run.project_id == project.id)

    if source_filter:
        query = query.filter(ExecutionLog.source == source_filter)
    if level_filter:
        query = query.filter(ExecutionLog.level == level_filter)

    # ページング
    logs = query.order_by(desc(ExecutionLog.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )

    logs_data = []
    for log in logs.items:
        logs_data.append(
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
        )

    if request.headers.get("Accept", "").startswith("application/json"):
        return jsonify(
            {
                "logs": logs_data,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": logs.total,
                    "pages": logs.pages,
                },
            }
        )

    return render_template(
        "logs/project_logs.html",
        project=project,
        logs_data=logs_data,
        source_filter=source_filter,
        level_filter=level_filter,
    )


@bp.route("/runs/<string:run_id>")
@require_auth
def run_logs(run_id: str):
    """
    特定のRunのログ一覧（4.5: Self-Healing メトリクス追加）
    GET /logs/runs/<run_id>?source=NPE&level=ERROR&page=1&per_page=50

    Data access: Direct DB access (no API call)
    FastAPI equivalent: GET /api/v1/runs/{id} (for external clients, but different data structure)
    """
    import json

    from nexuscore.integration.github_pr_comment import _collect_run_metrics
    from nexuscore.integration.run_report_generator import get_markdown_report_path
    from nexuscore.webapp.views_projects import (
        _compute_run_duration,
        _format_duration,
        _render_run_status_badge,
    )

    user = get_current_user()
    run = Run.query.filter_by(run_id=run_id).first_or_404()

    # 権限チェック（プロジェクトのオーナーか）
    project = Project.query.filter_by(id=run.project_id, owner_id=user.id).first_or_404()

    # 4.5: Self-Healing メトリクスを収集
    metrics = _collect_run_metrics(run)
    duration_sec = _compute_run_duration(run)
    duration_str = _format_duration(duration_sec) if duration_sec else "N/A"

    # 4.4: details から retry_count と last_error_class を取得
    from nexuscore.webapp.models import PatchRecord

    patches = PatchRecord.query.filter_by(run_id=run.id).all()
    patch_files = {p.file_path for p in patches}

    # ExecutionLog から details を取得
    logs = ExecutionLog.query.filter_by(run_id=run.id).all()
    retry_count = 0
    last_error_class = None
    model_name = None
    files_changed = len(patch_files)
    cost_usd = metrics.get("estimated_cost_jpy", 0.0) / 150.0  # JPY -> USD 簡易換算

    for log in logs:
        payload = log.payload_json or {}
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}
        if payload.get("retry_count"):
            retry_count = max(retry_count, payload.get("retry_count", 0))
        if payload.get("last_error_class"):
            last_error_class = payload.get("last_error_class")
        if payload.get("model") and not model_name:
            model_name = payload.get("model")

    # Guardian Review 情報を取得（ExecutionLog から）
    guardian_review = None
    for log in logs:
        payload = log.payload_json or {}
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}
        if payload.get("guardian_review"):
            guardian_review = payload.get("guardian_review")
            break

    # Diff Summary を取得（Run レポートから）
    diff_summary = ""
    try:
        report_path = get_markdown_report_path(run_id)
        if report_path.exists():
            markdown_content = report_path.read_text(encoding="utf-8")
            # Diff Summary セクションを抽出（簡易版）
            if "## AI Diff Summary" in markdown_content:
                diff_start = markdown_content.find("## AI Diff Summary")
                diff_end = markdown_content.find("##", diff_start + 1)
                if diff_end > 0:
                    diff_summary = markdown_content[diff_start:diff_end]
    except Exception:
        pass

    # クエリパラメータ
    source_filter = request.args.get("source")
    level_filter = request.args.get("level")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))

    # クエリ構築
    query = ExecutionLog.query.filter_by(run_id=run.id)

    if source_filter:
        query = query.filter(ExecutionLog.source == source_filter)
    if level_filter:
        query = query.filter(ExecutionLog.level == level_filter)

    # ページング
    logs_paginated = query.order_by(desc(ExecutionLog.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )

    logs_data = []
    for log in logs_paginated.items:
        logs_data.append(
            {
                "id": log.id,
                "source": log.source,
                "level": log.level,
                "message": log.message,
                "payload_json": log.payload_json,
                "payload_preview": str(log.payload_json)[:100] if log.payload_json else "",
                "created_at": log.created_at.isoformat(),
            }
        )

    if request.headers.get("Accept", "").startswith("application/json"):
        return jsonify(
            {
                "run": {
                    "run_id": run.run_id,
                    "status": run.status,
                    "started_at": run.started_at.isoformat() if run.started_at else None,
                    "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                },
                "metrics": {
                    "duration_str": duration_str,
                    "retry_count": retry_count,
                    "last_error_class": last_error_class,
                    "model": model_name,
                    "files_changed": files_changed,
                    "cost_usd": cost_usd,
                },
                "logs": logs_data,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": logs_paginated.total,
                    "pages": logs_paginated.pages,
                },
            }
        )

    return render_template(
        "logs/run_logs.html",
        run_id=run_id,
        run=run,
        project_id=project.id,
        status_badge_html=_render_run_status_badge(run.status),
        started_str=run.started_at.isoformat() if run.started_at else "N/A",
        finished_str=run.finished_at.isoformat() if run.finished_at else "N/A",
        model_name=model_name,
        duration_str=duration_str,
        retry_count=retry_count,
        files_changed=files_changed,
        cost_usd=cost_usd,
        last_error_class=last_error_class,
        guardian_review=guardian_review,
        diff_summary=diff_summary,
        logs_data=logs_data,
    )
