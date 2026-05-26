from __future__ import annotations

from typing import Any

try:
    from nexuscore.webapp.logging_service import log_execution_event as _log_exec_event
except ImportError:
    _log_exec_event = None


def log_orchestrator_event(
    *,
    run_db_id: int | None,
    phase: str,
    status: str,
    message: str,
    extra: dict[str, Any] | None = None,
) -> None:
    """
    Orchestrator から呼ぶための薄いフック。

    Webapp / DB が無い環境では何もしない。

    Args:
        run_db_id: Run.id（Webapp側でRunレコードを作成したときのID）
        phase: フェーズ名（"startup", "requirement", "planning", "coding", "testing", "review", "shutdown" など）
        status: ステータス（"STARTED", "SUCCESS", "FAILED", "FINISHED" など）
        message: メッセージ
        extra: 追加情報（辞書形式）
    """
    if _log_exec_event is None:
        return

    level = "ERROR" if status.lower() in ("failed", "error") else "INFO"
    payload: dict[str, Any] = {"phase": phase, "status": status}
    if extra:
        payload.update(extra)

    _log_exec_event(
        run_id=run_db_id,
        source="ORCHESTRATOR",
        level=level,
        message=message,
        payload=payload,
    )
