from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from flask import has_app_context

from nexuscore.webapp import db
from nexuscore.webapp.models import ExecutionLog


def _to_json(payload: Any) -> str:
    """
    ペイロードをJSON文字列に変換。

    Args:
        payload: 任意のオブジェクト

    Returns:
        JSON文字列（失敗時はフォールバック）
    """
    if payload is None:
        return ""

    try:
        return json.dumps(payload, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return json.dumps({"raw": str(payload)}, ensure_ascii=False)


def log_execution_event(
    *,
    run_id: int | None,
    source: str,
    level: str,
    message: str,
    payload: dict[str, Any] | None = None,
) -> None:
    """
    ExecutionLog に1行追加する。

    - Flaskアプリコンテキストが無い場合は何もしない（CLI実行を壊さない）。

    Args:
        run_id: Run.id（紐付け可能な場合のみ指定）
        source: ログのソース（"NPE", "ORCHESTRATOR", "AGENT", "SANDBOX" など）
        level: ログレベル（"INFO", "WARNING", "ERROR"）
        message: 短い説明メッセージ（最大512文字）
        payload: 任意の詳細情報（辞書形式）
    """
    if not has_app_context():
        return

    log = ExecutionLog(
        run_id=run_id,
        source=source,
        level=level,
        message=message[:512],  # DB負荷抑制のため適当に切る
        payload_json=payload,
        created_at=datetime.now(UTC),
    )

    db.session.add(log)

    # ログは失敗してもコア処理を壊さないように、commit 失敗は握りつぶす方向で
    try:
        db.session.commit()
    except Exception:  # noqa: BLE001 — DB commit failure must not crash the app
        db.session.rollback()
