"""
Webapp DB クエリ共通化ヘルパー

P2-5: filter_by(owner_id=user.id) パターンの共通化
P2-1: N+1 クエリ解消用の eager loading ヘルパー
"""

from __future__ import annotations

from flask import request
from sqlalchemy import desc
from sqlalchemy.orm import Query, subqueryload

from nexuscore.webapp.models import ExecutionLog, PatchRecord, Project, Run


def user_projects_query(user_id: int) -> Query:
    """ユーザー所有プロジェクトのベースクエリ"""
    return Project.query.filter_by(owner_id=user_id)


def user_project_or_404(user_id: int, project_id: int) -> Project:
    """ユーザー所有プロジェクトを1件取得、存在しなければ404"""
    return Project.query.filter_by(id=project_id, owner_id=user_id).first_or_404()


def user_runs_stats(user_id: int) -> dict[str, int]:
    """ユーザー全プロジェクトの Run 集計を1クエリで取得"""
    total = Run.query.join(Project).filter(Project.owner_id == user_id).count()
    success = (
        Run.query.join(Project).filter(Project.owner_id == user_id, Run.status == "SUCCESS").count()
    )
    failed = (
        Run.query.join(Project).filter(Project.owner_id == user_id, Run.status == "FAILED").count()
    )
    return {"total": total, "success": success, "failed": failed}


def project_latest_run(project_id: int) -> Run | None:
    """プロジェクトの最新 Run を1件取得"""
    return Run.query.filter_by(project_id=project_id).order_by(desc(Run.created_at)).first()


def project_runs_with_logs(project_id: int, limit: int = 50) -> list[Run]:
    """プロジェクトの Run 一覧を eager loading 付きで取得 (N+1 解消)"""
    return (
        Run.query.options(subqueryload(Run.execution_logs))
        .filter_by(project_id=project_id)
        .order_by(desc(Run.created_at))
        .limit(limit)
        .all()
    )


def projects_with_latest_run(user_id: int) -> list[Project]:
    """ユーザーのプロジェクト一覧を最新Run付きで取得"""
    return (
        Project.query.filter_by(owner_id=user_id)
        .order_by(desc(Project.updated_at))
        .all()
    )


def paginate_query(query: Query, order_column=None, per_page: int = 50) -> tuple:
    """
    クエリをページングして (paginated_result, pagination_dict) を返す。

    Args:
        query: ベースクエリ (order_by 前提)
        order_column: ソート対象カラム。省略時はソートなし
        per_page: 1ページあたりの件数

    Returns:
        (paginated, pagination_info) — paginated は Pagination オブジェクト
    """
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", per_page))
    if order_column is not None:
        query = query.order_by(desc(order_column))
    result = query.paginate(page=page, per_page=per_page, error_out=False)  # type: ignore[attr-defined]
    pagination = {
        "page": page,
        "per_page": per_page,
        "total": result.total,
        "pages": result.pages,
    }
    return result, pagination


def run_logs_payload(run_id: int) -> tuple[int, str | None]:
    """Run の ExecutionLog から retry_count と last_error_class を抽出"""
    import json

    logs = ExecutionLog.query.filter_by(run_id=run_id).all()
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

    return retry_count, last_error_class


def run_llm_cost(run_id: int) -> tuple[int, float, dict]:
    """
    Run の LLM コスト情報を集計。

    Returns:
        (call_count, total_cost, llm_breakdown)
    """
    import json

    logs = ExecutionLog.query.filter_by(run_id=run_id, source="NPE").all()
    call_count = len(logs)
    total_cost = 0.0
    breakdown: dict[str, dict] = {}

    for lg in logs:
        payload = lg.payload_json or {}
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}

        model = payload.get("model") or payload.get("model_name") or "unknown"
        usage = payload.get("usage", {})

        if model not in breakdown:
            breakdown[model] = {
                "call_count": 0,
                "token_prompt": 0,
                "token_completion": 0,
                "token_total": 0,
                "cost_total": 0.0,
            }

        breakdown[model]["call_count"] += 1
        breakdown[model]["token_prompt"] += usage.get("prompt_tokens", 0)
        breakdown[model]["token_completion"] += usage.get("completion_tokens", 0)
        breakdown[model]["token_total"] += usage.get("prompt_tokens", 0) + usage.get(
            "completion_tokens", 0
        )

        cost = (
            payload.get("estimated_cost")
            or payload.get("cost_jpy")
            or usage.get("cost_jpy", 0.0)
        )
        try:
            total_cost += float(cost)
            breakdown[model]["cost_total"] += float(cost)
        except Exception:
            pass

    return call_count, total_cost, breakdown


def run_patch_files(run_id: int) -> set[str]:
    """Run のパッチファイルパス一覧を取得"""
    patches = PatchRecord.query.filter_by(run_id=run_id).all()
    return {p.file_path for p in patches}
