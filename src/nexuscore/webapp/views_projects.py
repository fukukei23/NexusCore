from __future__ import annotations

import json
import os
import uuid

from flask import (
    Blueprint,
    flash,
    get_flashed_messages,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from nexuscore.webapp import db
from nexuscore.webapp.auth import get_current_user, require_auth
from nexuscore.webapp.db_helpers import (
    project_latest_run,
    projects_with_latest_run,
    run_logs_payload,
    user_project_or_404,
    user_projects_query,
)
from nexuscore.webapp.models import Project, Run

from ._projects_helpers import (
    _compute_run_duration,
    _format_duration,
    _render_run_status_badge,
    render_run_table,
)

bp = Blueprint("views_projects", __name__, url_prefix="/projects")


@bp.route("/")
@require_auth
def list_projects():
    """
    プロジェクト一覧（4.5: カード形式表示）
    GET /projects/

    Data access: Direct DB access (no API call)
    FastAPI equivalent: GET /api/v1/projects (for external clients)
    """
    from nexuscore.integration.github_pr_comment import _compute_recent_success_rate

    user = get_current_user()
    projects = projects_with_latest_run(user.id)

    projects_data = []
    for project in projects:
        latest_run = project_latest_run(project.id)

        success_rate = _compute_recent_success_rate(project.id, limit=30)

        latest_run_metrics = None
        if latest_run:
            duration_sec = _compute_run_duration(latest_run)
            duration_str = _format_duration(duration_sec) if duration_sec else "N/A"

            retry_count, last_error_class = run_logs_payload(latest_run.id)

            latest_run_metrics = {
                "duration_str": duration_str,
                "retry_count": retry_count,
                "last_error_class": last_error_class,
            }

        projects_data.append(
            {
                "id": project.id,
                "name": project.name,
                "repo_url": project.repo_url,
                "local_path": project.local_path,
                "success_rate": success_rate,
                "latest_run": (
                    {
                        "run_id": latest_run.run_id if latest_run else None,
                        "status": latest_run.status if latest_run else None,
                        "started_at": (
                            latest_run.started_at.isoformat()
                            if latest_run and latest_run.started_at
                            else None
                        ),
                        "metrics": latest_run_metrics,
                    }
                    if latest_run
                    else None
                ),
            }
        )

    if request.headers.get("Accept", "").startswith("application/json"):
        return jsonify({"projects": projects_data})

    return render_template(
        "projects/list.html",
        user_login=user.github_login,
        projects_data=projects_data,
    )


@bp.route("/<int:project_id>")
@require_auth
def project_detail(project_id: int):
    """
    プロジェクト詳細＋直近のRun一覧
    GET /projects/<project_id>

    Data access: Direct DB access (no API call)
    FastAPI equivalent: GET /api/v1/projects/{id} (for external clients)
    """
    user = get_current_user()
    project = user_project_or_404(user.id, project_id)

    from nexuscore.webapp.db_helpers import project_runs_with_logs

    runs = project_runs_with_logs(project.id, limit=50)

    runs_data = []
    for run in runs:
        success_count = sum(
            1 for lg in run.execution_logs
            if lg.level == "INFO" and lg.source == "ORCHESTRATOR"
        )
        failure_count = sum(1 for lg in run.execution_logs if lg.level == "ERROR")

        duration_sec = _compute_run_duration(run)

        runs_data.append(
            {
                "id": run.id,
                "run_id": run.run_id,
                "status": run.status,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                "duration_sec": duration_sec,
                "success_count": success_count,
                "failure_count": failure_count,
            }
        )

    if request.headers.get("Accept", "").startswith("application/json"):
        return jsonify(
            {
                "project": {
                    "id": project.id,
                    "name": project.name,
                    "repo_url": project.repo_url,
                    "local_path": project.local_path,
                },
                "runs": runs_data,
            }
        )

    flash_messages = get_flashed_messages(with_categories=True)

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

    return render_template(
        "projects/detail.html",
        project=project,
        runs=runs_ctx,
        runs_count=len(runs),
        flash_messages=flash_messages,
        metrics_html="",
    )


@bp.route("/new", methods=["GET", "POST"])
@require_auth
def create_project():
    """
    新規プロジェクト作成
    GET /projects/new - フォーム表示
    POST /projects/new - プロジェクト作成

    Data access: Direct DB access (no API call)
    FastAPI equivalent: POST /api/v1/projects (for external clients)
    """
    if request.method == "GET":
        return render_template("projects/new.html")

    user = get_current_user()
    name = request.form.get("name", "").strip()
    repo_url = request.form.get("repo_url", "").strip() or None
    local_path = request.form.get("local_path", "").strip()

    if not name or not local_path:
        return jsonify({"error": "Name and local_path are required"}), 400

    project = Project(
        owner_id=user.id,
        name=name,
        repo_url=repo_url,
        local_path=local_path,
    )
    db.session.add(project)
    db.session.commit()

    return redirect(url_for("views_projects.project_detail", project_id=project.id))


@bp.route("/<int:project_id>/run", methods=["POST"])
@require_auth
def trigger_run(project_id: int):
    """
    プロジェクト実行トリガー（フェーズ1: 同期接続版 → フェーズ2: Celery 非同期版に切り替え可能）

    POST /projects/<project_id>/run

    Data access: Direct DB access + Orchestrator service call (no API call)
    FastAPI equivalent: POST /api/v1/projects/{id}/run (for external clients)
    """

    user = get_current_user()
    project = user_project_or_404(user.id, project_id)

    data = request.get_json() or {}
    requirement = data.get("requirement", "")
    autonomy_level = data.get("autonomy_level", 1)
    fast_lane = data.get("fast_lane", False)

    if not requirement:
        return jsonify({"error": "requirement is required"}), 400

    run_id = uuid.uuid4().hex
    run = Run(
        project_id=project.id,
        run_id=run_id,
        triggered_by=user.id,
        status="PENDING",
        autonomy_level=autonomy_level,
        requirement=requirement,
        started_at=None,
        finished_at=None,
    )
    db.session.add(run)
    db.session.commit()

    use_celery = os.getenv("NEXUS_USE_CELERY", "1") == "1"

    if use_celery:
        from nexuscore.webapp.celery_app import run_orchestrator_task

        run_orchestrator_task.delay(run.id)

        if request.accept_mimetypes.best == "application/json":
            return (
                jsonify(
                    {
                        "run_id": run.run_id,
                        "status": run.status,
                        "message": "Run queued. Execution will start shortly.",
                    }
                ),
                202,
            )

        flash(
            f"Run '{run.run_id[:8]}...' がキューに入りました。実行状態は上記の Run 一覧で確認できます。ログは Run ID をクリックしてください。",
            "info",
        )
        return redirect(url_for("views_projects.project_detail", project_id=project.id))
    else:
        from nexuscore.webapp.orchestrator_inline import run_orchestrator_inline

        try:
            run_orchestrator_inline(
                run=run,
                project=project,
                requirement=requirement,
                autonomy_level=autonomy_level,
                fast_lane=fast_lane,
            )

            if request.accept_mimetypes.best == "application/json":
                return jsonify(
                    {
                        "run_id": run.run_id,
                        "status": run.status,
                        "message": "Run completed." if run.status == "SUCCESS" else "Run failed.",
                    }
                ), (200 if run.status == "SUCCESS" else 500)

            flash(
                f"Run '{run.run_id[:8]}...' が完了しました。ステータス: {run.status}",
                "success" if run.status == "SUCCESS" else "error",
            )
            return redirect(url_for("views_projects.project_detail", project_id=project.id))

        except Exception as exc:
            if request.accept_mimetypes.best == "application/json":
                return (
                    jsonify(
                        {
                            "run_id": run.run_id,
                            "status": run.status,
                            "message": f"Run failed: {str(exc)}",
                        }
                    ),
                    500,
                )

            flash(f"Run '{run.run_id[:8]}...' が失敗しました: {str(exc)}", "error")
            return redirect(url_for("views_projects.project_detail", project_id=project.id))
