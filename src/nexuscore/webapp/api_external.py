"""
外部統合 API

VSCode / Chrome 拡張などの外部クライアント向け REST API
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from flask import Blueprint, jsonify, request, g
from sqlalchemy import desc

from nexuscore.webapp import db
from nexuscore.webapp.models import Project, Run
from nexuscore.webapp.auth_api import api_key_required
from nexuscore.webapp.orchestrator_inline import run_orchestrator_inline
from nexuscore.webapp.celery_app import run_orchestrator_task

external_api_bp = Blueprint("external_api", __name__, url_prefix="/api/v1")


# DEPRECATED: This endpoint is deprecated and will be removed in CR-FASTAPI-009.
# FastAPI equivalent: GET /api/v1/projects (see src/nexuscore/api/routes/projects.py)
# This Flask endpoint is kept only for backward compatibility during migration.
# All new clients MUST use the FastAPI endpoint.
@external_api_bp.get("/projects")
@api_key_required
def list_projects():
    """
    プロジェクト一覧を取得する（非推奨）

    GET /api/v1/projects

    認証: X-Api-Key ヘッダまたは api_key クエリパラメータ

    レスポンス:
        {
            "projects": [
                {
                    "id": 1,
                    "name": "Project Name",
                    "repo_url": "https://github.com/owner/repo",
                    "local_path": "/path/to/project",
                    "created_at": "2025-01-01T00:00:00"
                }
            ]
        }

    注意: このエンドポイントは非推奨です。FastAPI 版の /api/v1/projects を使用してください。
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(
        "DEPRECATED endpoint /api/v1/projects (GET) called. "
        "Use FastAPI /api/v1/projects instead. "
        "This endpoint will be removed in v0.9.0."
    )
    user = g.current_api_user

    projects = (
        Project.query
        .filter_by(owner_id=user.id)
        .order_by(desc(Project.created_at))
        .all()
    )

    data = [
        {
            "id": p.id,
            "name": p.name,
            "repo_url": p.repo_url,
            "local_path": p.local_path,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in projects
    ]

    return jsonify({"projects": data})


# TODO: FastAPI migration planned for CR-FASTAPI-010
@external_api_bp.post("/projects/<int:project_id>/run")
@api_key_required
def external_trigger_run(project_id: int):
    """
    Self-Healing Run を発火する

    POST /api/v1/projects/<project_id>/run

    注意: このエンドポイントは FastAPI への移行予定です（CR-FASTAPI-010）。

    認証: X-Api-Key ヘッダまたは api_key クエリパラメータ

    リクエスト JSON:
        {
            "requirement": "Run self-healing for this repo",
            "autonomy_level": 2,
            "fast_lane": true
        }

    レスポンス:
        {
            "run_id": "abc123...",
            "project_id": 1,
            "status": "PENDING",
            "queue_mode": "async" または "sync"
        }

    ステータスコード:
        - 200: 同期実行完了
        - 202: 非同期実行開始（キューに入った）
        - 400: requirement が未指定
        - 404: プロジェクトが見つからない
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(
        f"DEPRECATED endpoint /api/v1/projects/{project_id}/run (POST) called. "
        "FastAPI migration planned for CR-FASTAPI-010. "
        "This endpoint will be removed in v0.9.0."
    )
    user = g.current_api_user

    # プロジェクトの所有権を確認
    project = (
        Project.query
        .filter_by(id=project_id, owner_id=user.id)
        .first()
    )

    if not project:
        return jsonify({"error": "Project not found"}), 404

    # リクエストボディを取得
    payload = request.get_json(silent=True) or {}
    requirement = payload.get("requirement") or ""

    if not requirement:
        return jsonify({"error": "requirement is required"}), 400

    autonomy_level = int(payload.get("autonomy_level", 2))
    fast_lane = bool(payload.get("fast_lane", False))

    # Run レコードを作成
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

    # Celery 使用フラグを確認
    use_celery = os.getenv("NEXUS_USE_CELERY", "1") == "1"

    if use_celery:
        # 非同期実行（Celery）
        async_result = run_orchestrator_task.delay(run.id)
        queue_mode = "async"
        status_code = 202
    else:
        # 同期実行
        try:
            run_orchestrator_inline(
                run=run,
                project=project,
                requirement=requirement,
                autonomy_level=autonomy_level,
                fast_lane=fast_lane,
            )
            queue_mode = "sync"
            status_code = 200
        except Exception as exc:
            # エラーが発生した場合でも Run レコードは作成済み
            db.session.refresh(run)
            return jsonify({
                "run_id": run.run_id,
                "project_id": project.id,
                "status": run.status,
                "queue_mode": "sync",
                "error": str(exc),
            }), 500

    db.session.refresh(run)

    return jsonify({
        "run_id": run.run_id,
        "project_id": project.id,
        "status": run.status,
        "queue_mode": queue_mode,
    }), status_code


# TODO: FastAPI migration planned for CR-FASTAPI-010
@external_api_bp.get("/projects/<int:project_id>/runs/latest")
@api_key_required
def get_latest_run(project_id: int):
    """
    最新の Run の概要を取得する

    GET /api/v1/projects/<project_id>/runs/latest

    注意: このエンドポイントは FastAPI への移行予定です（CR-FASTAPI-010）。

    認証: X-Api-Key ヘッダまたは api_key クエリパラメータ

    レスポンス:
        {
            "run": {
                "id": 1,
                "run_id": "abc123...",
                "status": "SUCCESS",
                "started_at": "2025-01-01T00:00:00",
                "finished_at": "2025-01-01T00:05:00"
            }
        }
        または
        {
            "run": null
        }

    ステータスコード:
        - 200: 成功
        - 404: プロジェクトが見つからない
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(
        f"DEPRECATED endpoint /api/v1/projects/{project_id}/runs/latest (GET) called. "
        "FastAPI migration planned for CR-FASTAPI-010. "
        "This endpoint will be removed in v0.9.0."
    )
    user = g.current_api_user

    # プロジェクトの所有権を確認
    project = (
        Project.query
        .filter_by(id=project_id, owner_id=user.id)
        .first()
    )

    if not project:
        return jsonify({"error": "Project not found"}), 404

    # 最新の Run を取得
    run = (
        Run.query
        .filter_by(project_id=project.id)
        .order_by(desc(Run.started_at))
        .first()
    )

    if not run:
        return jsonify({"run": None})

    return jsonify({
        "run": {
            "id": run.id,
            "run_id": run.run_id,
            "status": run.status,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        }
    })

