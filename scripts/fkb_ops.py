#!/usr/bin/env python3
"""FKB運用コマンド: snapshot / deactivate / list-active（nexuscore-bench Phase 0）.

使用例:
  python scripts/fkb_ops.py snapshot /tmp/fkb_snap.json
  python scripts/fkb_ops.py deactivate 3
  python scripts/fkb_ops.py list-active
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database.knowledge_base import KnowledgeBase  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    snap = sub.add_parser("snapshot", help="FKB全エントリをJSONに書き出す")
    snap.add_argument("out_path")
    deact = sub.add_parser("deactivate", help="knowledge_idを論理削除（無効化）")
    deact.add_argument("knowledge_id", type=int)
    sub.add_parser("list-active", help="有効なエントリ一覧")
    args = parser.parse_args()

    kb = KnowledgeBase()
    if args.cmd == "snapshot":
        print(kb.snapshot(args.out_path))
    elif args.cmd == "deactivate":
        ok = kb.deactivate(args.knowledge_id)
        print(f"deactivated: {args.knowledge_id}" if ok else f"not found: {args.knowledge_id}")
    else:
        for e in kb.list_active():
            print(e["id"], e["error_signature"])


if __name__ == "__main__":
    main()
