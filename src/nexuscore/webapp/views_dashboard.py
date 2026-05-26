from __future__ import annotations

import json
import os
from typing import Any

from flask import Blueprint, jsonify, render_template, request
from sqlalchemy import desc, func

from nexuscore.webapp import db
from nexuscore.webapp.auth import get_current_user, require_auth
from nexuscore.webapp.db_helpers import (
    project_latest_run,
    run_llm_cost,
    run_patch_files,
    user_project_or_404,
    user_projects_query,
    user_runs_stats,
)
from nexuscore.webapp.models import ExecutionLog, Run
from nexuscore.webapp.views_projects import (
    _compute_run_duration,
    _format_duration,
    _render_run_status_badge,
)

bp = Blueprint("views_dashboard", __name__, url_prefix="/dashboard")

_gradio_host = os.getenv("NEXUS_GRADIO_HOST", "http://localhost:7860")


@bp.route("/")
@require_auth
def dashboard():
    """
    PoC用ダッシュボード
    GET /dashboard/?project_id=123

    Data access: Direct DB access (no API call)
    FastAPI equivalent: N/A (internal UI only)
    """
    user = get_current_user()
    project_id = request.args.get("project_id", type=int)

    if project_id:
        project = user_project_or_404(user.id, project_id)
        projects = [project]
    else:
        projects = user_projects_query(user.id).all()

    # 集計データ — 1クエリで取得
    stats = user_runs_stats(user.id)

    # LLMごとの call_count, cost_sum（簡易版）
    try:
        llm_stats = (
            db.session.query(
                ExecutionLog.payload_json["model"].astext.label("model"),
                func.count(ExecutionLog.id).label("call_count"),
                func.sum(func.cast(ExecutionLog.payload_json["cost_est_usd"], db.Float)).label(
                    "cost_sum"
                ),
            )
            .filter(ExecutionLog.source == "NPE")
            .group_by(ExecutionLog.payload_json["model"].astext)
            .all()
        )
    except Exception:  # noqa: BLE001 — dashboard degrades gracefully on query failure
        llm_stats = []

    if request.headers.get("Accept", "").startswith("application/json"):
        return jsonify(
            {
                "projects": [{"id": p.id, "name": p.name} for p in projects],
                "stats": {
                    "total_runs": stats["total"],
                    "success_runs": stats["success"],
                    "failed_runs": stats["failed"],
                    "success_rate": (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0,
                },
                "llm_stats": [
                    {
                        "model": s.model,
                        "call_count": s.call_count,
                        "cost_sum": float(s.cost_sum or 0),
                    }
                    for s in llm_stats
                ],
            }
        )

    return render_template(
        "dashboard/index.html",
        user_login=user.github_login,
        total_runs=stats["total"],
        success_runs=stats["success"],
        failed_runs=stats["failed"],
        success_rate=(stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0,
        llm_stats=llm_stats,
        projects=projects,
    )


@bp.route("/projects/<int:project_id>")
@require_auth
def project_dashboard(project_id: int):
    """
    プロジェクトダッシュボード（カードレイアウト）
    GET /dashboard/projects/<project_id>

    Data access: Direct DB access (no API call)
    FastAPI equivalent: N/A (internal UI only)
    """
    user = get_current_user()
    project = user_project_or_404(user.id, project_id)

    # 統計情報を集計 — DB集計クエリでN+1解消
    total_runs = Run.query.filter_by(project_id=project.id).count()
    success_runs = Run.query.filter_by(project_id=project.id, status="SUCCESS").count()
    failed_runs = Run.query.filter_by(project_id=project.id, status="FAILED").count()

    # 過去30回の成功率
    recent_runs = (
        Run.query.filter_by(project_id=project.id).order_by(desc(Run.started_at)).limit(30).all()
    )
    recent_success = sum(1 for r in recent_runs if r.status == "SUCCESS")
    success_rate = (recent_success / len(recent_runs) * 100) if recent_runs else 0.0

    stats = {
        "total_runs": total_runs,
        "success_runs": success_runs,
        "failed_runs": failed_runs,
        "success_rate": success_rate / 100.0,  # 0.0-1.0 の範囲
    }

    # 最新Run
    latest_run = project_latest_run(project.id)

    # 最新Runのメトリクス
    latest_run_metrics: dict[str, Any] | None = None
    if latest_run:
        patch_files = run_patch_files(latest_run.id)
        llm_call_count, total_cost, _ = run_llm_cost(latest_run.id)
        duration_sec = _compute_run_duration(latest_run)

        latest_run_metrics = {
            "patch_count": len(patch_files) if isinstance(patch_files, set) else 0,
            "affected_files": len(patch_files),
            "llm_call_count_total": llm_call_count,
            "estimated_cost_total": total_cost,
            "duration_sec": duration_sec,
        }

    # LLMコスト内訳
    _, _, llm_breakdown = run_llm_cost(latest_run.id) if latest_run else (0, 0.0, {})

    # 直近のRun一覧（最大10件）
    recent_runs_list = (
        Run.query.filter_by(project_id=project.id).order_by(desc(Run.created_at)).limit(10).all()
    )

    # テンプレート用コンテキスト
    latest_status_badge = _render_run_status_badge(latest_run.status) if latest_run else ""
    latest_run_short = latest_run.run_id[:8] + "..." if latest_run else "-"
    duration_str = "-"
    if latest_run_metrics and latest_run_metrics.get("duration_sec") is not None:
        duration_str = _format_duration(latest_run_metrics["duration_sec"])

    return render_template(
        "dashboard/project.html",
        project=project,
        stats=stats,
        recent_runs=recent_runs_list,
        latest_run=latest_run,
        latest_run_metrics=latest_run_metrics,
        llm_breakdown=llm_breakdown,
        latest_status_badge=latest_status_badge,
        latest_run_short=latest_run_short,
        duration_str=duration_str,
    )


@bp.route("/gradio/<int:project_id>")
@require_auth
def gradio_dashboard(project_id: int):
    """
    Gradio UI iframe統合
    GET /dashboard/gradio/<project_id>

    Data access: Direct DB access (no API call)
    FastAPI equivalent: N/A (internal UI only)
    """
    user = get_current_user()
    project = user_project_or_404(user.id, project_id)

    # Gradio アプリのURL（別ポートで起動している前提）
    gradio_url = f"{_gradio_host}/?project_id={project_id}"

    return render_template(
        "dashboard/gradio.html",
        project=project,
        gradio_url=gradio_url,
    )
