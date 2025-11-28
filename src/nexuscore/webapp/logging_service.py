"""
NexusCore SaaS基盤 - ExecutionLog 書き込みサービス

Orchestrator / NPE / SandboxExecutor から直接 DB を触らずに、
「Flask アプリコンテキストがあれば ExecutionLog を書く」ための薄いラッパ。

既存の CLI 実行は挙動を変えない（has_app_context() チェックで分岐）。
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

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
    except Exception:
        # 万一シリアライズに失敗してもログ全体が死なないようにする
        return json.dumps({"raw": str(payload)}, ensure_ascii=False)


def log_execution_event(
    *,
    run_id: Optional[int],
    source: str,
    level: str,
    message: str,
    payload: Optional[dict[str, Any]] = None,
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
        payload_json=_to_json(payload),
        created_at=datetime.utcnow(),
    )

    db.session.add(log)

    # ログは失敗してもコア処理を壊さないように、commit 失敗は握りつぶす方向で
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

