from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from nexuscore.guard.policy_engine import GuardDecision, GuardInput, GuardResult

logger = logging.getLogger(__name__)

# Schema version for trace events (fixed identifier)
SCHEMA_VERSION = "trace_event_v0_1"

# Default trace directory
DEFAULT_TRACE_DIR = Path("var/trace")
DEFAULT_TRACE_FILE = DEFAULT_TRACE_DIR / "guard_decisions.jsonl"


def _get_git_commit() -> str | None:
    """Git commit hash を取得（取得不能なら None）"""
    try:
        import subprocess

        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=1.0,
            cwd=Path.cwd(),
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _get_repo_dirty() -> bool | None:
    """Git repository が dirty かどうかを取得（取得不能なら None）"""
    try:
        import subprocess

        result = subprocess.run(
            ["git", "diff", "--quiet"],
            capture_output=True,
            text=True,
            timeout=1.0,
            cwd=Path.cwd(),
        )
        # returncode 0 = clean, non-zero = dirty
        return result.returncode != 0
    except Exception:
        pass
    return None


def _build_trace_event(
    environment: str,
    decision: GuardDecision,
    reasons: list[str],
    guard_input: GuardInput,
    policy_id: str = "nexusguard-v0.1.1",
) -> dict:
    """
    TraceEvent を構築する。

    Args:
        environment: 環境（production/staging/poc）
        decision: Guard判定結果
        reasons: 判定理由のリスト
        guard_input: Guard入力
        policy_id: ポリシーID（デフォルト: nexusguard-v0.1.1）

    Returns:
        TraceEvent の辞書
    """
    # 必須フィールド
    event = {
        "event_type": "guard_decision",
        "schema_version": SCHEMA_VERSION,
        "timestamp": datetime.now(UTC).isoformat(),
        "environment": environment,
        "policy_id": policy_id,
        "decision": decision.value,
        "reasons": reasons,
    }

    # artifacts（常に4キーを保持、無い場合はnull）
    artifacts = {
        "eval_report_id": None,  # 将来の拡張用（現時点ではnull）
        "test_run_id": None,  # 将来の拡張用（現時点ではnull）
        "diff_id": None,  # 将来の拡張用（現時点ではnull）
        "security_scan_id": None,  # 将来の拡張用（現時点ではnull）
    }
    event["artifacts"] = artifacts

    # code_identity（取得可能な範囲で埋める）
    code_identity: dict[str, Any] = {}
    git_commit = _get_git_commit()
    if git_commit:
        code_identity["git_commit"] = git_commit
    else:
        code_identity["git_commit"] = None

    repo_dirty = _get_repo_dirty()
    if repo_dirty is not None:
        code_identity["repo_dirty"] = repo_dirty
    else:
        code_identity["repo_dirty"] = None

    event["code_identity"] = code_identity

    # override（GuardDecision で override を許容する設計がある以上、Trace に保存）
    if guard_input.override:
        # override がある場合（将来的に approver 等を追加する可能性を考慮して構造を固定）
        event["override"] = {
            "override": True,
            "approver": None,  # 将来の拡張用（現時点ではnull）
            "expires_at": None,  # 将来の拡張用（現時点ではnull）
            "override_reason": None,  # 将来の拡張用（現時点ではnull）
        }
    else:
        # override が無い場合
        event["override"] = None

    return event


def write_guard_decision_event(
    guard_result: GuardResult,
    guard_input: GuardInput,
    trace_file: Path | None = None,
    policy_id: str = "nexusguard-v0.1.1",
) -> None:
    """
    GuardDecision イベントを JSONL ファイルに追記する。

    Args:
        guard_result: Guard判定結果
        guard_input: Guard入力
        trace_file: 保存先ファイルパス（None の場合はデフォルト）
        policy_id: ポリシーID（デフォルト: nexusguard-v0.1.1）

    例外:
        保存失敗時は例外を外に投げず、警告ログを出力する。
    """
    if trace_file is None:
        trace_file = DEFAULT_TRACE_FILE

    try:
        # ディレクトリを作成（存在しない場合）
        trace_file.parent.mkdir(parents=True, exist_ok=True)

        # TraceEvent を構築
        event = _build_trace_event(
            environment=guard_input.environment,
            decision=guard_result.decision,
            reasons=guard_result.reasons,
            guard_input=guard_input,
            policy_id=policy_id,
        )

        # JSONL として追記（atomic append 相当）
        with open(trace_file, "a", encoding="utf-8") as f:
            json_line = json.dumps(event, ensure_ascii=False)
            f.write(json_line + "\n")

    except Exception as e:
        # 保存失敗は例外を外に投げず警告ログにする
        logger.warning(
            f"Failed to write guard decision event to {trace_file}: {e}",
            exc_info=True,
        )


class TraceWriter:
    """
    TraceEvent を書き込むための Writer クラス。

    将来的な拡張用（現時点では write_guard_decision_event をラップするだけ）。
    """

    def __init__(self, trace_file: Path | None = None):
        """
        Args:
            trace_file: 保存先ファイルパス（None の場合はデフォルト）
        """
        self.trace_file = trace_file or DEFAULT_TRACE_FILE

    def write_guard_decision(
        self,
        guard_result: GuardResult,
        guard_input: GuardInput,
        policy_id: str = "nexusguard-v0.1.1",
    ) -> None:
        """
        GuardDecision イベントを書き込む。

        Args:
            guard_result: Guard判定結果
            guard_input: Guard入力
            policy_id: ポリシーID（デフォルト: nexusguard-v0.1.1）
        """
        write_guard_decision_event(
            guard_result=guard_result,
            guard_input=guard_input,
            trace_file=self.trace_file,
            policy_id=policy_id,
        )
