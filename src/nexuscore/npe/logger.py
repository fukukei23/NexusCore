# ==============================================================================
# File: src/nexuscore/npe/logger.py
# Purpose:
#   - システム全体の監査証跡（Audit Trail）を記録する
#   - スレッドセーフ (Lock)
#   - 簡易ローテーション
# ==============================================================================
from __future__ import annotations

import datetime
import json
import logging
import os
import threading
from pathlib import Path

_lock = threading.Lock()
AUDIT_DIR = Path(os.getenv("NPE_AUDIT_DIR", "logs/npe"))
AUDIT_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_LOG = AUDIT_DIR / "npe_audit_log.jsonl"
ROTATE_BYTES = int(os.getenv("NPE_AUDIT_ROTATE_BYTES", "5242880"))  # 5MB
ROTATE_KEEP = int(os.getenv("NPE_AUDIT_ROTATE_KEEP", "3"))


def _rotate_if_needed(path: Path) -> None:
    try:
        if not path.exists():
            return
        if path.stat().st_size < ROTATE_BYTES:
            return
        # ローテーション: .1, .2, ...
        for i in range(ROTATE_KEEP, 0, -1):
            older = path.with_suffix(path.suffix + f".{i}")
            newer = path.with_suffix(path.suffix + (f".{i-1}" if i > 1 else ""))
            if newer.exists():
                if older.exists():
                    older.unlink(missing_ok=True)
                newer.rename(older)
        path.rename(path.with_suffix(path.suffix + ".1"))
    except Exception as e:
        print(f"[NPE-Logger] WARN: rotation failed: {e}")


def log_transaction(log_data: dict, log_file: str | Path = DEFAULT_LOG):
    """
    監査証跡をJSONLで追記。排他＋簡易ローテーション＋フォールバック出力。

    既存の動作を維持しつつ、Flaskアプリコンテキストが存在する場合はDBにも書き込む。
    """
    if isinstance(log_file, str):
        log_file = Path(log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    log_data["event_timestamp_utc"] = datetime.datetime.now(datetime.UTC).isoformat()
    entry_compact = json.dumps(log_data, ensure_ascii=False)

    # コンソール（開発者の可視性）
    try:
        pretty = json.dumps(log_data, indent=2, ensure_ascii=False)
        print("\n--- NPE AUDIT LOG ---")
        print(pretty)
        print("---------------------\n")
    except Exception as e:
        logging.getLogger("npe.logger").warning("Console print failed: %s", e)

    with _lock:
        try:
            _rotate_if_needed(log_file)
            with log_file.open("a", encoding="utf-8") as f:
                f.write(entry_compact + "\n")
        except Exception as e:
            # ファイルに書けない状況でも"監査の消失"を避ける
            print(f"[NPE-Logger] CRITICAL: failed to write audit file '{log_file}': {e}")
            print(entry_compact)

    # DBにも書き込む（ロギングプロバイダー経由）
    # Webapp層への直接依存を削除し、インターフェース経由でアクセス
    try:
        from nexuscore.core.logging_interface import get_logging_provider

        provider = get_logging_provider()
        provider.enhance_transaction(log_data, log_file)
    except Exception as e:
        logging.getLogger("npe.logger").warning("DB logging provider failed: %s", e)
