from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .constitutional_council_agent import ConstitutionalCouncilAgent

logger = logging.getLogger(__name__)


def run_cli_menu(agent: ConstitutionalCouncilAgent) -> None:
    logger.info("--- [Constitutional Council CLI] ---")
    while True:
        try:
            pending_files = sorted(
                list(agent.amendments_dir.glob("pending_*.json")),
                key=lambda f: f.stat().st_mtime,
            )
        except Exception as e:
            logger.error("Error reading amendments directory: %s", e)
            break

        if not pending_files:
            logger.info("保留中の改正案はありません。(No pending amendments.)")
            break

        logger.info("=== 保留中の改正案一覧 (Pending Amendments) ===")
        for idx, f in enumerate(pending_files):
            try:
                with f.open("r", encoding="utf-8") as fp:
                    proposal = json.load(fp)
                    summary = proposal.get(
                        "description", proposal.get("delete_policy_id", "N/A")
                    )
                    logger.info("[%d] %s (Summary: %s...)", idx, f.name, str(summary)[:50])
            except Exception as e:
                logger.error("[%d] %s (Error reading content: %s)", idx, f.name, e)

        logger.info("------------------------------------------")
        choice = (
            input("番号を選択 (a:承認, r:却下, q:終了) [例: a 0] -> ").strip().lower().split()
        )
        if not choice:
            continue

        action = choice[0]
        if action == "q":
            logger.info("CLIを終了します。")
            break

        if len(choice) != 2 or not choice[1].isdigit():
            logger.warning("無効な入力です。例: 'a 0' または 'r 1'")
            continue

        idx = int(choice[1])
        if idx not in range(len(pending_files)):
            logger.warning("無効な番号です。")
            continue

        target_file = pending_files[idx]
        if action == "a":
            logger.info("承認中: %s...", target_file.name)
            if agent.approve_amendment(target_file):
                logger.info("承認成功。")
            else:
                logger.error("承認失敗。ログを確認してください。")
        elif action == "r":
            logger.info("却下中: %s...", target_file.name)
            if agent.reject_amendment(target_file):
                logger.info("却下成功。")
            else:
                logger.error("却下失敗。ログを確認してください。")
        else:
            logger.warning("無効なアクションです。(a, r, q のみ)")
