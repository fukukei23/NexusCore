# ==============================================================================
# フォルダ: tools/
# ファイル名: chronicle_visualizer.py
# 目的: project_chronicle.jsonl を可視化（進化マップ / ヒートマップ / LLMモデル利用推移）
# 実行例:
#   python tools/chronicle_visualizer.py .  # デフォルト: project_chronicle.jsonl を読み込む
# ==============================================================================
from __future__ import annotations
import json
from collections import defaultdict, Counter
from datetime import datetime
from pathlib import Path
import argparse

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def load_chronicle(chronicle: Path):
    rows = []
    with open(chronicle, "r", encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
                rows.append(r)
            except Exception:
                continue
    return rows

def normalize_event_type(row: dict) -> str:
    # 後方互換: event_type が無い場合は event を簡易マッピング
    et = row.get("event_type")
    if et:
        return et
    ev = (row.get("event") or "").lower()
    if "genesis" in ev: return "genesis"
    if "snapshot" in ev: return "snapshot"
    if "export" in ev: return "export_generated"
    if "file_change" in ev: return "file_modified"  # 厳密には不明だが視覚上の便宜
    return "unknown"

def to_dt(ts: str):
    try:
        # 2025-08-09T02:34:56+00:00
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project_root")
    ap.add_argument("--chronicle", default="project_chronicle.jsonl")
    args = ap.parse_args()
    project_root = Path(args.project_root).absolute()
    chronicle = project_root / args.chronicle
    rows = load_chronicle(chronicle)

    # ---- 進化マップ（フォルダ×時系列） ----
    folder_events = defaultdict(list)
    for r in rows:
        dt = to_dt(r.get("timestamp", ""))
        if not dt: continue
        et = normalize_event_type(r)
        files = r.get("files_changed") or []
        if not files:
            # スナップショット系はフォルダ粒度の情報がない場合があるのでスキップ
            continue
        top_folders = {p.split("/", 1)[0] if "/" in p else p for p in files}
        for tf in top_folders:
            folder_events[tf].append((dt, et))

    plt.figure(figsize=(12, 6))
    color_map = {
        "file_created": "tab:green",
        "file_modified": "tab:blue",
        "file_deleted": "tab:red",
        "export_generated": "tab:orange",
        "diff_summary": "tab:purple",
        "snapshot": "tab:gray",
        "genesis": "tab:gray",
        "unknown": "tab:brown"
    }
    for idx, (folder, evs) in enumerate(sorted(folder_events.items())):
        evs = sorted(evs, key=lambda x: x[0])
        dates = [e[0] for e in evs]
        types = [e[1] for e in evs]
        plt.scatter(dates, [idx]*len(dates),
                    c=[color_map.get(t, "tab:brown") for t in types], alpha=0.8, edgecolors="k", linewidths=0.3)
    plt.gca().xaxis.set_major_locator(mdates.MonthLocator())
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    plt.yticks(range(len(folder_events)), [k for k,_ in sorted(folder_events.items())])
    plt.title("フォルダ進化マップ")
    plt.grid(axis="x", linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.show()

    # ---- フォルダ別活動ヒートマップ（月次件数） ----
    from collections import Counter
    folder_month = defaultdict(Counter)
    for r in rows:
        dt = to_dt(r.get("timestamp", ""))
        if not dt: continue
        files = r.get("files_changed") or []
        month = dt.strftime("%Y-%m")
        for p in files:
            top = p.split("/", 1)[0] if "/" in p else p
            folder_month[top][month] += 1
    if folder_month:
        df = pd.DataFrame(folder_month).T.fillna(0).astype(int)
        plt.figure(figsize=(12, max(4, 0.3*len(df))))
        plt.imshow(df, aspect="auto")
        plt.title("フォルダ別活動ヒートマップ（イベント数/月）")
        plt.yticks(range(len(df.index)), df.index)
        plt.xticks(range(len(df.columns)), df.columns, rotation=90)
        plt.colorbar(label="件数")
        plt.tight_layout()
        plt.show()

if __name__ == "__main__":
    main()
