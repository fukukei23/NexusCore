"""
NexusCore Webapp - Orchestrator ヘルパー関数

Orchestrator のインスタンス化と実行を簡易化するヘルパー関数。
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any

from nexuscore.config.unified_config import get_config
from nexuscore.core.orchestrator import Orchestrator
from nexuscore.core.agent_factory import assemble_agent_team
from nexuscore.core.session_control import SessionController

logger = logging.getLogger(__name__)


def create_orchestrator_instance(
    project_path: str,
    autonomy_level: int = 1,
    session_id: str | None = None,
) -> Orchestrator:
    """
    Orchestrator インスタンスを作成する。

    Args:
        project_path: プロジェクトのルートパス
        autonomy_level: 自動化レベル（0=対話中心, 1=半自動, 2=ほぼ全自動）
        session_id: セッションID（省略時は自動生成）

    Returns:
        Orchestrator インスタンス
    """
    # constitution の作成
    constitution: dict[str, Any] = {
        "automation_policy": {
            "autonomy_level": autonomy_level,
        }
    }

    # デフォルトの constitution に設定をマージ
    try:
        _cfg = get_config()
        constitution["automation_policy"].update(
            {"autonomy_level": autonomy_level}
        )
    except Exception:
        pass  # 失敗してもデフォルト値で進む

    # セッションIDの決定
    if not session_id:
        session_id = uuid.uuid4().hex

    # SessionController を初期化
    session_dir = os.path.join(project_path, ".nexus", "sessions")
    session_controller = SessionController(
        session_id=session_id,
        root_dir=session_dir,
    )

    # エージェントチームを組み立て
    agent_team = assemble_agent_team(project_path=project_path)

    # Orchestrator インスタンスを作成
    orchestrator = Orchestrator(
        project_path=project_path,
        constitution=constitution,
        session_controller=session_controller,
        **agent_team,
    )

    logger.info(f"Orchestrator instance created for project_path={project_path}")
    return orchestrator


def run_orchestrator_sync(
    project_path: str,
    user_requirement: str,
    run_db_id: int | None = None,
    autonomy_level: int = 1,
    language: str = "ja",
    fast_lane: bool = False,
) -> None:
    """
    Orchestrator を同期的に実行する（フェーズ1用）。

    Args:
        project_path: プロジェクトのルートパス
        user_requirement: ユーザー要件
        run_db_id: Run.id（Webapp側でRunレコードを作成したときのID）
        autonomy_level: 自動化レベル
        language: 言語（デフォルト: "ja"）
        fast_lane: 高速レーン実行フラグ

    Raises:
        Exception: Orchestrator 実行時のエラー
    """
    orchestrator = create_orchestrator_instance(
        project_path=project_path,
        autonomy_level=autonomy_level,
    )

    orchestrator.run_full_project(
        user_requirement=user_requirement,
        language=language,
        fast_lane=fast_lane,
        run_db_id=run_db_id,
    )
