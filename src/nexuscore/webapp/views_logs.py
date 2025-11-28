"""
NexusCore SaaS基盤 - ログビューア

既存の Orchestrator / NPE とは独立して動作する。
"""
from __future__ import annotations

from flask import Blueprint, request, jsonify, render_template
from sqlalchemy import desc, and_

from nexuscore.webapp.models import ExecutionLog, Run, Project
from nexuscore.webapp.auth import require_auth, get_current_user

bp = Blueprint("views_logs", __name__, url_prefix="/logs")


@bp.route("/projects/<int:project_id>")
@require_auth
def project_logs(project_id: int):
    """
    プロジェクト単位のログ一覧
    GET /logs/projects/<project_id>?source=NPE&level=ERROR&page=1&per_page=50
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
        logs_data.append({
            "id": log.id,
            "run_id": log.run_id,
            "source": log.source,
            "level": log.level,
            "message": log.message,
            "payload_json": log.payload_json,
            "created_at": log.created_at.isoformat(),
        })

    if request.headers.get("Accept", "").startswith("application/json"):
        return jsonify({
            "logs": logs_data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": logs.total,
                "pages": logs.pages,
            },
        })

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>NexusCore - Logs: {project.name}</title></head>
    <body>
        <h1>Logs: {project.name}</h1>
        <p>Filters: source={source_filter or 'all'}, level={level_filter or 'all'}</p>
        <hr>
        <table border="1">
            <tr>
                <th>Time</th>
                <th>Source</th>
                <th>Level</th>
                <th>Message</th>
                <th>Details</th>
            </tr>
    """
    for log in logs_data:
        payload_preview = str(log["payload_json"])[:100] if log["payload_json"] else ""
        html += f"""
            <tr>
                <td>{log['created_at']}</td>
                <td>{log['source']}</td>
                <td>{log['level']}</td>
                <td>{log['message'][:100]}</td>
                <td><details><summary>JSON</summary><pre>{payload_preview}</pre></details></td>
            </tr>
        """
    html += """
        </table>
        <hr>
        <a href="/projects/">Back to Projects</a>
    </body>
    </html>
    """
    return html


@bp.route("/runs/<string:run_id>")
@require_auth
def run_logs(run_id: str):
    """
    特定のRunのログ一覧（4.5: Self-Healing メトリクス追加）
    GET /logs/runs/<run_id>?source=NPE&level=ERROR&page=1&per_page=50
    """
    import json
    from nexuscore.webapp.views_projects import _format_duration, _compute_run_duration, _render_run_status_badge
    from nexuscore.integration.github_pr_comment import _collect_run_metrics, load_run_markdown
    from nexuscore.integration.run_report_generator import get_markdown_report_path

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
        logs_data.append({
            "id": log.id,
            "source": log.source,
            "level": log.level,
            "message": log.message,
            "payload_json": log.payload_json,
            "created_at": log.created_at.isoformat(),
        })

    if request.headers.get("Accept", "").startswith("application/json"):
        return jsonify({
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
        })

    # 4.5: Self-Healing メトリクスを含むHTMLレスポンス
    status_badge = _render_run_status_badge(run.status)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>NexusCore - Run: {run_id[:8]}...</title>
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
            .metrics-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 16px;
                margin-bottom: 24px;
            }}
            .card {{
                background-color: #ffffff;
                border-radius: 12px;
                padding: 16px;
                box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
            }}
            .card h2 {{
                font-size: 1rem;
                margin-top: 0;
                margin-bottom: 8px;
            }}
            .metric-row {{
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
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 16px;
            }}
            table th, table td {{
                padding: 8px;
                border-bottom: 1px solid #e5e7eb;
                text-align: left;
            }}
            table th {{
                background-color: #f9fafb;
            }}
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
            <h1>Run: {run_id[:8]}...</h1>
            <p>Status: {status_badge}</p>
            <p>Started: {run.started_at.isoformat() if run.started_at else 'N/A'}</p>
            <p>Finished: {run.finished_at.isoformat() if run.finished_at else 'N/A'}</p>
        </div>

        <!-- 4.5: Self-Healing Metrics -->
        <div class="metrics-grid">
            <div class="card">
                <h2>Self-Healing Metrics</h2>
                <div class="metric-row">
                    <span class="metric-label">Model:</span>
                    <span class="metric-value">{model_name or 'N/A'}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Exec Time:</span>
                    <span class="metric-value">{duration_str}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Retry Count:</span>
                    <span class="metric-value">{retry_count}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Files Changed:</span>
                    <span class="metric-value">{files_changed}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Cost:</span>
                    <span class="metric-value">${cost_usd:.4f} USD</span>
                </div>
                {f'<div class="metric-row"><span class="metric-label">Last Error:</span><span class="metric-value">{last_error_class}</span></div>' if last_error_class else ''}
            </div>

            {f'''<div class="card">
                <h2>Guardian Review</h2>
                <p><strong>Decision:</strong> {guardian_review.get('decision', 'N/A')}</p>
                <p><strong>Reason:</strong> {guardian_review.get('reason', 'N/A')[:200]}</p>
            </div>''' if guardian_review else ''}

            {f'''<div class="card">
                <h2>AI Diff Summary</h2>
                <pre style="white-space: pre-wrap; font-size: 0.85rem;">{diff_summary[:500]}</pre>
            </div>''' if diff_summary else ''}
        </div>

        <!-- Observability Links -->
        <div class="card">
            <h2>Observability</h2>
            <p>
                <a href="/logs/runs/{run_id}" class="btn-link">ExecutionLog 画面</a>
                <a href="/projects/{project.id}" class="btn-link">Project Detail</a>
            </p>
            <p>
                <a href="/dashboard/projects/{project.id}" class="btn-link">Project Dashboard</a>
            </p>
        </div>

        <hr>
        <h2>Execution Logs</h2>
        <table>
            <tr>
                <th>Time</th>
                <th>Source</th>
                <th>Level</th>
                <th>Message</th>
                <th>Details</th>
            </tr>
    """
    for log in logs_data:
        payload_preview = str(log["payload_json"])[:100] if log["payload_json"] else ""
        html += f"""
            <tr>
                <td>{log['created_at']}</td>
                <td>{log['source']}</td>
                <td>{log['level']}</td>
                <td>{log['message'][:100]}</td>
                <td><details><summary>JSON</summary><pre>{payload_preview}</pre></details></td>
            </tr>
        """
    html += """
        </table>
        <hr>
        <a href="/projects/">Back to Projects</a>
    </body>
    </html>
    """
    return html

