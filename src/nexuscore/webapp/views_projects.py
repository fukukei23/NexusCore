"""
NexusCore SaaS基盤 - プロジェクト管理ビュー

WebApp HTML UI view.

データ取得は FastAPI 経由ではなく、services / DB direct access を使用する。
本画面は FastAPI API migration の対象外（責務分離のため）。

既存の Orchestrator / NPE とは独立して動作する。
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Sequence, Dict
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, flash, get_flashed_messages
from sqlalchemy import desc

from nexuscore.webapp import db
from nexuscore.webapp.models import Project, Run, User
from nexuscore.webapp.auth import require_auth, get_current_user

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
    """
    プロジェクト詳細画面などで使う共通 Run 一覧テーブルをHTMLとして返す。
    """
    rows_html: list[str] = []

    for r in runs:
        status_badge = _render_run_status_badge(r.status or "")
        duration_sec = _compute_run_duration(r)
        duration_str = _format_duration(duration_sec)
        run_logs_url = f"/logs/runs/{r.run_id}"
        started_at = r.started_at.isoformat(sep=" ", timespec="seconds") if r.started_at else "-"
        finished_at = r.finished_at.isoformat(sep=" ", timespec="seconds") if r.finished_at else "-"

        rows_html.append(
            f"""
<tr>
  <td><a href="{run_logs_url}">{r.run_id[:8]}...</a></td>
  <td>{status_badge}</td>
  <td>{duration_str}</td>
  <td>{started_at}</td>
  <td>{finished_at}</td>
</tr>
"""
        )

    table_html = f"""
<style>
.status-badge {{
  display: inline-flex;
  align-items: center;
  padding: 2px 6px;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 600;
  color: #fff;
}}
.status-pending {{
  background-color: #7f8c8d;
}}
.status-running {{
  background-color: #2980b9;
  animation: pulse 1.2s infinite;
}}
.status-success {{
  background-color: #27ae60;
}}
.status-failed {{
  background-color: #c0392b;
}}
@keyframes pulse {{
  0% {{ opacity: 0.7; }}
  50% {{ opacity: 1; }}
  100% {{ opacity: 0.7; }}
}}
.run-table {{
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;
}}
.run-table th,
.run-table td {{
  padding: 4px 8px;
  border-bottom: 1px solid #eee;
  font-size: 0.9rem;
}}
.run-table th {{
  text-align: left;
  background-color: #f8f9fa;
}}
</style>
<table class="run-table">
  <thead>
    <tr>
      <th>Run ID</th>
      <th>Status</th>
      <th>Duration</th>
      <th>Started</th>
      <th>Finished</th>
    </tr>
  </thead>
  <tbody>
    {''.join(rows_html)}
  </tbody>
</table>
"""
    return table_html


@bp.route("/")
@require_auth
def list_projects():
    """
    プロジェクト一覧（4.5: カード形式表示）
    GET /projects/

    Data access: Direct DB access (no API call)
    FastAPI equivalent: GET /api/v1/projects (for external clients)
    """
    from sqlalchemy import desc, func
    from nexuscore.integration.github_pr_comment import _compute_recent_success_rate

    user = get_current_user()
    projects = Project.query.filter_by(owner_id=user.id).order_by(desc(Project.updated_at)).all()

    # 各プロジェクトの最新Run情報とメトリクスを取得
    projects_data = []
    for project in projects:
        latest_run = Run.query.filter_by(project_id=project.id).order_by(desc(Run.created_at)).first()

        # 4.5: 最近30件の成功率を計算
        success_rate = _compute_recent_success_rate(project.id, limit=30)

        # 4.5: 最新Runのメトリクスを取得
        latest_run_metrics = None
        if latest_run:
            duration_sec = _compute_run_duration(latest_run)
            duration_str = _format_duration(duration_sec) if duration_sec else "N/A"

            # 4.4: details から retry_count と last_error_class を取得
            from nexuscore.webapp.models import ExecutionLog
            logs = ExecutionLog.query.filter_by(run_id=latest_run.id).all()
            retry_count = 0
            last_error_class = None
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

            latest_run_metrics = {
                "duration_str": duration_str,
                "retry_count": retry_count,
                "last_error_class": last_error_class,
            }

        projects_data.append({
            "id": project.id,
            "name": project.name,
            "repo_url": project.repo_url,
            "local_path": project.local_path,
            "success_rate": success_rate,
            "latest_run": {
                "run_id": latest_run.run_id if latest_run else None,
                "status": latest_run.status if latest_run else None,
                "started_at": latest_run.started_at.isoformat() if latest_run and latest_run.started_at else None,
                "metrics": latest_run_metrics,
            } if latest_run else None,
        })

    # JSON レスポンス
    if request.headers.get("Accept", "").startswith("application/json"):
        return jsonify({"projects": projects_data})

    # 4.5: カード形式のHTMLレスポンス
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>NexusCore - Projects</title>
        <style>
            body {{
                font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                margin: 0;
                padding: 16px;
                background-color: #f3f4f6;
            }}
            .header {{
                margin-bottom: 24px;
            }}
            .header h1 {{
                margin-bottom: 8px;
            }}
            .header .subtitle {{
                color: #6b7280;
            }}
            .projects-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
                gap: 16px;
            }}
            .project-card {{
                background-color: #ffffff;
                border-radius: 12px;
                padding: 16px;
                box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
            }}
            .project-card h3 {{
                margin-top: 0;
                margin-bottom: 8px;
            }}
            .project-card .repo-url {{
                color: #6b7280;
                font-size: 0.9rem;
                margin-bottom: 12px;
            }}
            .metrics-row {{
                display: flex;
                justify-content: space-between;
                margin-top: 8px;
                font-size: 0.85rem;
            }}
            .metric-label {{
                color: #6b7280;
            }}
            .metric-value {{
                font-weight: 600;
            }}
            .status-badge {{
                display: inline-flex;
                align-items: center;
                padding: 2px 6px;
                border-radius: 999px;
                font-size: 0.75rem;
                font-weight: 600;
                color: #fff;
            }}
            .status-success {{ background-color: #27ae60; }}
            .status-failed {{ background-color: #c0392b; }}
            .status-running {{ background-color: #2980b9; }}
            .status-pending {{ background-color: #7f8c8d; }}
            .btn-link {{
                display: inline-block;
                margin-top: 12px;
                padding: 6px 12px;
                border-radius: 6px;
                background-color: #2563eb;
                color: #ffffff;
                text-decoration: none;
                font-size: 0.85rem;
            }}
            .btn-link:hover {{
                background-color: #1d4ed8;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Projects</h1>
            <div class="subtitle">Logged in as: {user.github_login} | <a href="{url_for('auth.logout')}">Logout</a></div>
        </div>
        <div class="projects-grid">
    """
    for p in projects_data:
        latest_status_badge = ""
        if p['latest_run']:
            latest_status_badge = _render_run_status_badge(p['latest_run']['status'])

        success_rate_pct = p['success_rate'] * 100 if p['success_rate'] else 0.0

        # 最新Runのメトリクス
        exec_time = "N/A"
        retry_count = "-"
        last_error = "-"
        if p['latest_run'] and p['latest_run'].get('metrics'):
            metrics = p['latest_run']['metrics']
            exec_time = metrics.get('duration_str', 'N/A')
            retry_count = str(metrics.get('retry_count', 0))
            last_error = metrics.get('last_error_class', '-') or '-'

        html += f"""
            <div class="project-card">
                <h3><a href="{url_for('views_projects.project_detail', project_id=p['id'])}">{p['name']}</a></h3>
                <div class="repo-url">{p['repo_url'] or 'No repo URL'}</div>
                <div class="metrics-row">
                    <span class="metric-label">Success Rate (30 runs):</span>
                    <span class="metric-value">{success_rate_pct:.1f}%</span>
                </div>
                <div class="metrics-row">
                    <span class="metric-label">Latest Status:</span>
                    <span>{latest_status_badge if latest_status_badge else '-'}</span>
                </div>
                <div class="metrics-row">
                    <span class="metric-label">Exec Time:</span>
                    <span class="metric-value">{exec_time}</span>
                </div>
                <div class="metrics-row">
                    <span class="metric-label">Retry:</span>
                    <span class="metric-value">{retry_count}</span>
                </div>
                {f'<div class="metrics-row"><span class="metric-label">Last Error:</span><span class="metric-value">{last_error}</span></div>' if last_error != '-' else ''}
                <a href="{url_for('views_projects.project_detail', project_id=p['id'])}" class="btn-link">View Details</a>
            </div>
        """
    html += """
        </div>
        <hr>
        <a href="/projects/new">Create New Project</a>
    </body>
    </html>
    """
    return html


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
    project = Project.query.filter_by(id=project_id, owner_id=user.id).first_or_404()

    # 直近のRun一覧（最大50件）
    runs = Run.query.filter_by(project_id=project.id).order_by(desc(Run.created_at)).limit(50).all()

    runs_data = []
    for run in runs:
        # 成功/失敗数の集計（簡易版）
        from nexuscore.webapp.models import ExecutionLog
        success_count = ExecutionLog.query.filter_by(
            run_id=run.id, level="INFO", source="ORCHESTRATOR"
        ).count()
        failure_count = ExecutionLog.query.filter_by(
            run_id=run.id, level="ERROR"
        ).count()

        # 実行時間を計算
        duration_sec = _compute_run_duration(run)

        runs_data.append({
            "id": run.id,
            "run_id": run.run_id,
            "status": run.status,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "duration_sec": duration_sec,
            "success_count": success_count,
            "failure_count": failure_count,
        })

    if request.headers.get("Accept", "").startswith("application/json"):
        return jsonify({
            "project": {
                "id": project.id,
                "name": project.name,
                "repo_url": project.repo_url,
                "local_path": project.local_path,
            },
            "runs": runs_data,
        })

    # フラッシュメッセージの取得
    flash_messages = get_flashed_messages(with_categories=True)

    # ダッシュボードへのリンク
    dashboard_url = f"/dashboard/projects/{project.id}"

    # 4.5: メトリクス可視化セクション
    metrics_html = ""
    if recent_runs:
        success_rate_pct = recent_success_rate * 100
        avg_exec_time_str = _format_duration(avg_exec_time) if avg_exec_time else "N/A"
        metrics_html = f"""
        <div style="background-color: #f9fafb; padding: 16px; border-radius: 8px; margin-bottom: 24px;">
            <h2>Metrics (Last 30 Runs)</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px;">
                <div>
                    <div style="font-size: 0.85rem; color: #6b7280;">Success Rate</div>
                    <div style="font-size: 1.5rem; font-weight: 700;">{success_rate_pct:.1f}%</div>
                </div>
                <div>
                    <div style="font-size: 0.85rem; color: #6b7280;">Avg Exec Time</div>
                    <div style="font-size: 1.5rem; font-weight: 700;">{avg_exec_time_str}</div>
                </div>
                <div>
                    <div style="font-size: 0.85rem; color: #6b7280;">Avg Retry</div>
                    <div style="font-size: 1.5rem; font-weight: 700;">{avg_retry:.1f}</div>
                </div>
                {f'''<div>
                    <div style="font-size: 0.85rem; color: #6b7280;">Most Common Error</div>
                    <div style="font-size: 1.5rem; font-weight: 700;">{most_common_error}</div>
                </div>''' if most_common_error else ''}
            </div>
        </div>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>NexusCore - {project.name}</title>
        <style>
            body {{
                font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                margin: 0;
                padding: 16px;
                background-color: #f3f4f6;
            }}
            .flash-message {{
                padding: 10px;
                margin: 10px 0;
                border-radius: 4px;
                background-color: #e7f3ff;
                border-left: 4px solid #0066cc;
            }}
            .btn-link {{
                display: inline-block;
                padding: 4px 10px;
                border-radius: 999px;
                background-color: #2563eb;
                color: #ffffff;
                font-size: 0.85rem;
                text-decoration: none;
            }}
            .btn-link:hover {{
                background-color: #1d4ed8;
            }}
        </style>
    </head>
    <body>
        <h1>{project.name}</h1>
        <p>Repo: {project.repo_url or 'N/A'}</p>
        <p>Local Path: {project.local_path}</p>
        <p>
            <a href="{dashboard_url}" class="btn-link">Open Project Dashboard</a>
        </p>
        <hr>

        {metrics_html}

    """

    # フラッシュメッセージの表示
    if flash_messages:
        for category, message in flash_messages:
            html += f'<div class="flash-message">{message}</div>'

    # Run 一覧テーブルをヘルパー関数で生成
    html += f"""
        <h2>Recent Runs ({len(runs)})</h2>
        {render_run_table(project, runs)}
        <hr>
        <a href="/projects/">Back to Projects</a>
    </body>
    </html>
    """
    return html


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
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>NexusCore - New Project</title></head>
        <body>
            <h1>Create New Project</h1>
            <form method="POST">
                <p>Name: <input type="text" name="name" required></p>
                <p>Repo URL: <input type="text" name="repo_url" placeholder="https://github.com/user/repo"></p>
                <p>Local Path: <input type="text" name="local_path" required placeholder="/path/to/project"></p>
                <p><button type="submit">Create</button></p>
            </form>
            <a href="/projects/">Cancel</a>
        </body>
        </html>
        """
        return html

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
    from datetime import datetime

    user = get_current_user()
    project = Project.query.filter_by(id=project_id, owner_id=user.id).first_or_404()

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

        async_result = run_orchestrator_task.delay(run.id)

        # 必要なら Run に task_id を保存してもよい（進捗トラッキング用）
        # run.celery_task_id = async_result.id
        # db.session.commit()

        # ユーザーには「Run がキューに入った」ことを返す
        if request.accept_mimetypes.best == "application/json":
            return jsonify({
                "run_id": run.run_id,
                "status": run.status,
                "message": "Run queued. Execution will start shortly.",
            }), 202

        # HTML レスポンスの場合はプロジェクト詳細ページへリダイレクト
        flash(f"Run '{run.run_id[:8]}...' がキューに入りました。実行状態は上記の Run 一覧で確認できます。ログは Run ID をクリックしてください。", "info")
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
                return jsonify({
                    "run_id": run.run_id,
                    "status": run.status,
                    "message": "Run completed." if run.status == "SUCCESS" else "Run failed.",
                }), 200 if run.status == "SUCCESS" else 500

            # HTML レスポンスの場合はプロジェクト詳細ページへリダイレクト
            flash(f"Run '{run.run_id[:8]}...' が完了しました。ステータス: {run.status}", "success" if run.status == "SUCCESS" else "error")
            return redirect(url_for("views_projects.project_detail", project_id=project.id))

        except Exception as exc:
            # エラーが発生した場合
            if request.accept_mimetypes.best == "application/json":
                return jsonify({
                    "run_id": run.run_id,
                    "status": run.status,
                    "message": f"Run failed: {str(exc)}",
                }), 500

            flash(f"Run '{run.run_id[:8]}...' が失敗しました: {str(exc)}", "error")
            return redirect(url_for("views_projects.project_detail", project_id=project.id))

