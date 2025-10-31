# ==============================================================================
# ファイル名: migrate_fkb.py
# 配置場所: scripts/
# 目的: fkb_local.json の内容をPostgreSQLデータベースに一度だけ移行する
# バージョン: 2.0 (Production Ready)
# 使い方:
#   - (通常実行) python scripts/migrate_fkb.py
#   - (プレビュー) python scripts/migrate_fkb.py --dry-run
#   - (ファイル指定) python scripts/migrate_fkb.py --json path/to/your.json
# ==============================================================================
import os
import json
import argparse
import logging
from typing import Any, Dict, List

# 必要に応じてsys.path追加
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.nexuscore.database.knowledge_base import KnowledgeBase

logger = logging.getLogger("migrate_fkb")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

REQUIRED_KEYS = {"error_signature"}

def load_json(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("fkb_local.json は配列(list)形式である必要があります。")
    return data

def normalize_entry(raw: Dict[str, Any]) -> Dict[str, Any]:
    # 許容するキーを抽出（DBモデルに合わせる）
    allowed = {"error_signature", "cause", "target", "solution_pattern", "description"}
    entry = {k: raw.get(k) for k in allowed}
    missing = REQUIRED_KEYS - {k for k, v in entry.items() if v not in (None, "")}
    if missing:
        raise ValueError(f"必須キーが不足: {missing} (entry={raw})")
    return entry

def main():
    parser = argparse.ArgumentParser(description="Migrate FKB JSON to PostgreSQL")
    parser.add_argument("--json", default="fkb_local.json", help="Path to fkb_local.json")
    parser.add_argument("--dry-run", action="store_true", help="Do not write, only show plan")
    args = parser.parse_args()

    kb = KnowledgeBase()
    if not getattr(kb, "_engine", None):
        logger.error("KnowledgeBaseが初期化されていません（DATABASE_URLの確認）")
        sys.exit(1)

    data = load_json(args.json)
    logger.info(f"読み込み件数: {len(data)}")

    created = 0
    exists = 0
    failed = 0

    for i, raw in enumerate(data, 1):
        try:
            entry = normalize_entry(raw)
            if args.dry_run:
                logger.info(f"[DRY-RUN] {i}: {entry.get('error_signature')}")
                continue
            result = kb.add_knowledge(entry)
            if result == "created":
                created += 1
            elif result == "exists":
                exists += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
            logger.error(f"{i}件目でエラー: {e}")

    if args.dry_run:
        logger.info("DRY-RUN完了（DBへの書き込みはしていません）")
    logger.info(f"結果: created={created}, exists={exists}, failed={failed}")

if __name__ == "__main__":
    main()
