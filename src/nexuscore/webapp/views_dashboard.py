"""
NexusCore SaaS基盤 - ダッシュボードビュー

WebApp HTML UI view.

データ取得は FastAPI 経由ではなく、services / DB direct access を使用する。
本画面は FastAPI API migration の対象外（責務分離のため）。

既存の Orchestrator / NPE とは独立して動作する。
Gradio UI との統合もここで行う。
"""

from __future__ import annotations

import json
from typing import Any

from flask import Blueprint, jsonify, render_template, request

from nexuscore.webapp import db
from nexuscore.webapp.auth import get_current_user, require_auth
from nexuscore.webapp.models import ExecutionLog, PatchRecord, Project, Run
from nexuscore.webapp.views_projects import (
    _compute_run_duration,
    _format_duration,
    _render_run_status_badge,
)

bp = Blueprint("views_dashboard", __name__, url_prefix="/dashboard")


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
        project = Project.query.filter_by(id=project_id, owner_id=user.id).first_or_404()
        projects = [project]
    else:
        projects = Project.query.filter_by(owner_id=user.id).all()

    # 集計データ
    total_runs = Run.query.join(Project).filter(Project.owner_id == user.id).count()
    success_runs = (
        Run.query.join(Project).filter(Project.owner_id == user.id, Run.status == "SUCCESS").count()
    )
    failed_runs = (
        Run.query.join(Project).filter(Project.owner_id == user.id, Run.status == "FAILED").count()
    )

    # LLMごとの call_count, cost_sum（簡易版）
    # SQLiteではJSON操作がサポートされていないため、try-exceptで囲む
    from sqlalchemy import func

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
    except Exception:
        # SQLiteなどJSON操作が未サポートのDBでは空リストを返す
        llm_stats = []

    if request.headers.get("Accept", "").startswith("application/json"):
        return jsonify(
            {
                "projects": [{"id": p.id, "name": p.name} for p in projects],
                "stats": {
                    "total_runs": total_runs,
                    "success_runs": success_runs,
                    "failed_runs": failed_runs,
                    "success_rate": (success_runs / total_runs * 100) if total_runs > 0 else 0,
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
        total_runs=total_runs,
        success_runs=success_runs,
        failed_runs=failed_runs,
        success_rate=(success_runs / total_runs * 100) if total_runs > 0 else 0,
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
    from sqlalchemy import desc

    user = get_current_user()
    project = Project.query.filter_by(id=project_id, owner_id=user.id).first_or_404()

    # 統計情報を集計
    all_runs = Run.query.filter_by(project_id=project.id).all()
    total_runs = len(all_runs)
    success_runs = sum(1 for r in all_runs if r.status == "SUCCESS")
    failed_runs = sum(1 for r in all_runs if r.status == "FAILED")

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
    latest_run = Run.query.filter_by(project_id=project.id).order_by(desc(Run.created_at)).first()

    # 最新Runのメトリクス
    latest_run_metrics: dict[str, Any] | None = None
    if latest_run:
        # パッチ情報
        patches = PatchRecord.query.filter_by(run_id=latest_run.id).all()
        patch_files = {p.file_path for p in patches}

        # LLMログ
        logs = ExecutionLog.query.filter_by(run_id=latest_run.id, source="NPE").all()
        llm_call_count = len(logs)
        total_cost = 0.0

        for lg in logs:
            payload = lg.payload_json or {}
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except Exception:
                    payload = {}

            cost = (
                payload.get("estimated_cost")
                or payload.get("cost_jpy")
                or payload.get("usage", {}).get("cost_jpy", 0.0)
            )
            try:
                total_cost += float(cost)
            except Exception:
                pass

        duration_sec = _compute_run_duration(latest_run)

        latest_run_metrics = {
            "patch_count": len(patches),
            "affected_files": len(patch_files),
            "llm_call_count_total": llm_call_count,
            "estimated_cost_total": total_cost,
            "duration_sec": duration_sec,
        }

    # LLMコスト内訳
    llm_breakdown: dict[str, dict[str, Any]] = {}
    if latest_run:
        logs = ExecutionLog.query.filter_by(run_id=latest_run.id, source="NPE").all()
        for lg in logs:
            payload = lg.payload_json or {}
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except Exception:
                    payload = {}

            model = payload.get("model") or payload.get("model_name") or "unknown"
            usage = payload.get("usage", {})

            if model not in llm_breakdown:
                llm_breakdown[model] = {
                    "call_count": 0,
                    "token_prompt": 0,
                    "token_completion": 0,
                    "token_total": 0,
                    "cost_total": 0.0,
                }

            llm_breakdown[model]["call_count"] += 1
            llm_breakdown[model]["token_prompt"] += usage.get("prompt_tokens", 0)
            llm_breakdown[model]["token_completion"] += usage.get("completion_tokens", 0)
            llm_breakdown[model]["token_total"] += usage.get("prompt_tokens", 0) + usage.get(
                "completion_tokens", 0
            )

            cost = (
                payload.get("estimated_cost")
                or payload.get("cost_jpy")
                or usage.get("cost_jpy", 0.0)
            )
            try:
                llm_breakdown[model]["cost_total"] += float(cost)
            except Exception:
                pass

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
    project = Project.query.filter_by(id=project_id, owner_id=user.id).first_or_404()

    # Gradio アプリのURL（別ポートで起動している前提）
    gradio_url = f"http://localhost:7860/?project_id={project_id}"

    return render_template(
        "dashboard/gradio.html",
        project=project,
        gradio_url=gradio_url,
    )
