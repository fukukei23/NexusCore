"""SKILL.md 乖離検知チェッカー（L141=A「乖離検知のみ」・同期はしない）。

CLI版スキル（~/.claude/ -skills/multi-llm-review/SKILL.md・運用で育つ正典）と
NexusCore 組込み版の乖離を**検知するだけ**（A案・ふくけい承認 2026-10-08）。

使い方:
    python -m nexuscore.scripts.check_skill_drift
        （baseline と現行 compare SKILL.md を突合・drift 時 exit 1）
    python -m nexuscore.scripts.check_skill_drift --update-baseline
        （現行 hash で baseline を更新 = re-adoption）
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime

DEFAULT_SKILL = os.path.expanduser("~/.claude/skills/multi-llm-review/SKILL.md")
DEFAULT_BASELINE = os.path.expanduser(
    "~/.claude/state/nexuscore-skill-baseline/multi_llm_review_SKILL.md.sha256"
)


def compute_sha256(path: str) -> str | None:
    """ファイルのsha256を返す（存在しなければ None）。"""
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def detect_drift(baseline_hash: str | None, current_hash: int | None) -> str:
    """baseline と現行の突合結果を返す（ok / drift / missing）。"""
    if not baseline_hash or not current_hash:
        return "missing"
    return "ok" if baseline_hash == current_hash else "drift"


def load_baseline(path: str) -> dict | None:
    """baseline JSON（sha256+note+recorded_at）を読む（無ければ None）。"""
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_baseline(path: str, sha256: str, note: str = "") -> None:
    """baseline を JSON で記録（取込み直後の1回・re-adoption時に --update-baseline）。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {
        "sha256": sha256,
        "note": note,
        "recorded_at": datetime.now().isoformat(timespec="seconds"),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="SKILL.md drift checker (detect-only)")
    ap.add_argument("--baseline", default=DEFAULT_BASELINE)
    ap.add_argument("--skill", default=DEFAULT_SKILL)
    ap.add_argument(
        "--update-baseline", action="store_true",
        help="現行 hash で baseline を更新（re-adoption）",
    )
    args = ap.parse_args(argv)
    current_hash = compute_sha256(args.skill)
    baseline = load_baseline(args.baseline)
    if args.update_baseline:
        write_baseline(args.baseline, current_hash or "", note="manual update")
        print(f"baseline updated: {args.baseline} sha256={current_hash}")
        return 0
    status = detect_drift((baseline or {}).get("sha256"), current_hash)
    message = {
        "ok": "SKILL.md は baseline と一致（乖離なし）",
        "drift": "⚠️ SKILL.md が baseline から乖離（組込み版は取込時点で凍結・--update-baseline で再記録）",
        "missing": "baseline または SKILL.md が見つからない（初回は --update-baseline で記録）",
    }[status]
    print(json.dumps(
        {
            "status": status,
            "skill_path": args.skill,
            "baseline_path": args.baseline,
            "message": message,
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 1 if status == "drift" else 0


if __name__ == "__main__":
    sys.exit(main())
