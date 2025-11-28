"""
NexusCore SaaS基盤 - ダッシュボードビュー

既存の Orchestrator / NPE とは独立して動作する。
Gradio UI との統合もここで行う。
"""
from __future__ import annotations

import json
from collections import defaultdict
from typing import Any, Dict, List, Optional

from flask import Blueprint, request, jsonify, render_template

from nexuscore.webapp import db
from nexuscore.webapp.models import Project, Run, ExecutionLog, PatchRecord
from nexuscore.webapp.auth import require_auth, get_current_user
from nexuscore.webapp.views_projects import (
    _render_run_status_badge,
    _format_duration,
    _compute_run_duration,
)

bp = Blueprint("views_dashboard", __name__, url_prefix="/dashboard")


@bp.route("/")
@require_auth
def dashboard():
    """
    PoC用ダッシュボード
    GET /dashboard/?project_id=123
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
    success_runs = Run.query.join(Project).filter(
        Project.owner_id == user.id, Run.status == "SUCCESS"
    ).count()
    failed_runs = Run.query.join(Project).filter(
        Project.owner_id == user.id, Run.status == "FAILED"
    ).count()

    # LLMごとの call_count, cost_sum（簡易版）
    from sqlalchemy import func
    llm_stats = (
        db.session.query(
            ExecutionLog.payload_json["model"].astext.label("model"),
            func.count(ExecutionLog.id).label("call_count"),
            func.sum(
                func.cast(ExecutionLog.payload_json["cost_est_usd"], db.Float)
            ).label("cost_sum"),
        )
        .filter(ExecutionLog.source == "NPE")
        .group_by(ExecutionLog.payload_json["model"].astext)
        .all()
    )

    if request.headers.get("Accept", "").startswith("application/json"):
        return jsonify({
            "projects": [{"id": p.id, "name": p.name} for p in projects],
            "stats": {
                "total_runs": total_runs,
                "success_runs": success_runs,
                "failed_runs": failed_runs,
                "success_rate": (success_runs / total_runs * 100) if total_runs > 0 else 0,
            },
            "llm_stats": [
                {"model": s.model, "call_count": s.call_count, "cost_sum": float(s.cost_sum or 0)}
                for s in llm_stats
            ],
        })

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>NexusCore - Dashboard</title></head>
    <body>
        <h1>NexusCore Dashboard</h1>
        <p>Logged in as: {user.github_login}</p>
        <hr>
        <h2>Statistics</h2>
        <ul>
            <li>Total Runs: {total_runs}</li>
            <li>Success: {success_runs}</li>
            <li>Failed: {failed_runs}</li>
            <li>Success Rate: {(success_runs / total_runs * 100) if total_runs > 0 else 0:.1f}%</li>
        </ul>
        <h2>LLM Usage</h2>
        <table border="1">
            <tr><th>Model</th><th>Calls</th><th>Cost (USD)</th></tr>
    """
    for s in llm_stats:
        html += f"<tr><td>{s.model}</td><td>{s.call_count}</td><td>${float(s.cost_sum or 0):.4f}</td></tr>"
    html += """
        </table>
        <hr>
        <h2>Projects</h2>
        <ul>
    """
    for p in projects:
        html += f'<li><a href="/projects/{p.id}">{p.name}</a></li>'
    html += """
        </ul>
        <hr>
        <a href="/projects/">Back to Projects</a>
    </body>
    </html>
    """
    return html


@bp.route("/projects/<int:project_id>")
@require_auth
def project_dashboard(project_id: int):
    """
    プロジェクトダッシュボード（カードレイアウト）
    GET /dashboard/projects/<project_id>
    """
    from sqlalchemy import desc, func

    user = get_current_user()
    project = Project.query.filter_by(id=project_id, owner_id=user.id).first_or_404()

    # 統計情報を集計
    all_runs = Run.query.filter_by(project_id=project.id).all()
    total_runs = len(all_runs)
    success_runs = sum(1 for r in all_runs if r.status == "SUCCESS")
    failed_runs = sum(1 for r in all_runs if r.status == "FAILED")

    # 過去30回の成功率
    recent_runs = Run.query.filter_by(project_id=project.id).order_by(desc(Run.started_at)).limit(30).all()
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
    latest_run_metrics: Optional[Dict[str, Any]] = None
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

            cost = payload.get("estimated_cost") or payload.get("cost_jpy") or payload.get("usage", {}).get("cost_jpy", 0.0)
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
    llm_breakdown: Dict[str, Dict[str, Any]] = {}
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
            llm_breakdown[model]["token_total"] += usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)

            cost = payload.get("estimated_cost") or payload.get("cost_jpy") or usage.get("cost_jpy", 0.0)
            try:
                llm_breakdown[model]["cost_total"] += float(cost)
            except Exception:
                pass

    # 直近のRun一覧（最大10件）
    recent_runs_list = Run.query.filter_by(project_id=project.id).order_by(desc(Run.created_at)).limit(10).all()

    # HTMLを生成
    html = render_project_dashboard_html(
        project=project,
        stats=stats,
        recent_runs=recent_runs_list,
        latest_run=latest_run,
        latest_run_metrics=latest_run_metrics,
        llm_breakdown=llm_breakdown,
    )

    return html


def _render_llm_cost_table(llm_breakdown: Dict[str, Dict[str, Any]]) -> str:
    """
    LLMコスト内訳テーブルをHTMLとして返す
    """
    rows = []
    for model, entry in llm_breakdown.items():
        rows.append(
            f"""
<tr>
  <td>{model}</td>
  <td>{entry.get('call_count', 0)}</td>
  <td>{entry.get('token_prompt', 0)}</td>
  <td>{entry.get('token_completion', 0)}</td>
  <td>{entry.get('token_total', 0)}</td>
  <td>{float(entry.get('cost_total', 0.0)):.2f}</td>
</tr>
"""
        )

    return f"""
<table class="simple">
  <thead>
    <tr>
      <th>Model</th>
      <th>Calls</th>
      <th>Prompt</th>
      <th>Completion</th>
      <th>Total</th>
      <th>Cost (JPY)</th>
    </tr>
  </thead>
  <tbody>
    {''.join(rows)}
  </tbody>
</table>
"""


def _render_recent_runs_list(project: Project, runs: List[Run]) -> str:
    """
    直近のRun一覧をHTMLとして返す
    """
    if not runs:
        return "<p>No runs yet.</p>"

    items = []
    for r in runs[:10]:
        badge = _render_run_status_badge(r.status or "")
        run_link = f"/logs/runs/{r.run_id}"
        started = r.started_at.isoformat(sep=" ", timespec="seconds") if r.started_at else "-"

        items.append(
            f"""
<li>
  <div>
    <a href="{run_link}">{r.run_id[:8]}...</a><br/>
    <span class="metric-label">{started}</span>
  </div>
  <div>{badge}</div>
</li>
"""
        )

    return f"<ul class='runs-list'>{''.join(items)}</ul>"


def render_project_dashboard_html(
    *,
    project: Project,
    stats: Dict[str, Any],
    recent_runs: List[Run],
    latest_run: Optional[Run],
    latest_run_metrics: Optional[Dict[str, Any]],
    llm_breakdown: Dict[str, Dict[str, Any]],
) -> str:
    """
    プロジェクトダッシュボードのHTMLを生成（カードレイアウト）
    """
    project_title = project.name
    success_rate_pct = stats.get("success_rate", 0.0) * 100

    # Statusバッジ
    latest_status_badge = _render_run_status_badge(latest_run.status) if latest_run else ""

    # Runの短縮ID
    latest_run_short = latest_run.run_id[:8] + "..." if latest_run else "-"

    # Duration表現
    duration_str = "-"
    if latest_run_metrics and latest_run_metrics.get("duration_sec") is not None:
        duration_str = _format_duration(latest_run_metrics["duration_sec"])

    # HTML全体
    html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>NexusCore Project Dashboard - {project_title}</title>
  <style>
    body {{
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 0;
      padding: 16px;
      background-color: #f3f4f6;
    }}
    h1 {{
      margin-bottom: 8px;
    }}
    .subtitle {{
      color: #6b7280;
      margin-bottom: 16px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 16px;
      margin-top: 16px;
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
    .metric-main {{
      font-size: 1.6rem;
      font-weight: 700;
    }}
    .metric-label {{
      font-size: 0.8rem;
      color: #6b7280;
    }}
    .metric-row {{
      display: flex;
      justify-content: space-between;
      margin-top: 4px;
      font-size: 0.9rem;
    }}
    .tag {{
      display: inline-flex;
      align-items: center;
      padding: 2px 8px;
      border-radius: 999px;
      background-color: #e5e7eb;
      font-size: 0.75rem;
    }}
    table.simple {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 8px;
      font-size: 0.85rem;
    }}
    table.simple th,
    table.simple td {{
      padding: 4px 6px;
      border-bottom: 1px solid #e5e7eb;
      text-align: left;
    }}
    table.simple th {{
      background-color: #f9fafb;
    }}
    .runs-list {{
      list-style: none;
      padding-left: 0;
      margin: 0;
      font-size: 0.85rem;
    }}
    .runs-list li {{
      padding: 4px 0;
      border-bottom: 1px solid #e5e7eb;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .runs-list a {{
      color: #2563eb;
      text-decoration: none;
    }}
    .runs-list a:hover {{
      text-decoration: underline;
    }}
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
  </style>
</head>
<body>
  <h1>Project: {project_title}</h1>
  <div class="subtitle">
    Runs: {stats.get("total_runs", 0)} / Success: {stats.get("success_runs", 0)} / Failed: {stats.get("failed_runs", 0)}
    &nbsp; | &nbsp; Success Rate (last 30): {success_rate_pct:.1f}%
  </div>
  <p>
    <a href="/projects/{project.id}">Back to Project Detail</a>
  </p>

  <div class="grid">
    <!-- Project Summary Card -->
    <div class="card">
      <h2>Project Summary</h2>
      <div class="metric-main">{success_rate_pct:.1f}%</div>
      <div class="metric-label">Success Rate (last 30 runs)</div>
      <div class="metric-row">
        <span>Total Runs</span>
        <span>{stats.get("total_runs", 0)}</span>
      </div>
      <div class="metric-row">
        <span>Success</span>
        <span>{stats.get("success_runs", 0)}</span>
      </div>
      <div class="metric-row">
        <span>Failed</span>
        <span>{stats.get("failed_runs", 0)}</span>
      </div>
    </div>

    <!-- Latest Run Summary Card -->
    <div class="card">
      <h2>Latest Run</h2>
      <div class="metric-row">
        <span>Run ID</span>
        <span>{latest_run_short}</span>
      </div>
      <div class="metric-row">
        <span>Status</span>
        <span>{latest_status_badge}</span>
      </div>
      <div class="metric-row">
        <span>Duration</span>
        <span>{duration_str}</span>
      </div>
      <div class="metric-row">
        <span>Patches</span>
        <span>{(latest_run_metrics or {}).get("patch_count", 0)} files: {(latest_run_metrics or {}).get("affected_files", 0)}</span>
      </div>
      <div class="metric-row">
        <span>LLM Calls</span>
        <span>{(latest_run_metrics or {}).get("llm_call_count_total", 0)}</span>
      </div>
      <div class="metric-row">
        <span>Estimated Cost</span>
        <span>~{((latest_run_metrics or {}).get("estimated_cost_total") or 0.0):.2f} JPY</span>
      </div>
    </div>

    <!-- LLM Cost Breakdown Card -->
    <div class="card">
      <h2>LLM Cost Breakdown</h2>
      {("<p>No LLM logs.</p>" if not llm_breakdown else _render_llm_cost_table(llm_breakdown))}
    </div>

    <!-- Recent Runs Card -->
    <div class="card">
      <h2>Recent Runs</h2>
      {_render_recent_runs_list(project, recent_runs)}
    </div>
  </div>
</body>
</html>
"""
    return html


@bp.route("/gradio/<int:project_id>")
@require_auth
def gradio_dashboard(project_id: int):
    """
    Gradio UI の iframe 統合
    GET /dashboard/gradio/<project_id>
    """
    user = get_current_user()
    project = Project.query.filter_by(id=project_id, owner_id=user.id).first_or_404()

    # Gradio アプリのURL（別ポートで起動している前提）
    gradio_url = f"http://localhost:7860/?project_id={project_id}"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>NexusCore - Gradio Dashboard: {project.name}</title></head>
    <body>
        <h1>Gradio Dashboard: {project.name}</h1>
        <iframe src="{gradio_url}" width="100%" height="800px"></iframe>
        <hr>
        <a href="/projects/">Back to Projects</a>
    </body>
    </html>
    """
    return html

