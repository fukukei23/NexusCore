"""Task 25: harness dogfooding 計測6項目の収集スクリプト（spec §10・Phase 5）

計測6項目とデータ源:
- 429頻度           : 直接ログなし→breaker OPEN回数で代理観測（429→breaker OPENの設計）
- ブレーカ遷移      : run_state*.json の breaker_state / breaker_opened_at
- ask応答時間 p95   : 計装未実装→null（強化層候補として記録）
- checkpoint失敗率  : artifacts/checkpoints/*/YYYY-MM-DD/log.json の abort_reason
- abort分布         : run_state*.json の abort_reason カウント
- トークン量/タスク : run_state*.json の tokens_used

使い方:
    python scripts/collect_harness_metrics.py [--root REPO_ROOT] [--out PATH]
出力: JSON（artifacts/harness/metrics.json 既定）
"""
from __future__ import annotations

import argparse
import fcntl
import json
from collections import Counter
from pathlib import Path
from typing import Any


def _extract_last_json(text: str) -> dict[str, Any] | None:
    """混在テキスト（askログ+末尾JSON）から最後のJSONオブジェクトを抽出する

    checkpoint log.json は「y\\n[ASK]...\\n{...}」形式のことがあるため、
    後方から JSON パースを試みて最初に成功した位置を採用する。
    """
    for i in range(len(text) - 1, -1, -1):
        if text[i] != "{":
            continue
        try:
            obj = json.loads(text[i:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    return None


def collect_metrics(root: Path) -> dict[str, Any]:
    """spec §10 計測6項目を artifacts から収集する"""
    runs: list[dict[str, Any]] = []
    for p in sorted((root / "artifacts/harness").glob("run_state*.json")):
        try:
            data = json.loads(p.read_text())["data"]
        except (json.JSONDecodeError, KeyError, OSError):
            continue
        data["_source"] = str(p.relative_to(root))
        runs.append(data)

    abort_dist: Counter[str] = Counter()
    breaker_opens = 0
    tokens: list[int] = []
    for r in runs:
        reason = r.get("abort_reason")
        abort_dist["none" if reason is None else str(reason)] += 1
        if r.get("breaker_opened_at") or r.get("breaker_state") == "OPEN":
            breaker_opens += 1
        if isinstance(r.get("tokens_used"), int):
            tokens.append(r["tokens_used"])

    checkpoints: list[dict[str, Any]] = []
    for p in sorted((root / "artifacts/checkpoints").glob("*/2026-*/log.json")):
        obj = _extract_last_json(p.read_text(errors="replace"))
        if obj is None:
            checkpoints.append({"phase": p.parts[-3], "abort_reason": "unparseable"})
            continue
        checkpoints.append({"phase": p.parts[-3], "abort_reason": obj.get("abort_reason")})
    cp_failed = sum(1 for c in checkpoints if c["abort_reason"] not in (None,))
    cp_total = len(checkpoints)

    return {
        "collected_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
        "metrics": {
            "rate_limit_429_proxy_breaker_opens": breaker_opens,
            "breaker_transitions": breaker_opens,
            "ask_response_time_p95_sec": None,
            "ask_instrumentation": "not_implemented",
            "checkpoint_failure_rate": {
                "failed": cp_failed, "total": cp_total,
                "rate": round(cp_failed / cp_total, 3) if cp_total else None,
            },
            "abort_distribution": dict(abort_dist),
            "tokens_per_task": {
                "runs": len(tokens),
                "mean": round(sum(tokens) / len(tokens)) if tokens else None,
                "max": max(tokens) if tokens else None,
                "min": min(tokens) if tokens else None,
            },
        },
        "runs_detail": runs,
        "checkpoints_detail": checkpoints,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="harness dogfooding 計測6項目収集")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, default=Path("artifacts/harness/metrics.json"))
    args = parser.parse_args()
    result = collect_metrics(args.root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    lock = args.out.with_suffix(args.out.suffix + ".lock")
    with open(lock, "w") as lf:  # r2 Gemini#4: 手動/cron競合の排他
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result["metrics"], ensure_ascii=False, indent=2))
    print(f"saved: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
