# ==============================================================================
# File: src/nexuscore/core/job_state_machine.py
# Purpose:
#   - ジョブの進行状況を管理するステートマシン
#   - 状態遷移を制御し、各状態ごとに異なる動作を定義
#   - SessionController と RunHistoryLogger と統合
# ==============================================================================
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Type

from nexuscore.core.session_control import SessionController
from nexuscore.core.run_history import RunHistoryLogger, RunRecord


logger = logging.getLogger(__name__)


# ==============================================================================
# 状態定義
# ==============================================================================

class State(ABC):
    """ステートマシンの基底状態クラス"""

    def __init__(self, machine: "JobStateMachine"):
        self.machine = machine

    @abstractmethod
    def handle(self) -> None:
        """状態固有の処理を実行"""
        pass

    @abstractmethod
    def get_state_name(self) -> str:
        """状態名を返す"""
        pass

    def can_transition_to(self, target_state: Type["State"]) -> bool:
        """遷移可能かどうかを判定（デフォルトは全遷移許可）"""
        return True


class PendingState(State):
    """ジョブ待機状態"""

    def handle(self) -> None:
        logger.info(f"Job {self.machine.job_id} is pending.")
        self.machine._update_state_metadata({"status": "pending", "message": "Job is waiting to start"})

    def get_state_name(self) -> str:
        return "pending"

    def can_transition_to(self, target_state: Type["State"]) -> bool:
        """PendingState からは RunningState へのみ遷移可能"""
        return target_state == RunningState


class RunningState(State):
    """ジョブ実行中状態"""

    def handle(self) -> None:
        logger.info(f"Job {self.machine.job_id} is running.")
        self.machine._update_state_metadata({"status": "running", "message": "Job is executing"})

    def get_state_name(self) -> str:
        return "running"

    def can_transition_to(self, target_state: Type["State"]) -> bool:
        """RunningState からは CompletedState または FailedState へのみ遷移可能"""
        return target_state in (CompletedState, FailedState)


class CompletedState(State):
    """ジョブ完了状態"""

    def handle(self) -> None:
        logger.info(f"Job {self.machine.job_id} is completed.")
        self.machine._update_state_metadata({"status": "completed", "message": "Job completed successfully"})
        self.machine._record_completion()

    def get_state_name(self) -> str:
        return "completed"

    def can_transition_to(self, target_state: Type["State"]) -> bool:
        """CompletedState は終端状態（遷移不可）"""
        return False


class FailedState(State):
    """ジョブ失敗状態"""

    def __init__(self, machine: "JobStateMachine", error_message: Optional[str] = None):
        super().__init__(machine)
        self.error_message = error_message or "Unknown error"

    def handle(self) -> None:
        logger.error(f"Job {self.machine.job_id} failed: {self.error_message}")
        self.machine._update_state_metadata({
            "status": "failed",
            "message": "Job execution failed",
            "error": self.error_message
        })
        self.machine._record_failure(self.error_message)

    def get_state_name(self) -> str:
        return "failed"

    def can_transition_to(self, target_state: Type["State"]) -> bool:
        """FailedState は終端状態（遷移不可）"""
        return False


# ==============================================================================
# ステートマシン本体
# ==============================================================================

@dataclass
class JobMetadata:
    """ジョブのメタデータ"""
    job_id: str
    job_type: str = "orchestrator"  # "orchestrator", "self_healing", etc.
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    status: str = "pending"
    message: str = ""
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


class JobStateMachine:
    """
    ジョブの進行状況を管理するステートマシン。

    機能:
    - 状態遷移の管理（Pending → Running → Completed/Failed）
    - SessionController との統合（状態の永続化）
    - RunHistoryLogger との統合（履歴の記録）
    """

    def __init__(
        self,
        job_id: str,
        session_controller: Optional[SessionController] = None,
        history_logger: Optional[RunHistoryLogger] = None,
        job_type: str = "orchestrator",
    ):
        self.job_id = job_id
        self.job_type = job_type
        self.state: State = PendingState(self)
        self.metadata = JobMetadata(job_id=job_id, job_type=job_type)
        self.session_controller = session_controller
        self.history_logger = history_logger

        # 初期状態を処理
        self.state.handle()

    def transition_to(self, new_state_class: Type[State], **kwargs) -> None:
        """
        状態遷移を実行する。

        Args:
            new_state_class: 遷移先の状態クラス
            **kwargs: 状態クラスのコンストラクタに渡す引数（例: FailedState の error_message）

        Raises:
            ValueError: 遷移が許可されていない場合
        """
        # 遷移可能性をチェック
        if not self.state.can_transition_to(new_state_class):
            raise ValueError(
                f"Cannot transition from {self.state.get_state_name()} to {new_state_class.__name__}"
            )

        # 状態遷移を実行
        old_state_name = self.state.get_state_name()
        self.state = new_state_class(self, **kwargs)
        new_state_name = self.state.get_state_name()

        logger.info(
            f"Job {self.job_id}: State transition {old_state_name} -> {new_state_name}"
        )

        # 状態固有の処理を実行
        self.state.handle()

        # セッションに状態を保存
        if self.session_controller:
            self.session_controller.checkpoint(
                phase=f"state_{new_state_name}",
                metadata={
                    "state": new_state_name,
                    "job_id": self.job_id,
                    "job_type": self.job_type,
                    **self.metadata.details,
                }
            )

        # 履歴に記録
        self._log_state_transition(old_state_name, new_state_name)

    def start(self) -> None:
        """ジョブを開始（Pending → Running）"""
        if not isinstance(self.state, PendingState):
            raise ValueError(f"Cannot start job in state {self.state.get_state_name()}")
        self.metadata.started_at = time.time()
        self.transition_to(RunningState)

    def complete(self, details: Optional[Dict[str, Any]] = None) -> None:
        """ジョブを完了（Running → Completed）"""
        if not isinstance(self.state, RunningState):
            raise ValueError(f"Cannot complete job in state {self.state.get_state_name()}")
        if details:
            self.metadata.details.update(details)
        self.metadata.finished_at = time.time()
        self.transition_to(CompletedState)

    def fail(self, error_message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """ジョブを失敗として記録（Running → Failed）"""
        if not isinstance(self.state, RunningState):
            raise ValueError(f"Cannot fail job in state {self.state.get_state_name()}")
        if details:
            self.metadata.details.update(details)
        self.metadata.finished_at = time.time()
        self.transition_to(FailedState, error_message=error_message)

    def get_current_state(self) -> str:
        """現在の状態名を取得"""
        return self.state.get_state_name()

    def get_metadata(self) -> JobMetadata:
        """ジョブのメタデータを取得"""
        return self.metadata

    # --------------------------------------------------------------------------
    # 内部メソッド
    # --------------------------------------------------------------------------

    def _update_state_metadata(self, updates: Dict[str, Any]) -> None:
        """状態メタデータを更新"""
        if "status" in updates:
            self.metadata.status = updates["status"]
        if "message" in updates:
            self.metadata.message = updates["message"]
        if "error" in updates:
            self.metadata.error = updates["error"]
        if "details" in updates:
            self.metadata.details.update(updates["details"])

    def _record_completion(self) -> None:
        """完了を履歴に記録"""
        if not self.history_logger:
            return

        record = RunRecord(
            run_id=self.job_id,
            session_id=self.session_controller.session_id if self.session_controller else self.job_id,
            kind=self.job_type,
            status="success",
            started_at=self.metadata.started_at or time.time(),
            finished_at=self.metadata.finished_at or time.time(),
            summary=self.metadata.message,
            details=self.metadata.details,
        )
        self.history_logger.log_run(record)

    def _record_failure(self, error_message: str) -> None:
        """失敗を履歴に記録"""
        if not self.history_logger:
            return

        record = RunRecord(
            run_id=self.job_id,
            session_id=self.session_controller.session_id if self.session_controller else self.job_id,
            kind=self.job_type,
            status="error",
            started_at=self.metadata.started_at or time.time(),
            finished_at=self.metadata.finished_at or time.time(),
            summary=f"Job failed: {error_message}",
            details={**self.metadata.details, "error": error_message},
        )
        self.history_logger.log_run(record)

    def _log_state_transition(self, old_state: str, new_state: str) -> None:
        """状態遷移をログに記録"""
        logger.debug(
            f"Job {self.job_id}: State transition logged: {old_state} -> {new_state}"
        )

