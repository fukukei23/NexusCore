"""
NexusCore SaaS基盤 - プロジェクト管理ビュー

WebApp HTML UI view.

データ取得は FastAPI 経由ではなく、services / DB direct access を使用する。
本画面は FastAPI API migration の対象外（責務分離のため）。

既存の Orchestrator / NPE とは独立して動作する。
"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Sequence

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
from sqlalchemy import desc

from nexuscore.webapp import db
from nexuscore.webapp.auth import get_current_user, require_auth
from nexuscore.webapp.db_helpers import (
    project_latest_run,
    projects_with_latest_run,
    run_logs_payload,
    run_patch_files,
    user_project_or_404,
    user_projects_query,
)
from nexuscore.webapp.models import Project, Run

bp = Blueprint("views_projects", __name__, url_prefix="/projects")


# ============================================================================
# ヘルパー関数: Run 一覧テーブル描画
# ============================================================================


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

    # 各プロジェクトの最新Run情報とメトリクスを取得
    projects_data = []
    for project in projects:
        latest_run = project_latest_run(project.id)

        # 4.5: 最近30件の成功率を計算
        success_rate = _compute_recent_success_rate(project.id, limit=30)

        # 4.5: 最新Runのメトリクスを取得
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

    # JSON レスポンス
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

    # 直近のRun一覧（最大50件）— execution_logs を eager load して N+1 解消
    from nexuscore.webapp.db_helpers import project_runs_with_logs

    runs = project_runs_with_logs(project.id, limit=50)

    runs_data = []
    for run in runs:
        # 成功/失敗数の集計 — eager loaded execution_logs を使用
        success_count = sum(
            1 for lg in run.execution_logs
            if lg.level == "INFO" and lg.source == "ORCHESTRATOR"
        )
        failure_count = sum(1 for lg in run.execution_logs if lg.level == "ERROR")

        # 実行時間を計算
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

    # フラッシュメッセージの取得
    flash_messages = get_flashed_messages(with_categories=True)

    # テンプレート用のRunコンテキスト構築
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

    # POST処理
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

    フェーズ1: 同期実行（直接 Orchestrator を呼び出す）
    フェーズ2: Celery タスクとして Orchestrator を非同期実行する（コメントアウトで切り替え可能）
    """

    user = get_current_user()
    project = user_project_or_404(user.id, project_id)

    # リクエストボディからパラメータを取得
    data = request.get_json() or {}
    requirement = data.get("requirement", "")
    autonomy_level = data.get("autonomy_level", 1)
    fast_lane = data.get("fast_lane", False)

    if not requirement:
        return jsonify({"error": "requirement is required"}), 400

    # Run レコードを作成
    run_id = uuid.uuid4().hex
    run = Run(
        project_id=project.id,
        run_id=run_id,
        triggered_by=user.id,
        status="PENDING",
        autonomy_level=autonomy_level,
        requirement=requirement,  # requirement を保存
        started_at=None,
        finished_at=None,
    )
    db.session.add(run)
    db.session.commit()  # run.id を確定

    # 環境変数で同期/非同期を切り替え
    use_celery = os.getenv("NEXUS_USE_CELERY", "1") == "1"

    if use_celery:
        # ========================================================================
        # Celery 非同期実行（デフォルト）
        # ========================================================================
        from nexuscore.webapp.celery_app import run_orchestrator_task

        run_orchestrator_task.delay(run.id)

        # 必要なら Run に task_id を保存してもよい（進捗トラッキング用）
        # run.celery_task_id = async_result.id
        # db.session.commit()

        # ユーザーには「Run がキューに入った」ことを返す
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

        # HTML レスポンスの場合はプロジェクト詳細ページへリダイレクト
        flash(
            f"Run '{run.run_id[:8]}...' がキューに入りました。実行状態は上記の Run 一覧で確認できます。ログは Run ID をクリックしてください。",
            "info",
        )
        return redirect(url_for("views_projects.project_detail", project_id=project.id))
    else:
        # ========================================================================
        # 同期実行（デバッグ用）
        # ========================================================================
        from nexuscore.webapp.orchestrator_inline import run_orchestrator_inline

        try:
            run_orchestrator_inline(
                run=run,
                project=project,
                requirement=requirement,
                autonomy_level=autonomy_level,
                fast_lane=fast_lane,
            )

            # ユーザーには実行結果を返す
            if request.accept_mimetypes.best == "application/json":
                return jsonify(
                    {
                        "run_id": run.run_id,
                        "status": run.status,
                        "message": "Run completed." if run.status == "SUCCESS" else "Run failed.",
                    }
                ), (200 if run.status == "SUCCESS" else 500)

            # HTML レスポンスの場合はプロジェクト詳細ページへリダイレクト
            flash(
                f"Run '{run.run_id[:8]}...' が完了しました。ステータス: {run.status}",
                "success" if run.status == "SUCCESS" else "error",
            )
            return redirect(url_for("views_projects.project_detail", project_id=project.id))

        except Exception as exc:
            # エラーが発生した場合
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
