"""
README バッジ向けのメトリクス API

shields.io などで使用できる JSON エンドポイントを提供する。
"""

from __future__ import annotations

from flask import Blueprint, jsonify
from sqlalchemy import desc

from nexuscore.webapp.models import Project, Run
from nexuscore.webapp.auth import require_auth, get_current_user

bp = Blueprint("api_badges", __name__, url_prefix="/api")


@bp.route("/projects/<int:project_id>/badge/success_rate")
def project_success_rate_badge(project_id: int):
    """
    プロジェクトの成功率バッジ用 JSON を返す（shields.io endpoint 互換）

    GET /api/projects/<project_id>/badge/success_rate
    """
    project = Project.query.filter_by(id=project_id).first_or_404()

    # 過去30回のRunを取得
    runs = Run.query.filter_by(project_id=project.id).order_by(desc(Run.started_at)).limit(30).all()

    if not runs:
        success_rate = 0.0
    else:
        success_count = sum(1 for r in runs if r.status == "SUCCESS")
        success_rate = success_count / len(runs) * 100.0

    # カラーを決定
    if success_rate >= 90:
        color = "brightgreen"
    elif success_rate >= 70:
        color = "green"
    elif success_rate >= 50:
        color = "yellow"
    else:
        color = "red"

    return jsonify({
        "schemaVersion": 1,
        "label": "self-healing",
        "message": f"{success_rate:.1f}% success",
        "color": color,
    })


@bp.route("/projects/<int:project_id>/badge/last_run")
def project_last_run_badge(project_id: int):
    """
    プロジェクトの最新Runステータスバッジ用 JSON を返す（shields.io endpoint 互換）

    GET /api/projects/<project_id>/badge/last_run
    """
    project = Project.query.filter_by(id=project_id).first_or_404()

    # 最新のRunを取得
    latest_run = Run.query.filter_by(project_id=project.id).order_by(desc(Run.started_at)).first()

    if not latest_run:
        return jsonify({
            "schemaVersion": 1,
            "label": "self-healing",
            "message": "last: -",
            "color": "lightgrey",
        })

    status = (latest_run.status or "UNKNOWN").upper()

    # ステータスに応じたカラーとメッセージ
    if status == "SUCCESS":
        color = "brightgreen"
        message = "last: SUCCESS"
    elif status == "FAILED":
        color = "red"
        message = "last: FAILED"
    elif status == "RUNNING":
        color = "blue"
        message = "last: RUNNING"
    else:
        color = "lightgrey"
        message = f"last: {status}"

    return jsonify({
        "schemaVersion": 1,
        "label": "self-healing",
        "message": message,
        "color": color,
    })

