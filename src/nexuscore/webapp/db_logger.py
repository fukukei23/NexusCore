"""
NexusCore SaaS基盤 - DBログフック

既存の NPE logger.log_transaction を拡張して、
Flaskアプリコンテキストが存在する場合のみDBに書き込む。

既存の CLI 実行を壊さないよう、防衛的に実装。

このモジュールは既存の log_transaction からの呼び出しを想定しているが、
新しいコードでは logging_service.log_execution_event を直接使用することを推奨。
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def enhance_log_transaction(log_data: dict[str, Any], log_file: str | None = None) -> None:
    """
    既存の log_transaction を拡張して、DBにも書き込む。

    この関数は既存の log_transaction の後に呼び出されることを想定。
    内部では logging_service.log_execution_event を使用する。

    Args:
        log_data: log_transaction に渡されたデータ
        log_file: ログファイルパス（使用しないが互換性のため）
    """
    try:
        from nexuscore.webapp.logging_service import log_execution_event
    except ImportError:
        # webapp がインストールされていない場合はスキップ（CLI実行時など）
        return
    except Exception:
        # インポートエラーは既存の処理を止めない
        return

    # log_data から情報を抽出
    source = log_data.get("source", "NPE")
    level = log_data.get("level", "INFO")

    # task_type や model などの情報からメッセージを生成
    task_type = log_data.get("task_type", "")
    model = log_data.get("model", "")

    # event フィールドから情報を抽出（NPE の log_transaction で使用）
    event = log_data.get("event", "")
    if event == "llm_call":
        # NPE の LLM 呼び出しログ
        status = "SUCCESS" if log_data.get("ok", True) else "FAILED"
        level = "ERROR" if status == "FAILED" else "INFO"
        message = f"{task_type} via {model}" if task_type and model else f"LLM call: {model}"
    elif event == "llm_blocked":
        level = "WARNING"
        message = f"LLM blocked: {model} ({log_data.get('reason', '')})"
    else:
        message = f"{task_type} via {model}" if task_type and model else "NPE transaction"

    # run_id を取得（log_data に含まれている場合）
    run_id = log_data.get("run_id")

    # payload を作成（元の log_data から必要な情報を抽出）
    payload: dict[str, Any] = {}
    if task_type:
        payload["task_type"] = task_type
    if model:
        payload["model"] = model
    if "usage" in log_data:
        payload["token_usage"] = log_data["usage"]
    if "cost_jpy" in log_data:
        payload["cost_jpy"] = log_data["cost_jpy"]
    if "estimated_cost" in log_data:
        payload["estimated_cost"] = log_data["estimated_cost"]
    if not payload:
        payload = log_data  # フォールバック

    # DBに書き込み
    log_execution_event(
        run_id=run_id,
        source=source,
        level=level,
        message=message,
        payload=payload,
    )
