# ==============================================================================
# ファイル名: dashboard.py
# レジストリ: src/nexuscore/gradio_app/
# バージョン: 1.1 (Agg backend / 起動オプション拡張)
# 日付: 2025-09-12 00:00 (JST)
#
# 使い方:
#   # 標準起動（ポート:7860）
#   (.venv) PS C:\...\NexusCore> python -m src.nexuscore.gradio_app.dashboard
#
#   # オプション:
#   #  - ポート変更: 環境変数 NEXUS_DASHBOARD_PORT=7890
#   #  - 共有リンク: 環境変数 NEXUS_DASHBOARD_SHARE=1
#   #  - Matplotlibバックエンド: デフォルトで Agg 指定済（Tk不要）
#
# 概要:
#   patch_history/*.json を集計し、成功率/平均試行回数/直近成功率/連勝・連敗/
#   カテゴリ分布/日次推移をカード＆図で可視化。詳細掘りは repair_timeline.py へ。
# ==============================================================================

from __future__ import annotations

# --- Matplotlib を Tk 非依存化（Gradio と相性◎） ------------------------------
import os
os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib
matplotlib.use("Agg")
import atexit

# -----------------------------------------------------------------------------
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta, date

import gradio as gr
import matplotlib.pyplot as plt

plt.ioff()  # 対話モードOFF（描画はFigure返却ベース）
atexit.register(lambda: plt.close("all"))  # プロセス終了時に安全クローズ

# ====== パス設定 ===============================================================
HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[3]
OUTPUT_ROOT = PROJECT_ROOT / "output"
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
PATCH_HISTORY_ROOT = Path(os.getenv("NEXUS_PATCH_HISTORY_ROOT", OUTPUT_ROOT / "patch_history"))
PATCH_HISTORY_ROOT.mkdir(parents=True, exist_ok=True)
PATCH_HISTORY_DIRS = [
    PATCH_HISTORY_ROOT,
    PROJECT_ROOT / "patch_history",
    PROJECT_ROOT / "src" / "patch_history",
    PROJECT_ROOT / "src" / "src" / "nexuscore" / "gradio_app" / "patch_history",
]

# ====== ユーティリティ =========================================================
def _parse_ts(ts: str) -> datetime:
    for fmt in ("%Y%m%d_%H%M%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(ts, fmt)
        except Exception:
            pass
    return datetime(1970, 1, 1)

def _read_json(f: Path) -> Dict[str, Any]:
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _collect_files() -> List[Path]:
    files: List[Path] = []
    for d in PATCH_HISTORY_DIRS:
        if d.exists():
            files.extend(d.glob("patch_*.json"))
    return sorted(files, key=lambda p: p.stem, reverse=True)

def _load_items(limit: int | None, date_filter: str) -> List[Dict[str, Any]]:
    files = _collect_files()
    if limit:
        files = files[:limit]

    now = datetime.now()
    if date_filter == "today":
        start = datetime(now.year, now.month, now.day)
    elif date_filter == "7days":
        start = now - timedelta(days=7)
    elif date_filter == "30days":
        start = now - timedelta(days=30)
    else:
        start = datetime(1970, 1, 1)

    items: List[Dict[str, Any]] = []
    for f in files:
        data = _read_json(f)
        ts = data.get("timestamp") or f.stem.replace("patch_", "")
        if _parse_ts(ts) >= start:
            data["_file"] = str(f)
            items.append(data)
    return sorted(items, key=lambda x: x.get("timestamp", ""), reverse=True)

# ====== カテゴリ判定（repair_timeline と揃える軽量版） =========================
_RULES: List[Tuple[str, List[str]]] = [
    ("境界値/特例", ["n=0", "n=1", "n=2", "edge", "boundary", "off-by-one", "<= 2", "< 2"]),
    ("アルゴリズム/計算量", ["two pointers", "binary search", "O(", "while i * i"]),
    ("I/O・パス・環境", ["path", "windows", "encoding", "permission", "ENV"]),
    ("テスト修正/品質", ["test", "pytest", "assert", "fixture"]),
    ("設計/仕様", ["spec", "仕様", "contract", "interface"]),
]
def _categorize(text: str) -> str:
    t = (text or "").lower()
    for name, keys in _RULES:
        for k in keys:
            if k.lower() in t:
                return name
    if "even numbers" in t or "handle n=2" in t:
        return "境界値/特例"
    return "不明"

# ====== 集計 ===================================================================
def _metrics(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(items)
    success = sum(1 for x in items if (x.get("status") or "").startswith("success"))
    attempts = sum(1 for x in items if (x.get("status") or "").startswith("attempt"))
    initial = sum(1 for x in items if (x.get("status") or "") == "initial_pass")

    recent = items[:10]
    recent_success = sum(1 for x in recent if (x.get("status") or "").startswith("success"))
    recent_rate = (recent_success / max(1, len(recent))) * 100

    # 連勝/連敗（新→旧）
    streak_win = streak_lose = 0
    for x in items:
        st = (x.get("status") or "")
        if st.startswith("success"):
            if streak_lose == 0:
                streak_win += 1
            else:
                break
        elif st.startswith("attempt"):
            if streak_win == 0:
                streak_lose += 1
            else:
                break
        else:
            if streak_win or streak_lose:
                break

    avg_attempts = attempts / max(1, success)

    # カテゴリ分布
    cats: Dict[str, int] = {}
    for x in items:
        c = _categorize(x.get("reason", "") or x.get("summary", ""))
        cats[c] = cats.get(c, 0) + 1

    # 日次推移
    by_day: Dict[date, Dict[str, int]] = {}
    for x in items:
        d = _parse_ts(x.get("timestamp", "")).date()
        st = (x.get("status") or "")
        bucket = by_day.setdefault(d, {"success": 0, "attempt": 0, "initial": 0})
        if st.startswith("success"):
            bucket["success"] += 1
        elif st.startswith("attempt"):
            bucket["attempt"] += 1
        elif st == "initial_pass":
            bucket["initial"] += 1

    return {
        "total": total,
        "success": success,
        "attempts": attempts,
        "initial": initial,
        "success_rate": (success / max(1, total)) * 100,
        "recent_success_rate": recent_rate,
        "avg_attempts_per_success": avg_attempts,
        "streak_win": streak_win,
        "streak_lose": streak_lose,
        "categories": cats,
        "by_day": dict(sorted(by_day.items(), key=lambda kv: kv[0])),
    }

# ====== 図作成 =================================================================
def _make_cat_plot(cats: Dict[str, int]):
    fig, ax = plt.subplots(figsize=(4, 3))
    if not cats:
        ax.text(0.5, 0.5, "カテゴリデータなし", ha="center", va="center")
        return fig
    labels = list(cats.keys())
    sizes = [cats[k] for k in labels]
    ax.pie(sizes, labels=labels, autopct="%1.0f%%", startangle=90)
    ax.axis("equal")
    ax.set_title("修正理由カテゴリ構成")
    return fig

def _make_daily_plot(by_day: Dict[date, Dict[str, int]]):
    fig, ax = plt.subplots(figsize=(6, 3))
    if not by_day:
        ax.text(0.5, 0.5, "日次データなし", ha="center", va="center")
        return fig
    days = list(by_day.keys())
    succ = [by_day[d]["success"] for d in days]
    attm = [by_day[d]["attempt"] for d in days]
    init = [by_day[d]["initial"] for d in days]
    ax.plot(days, succ, marker="o", label="success")
    ax.plot(days, attm, marker="o", label="attempt")
    ax.plot(days, init, marker="o", label="initial")
    ax.legend()
    ax.set_title("日次イベント推移")
    ax.set_xlabel("date")
    ax.set_ylabel("count")
    fig.autofmt_xdate()
    return fig

# ====== UI ====================================================================
def build_ui():
    with gr.Blocks(title="NexusCore — Self-Healing Dashboard", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 📊 NexusCore — Self-Healing Dashboard")
        gr.Markdown(
            "失敗→自己修復→成功→知識化の**進化メトリクス**を要約表示します。"
            "詳細はサイドの **Repair Timeline** を開いてください。"
        )

        with gr.Row():
            with gr.Column(scale=1):
                range_sel = gr.Radio(
                    choices=["latest10", "latest20", "today", "7days", "30days", "all"],
                    value="7days",
                    label="対象期間 / 件数",
                )
                reload_btn = gr.Button("🔁 再集計", variant="secondary")
                link_tl = gr.Markdown("[➡ Repair Timeline を開く](http://127.0.0.1:7861)", visible=True)
                srcs = gr.Markdown("")

            with gr.Column(scale=2):
                kpi = gr.Markdown("")  # KPIカード
                with gr.Row():
                    cat_plot = gr.Plot(label="カテゴリ構成")
                    day_plot = gr.Plot(label="日次推移")

        with gr.Row():
            table = gr.Dataframe(
                headers=["timestamp", "status", "reason_excerpt"],
                datatype=["str", "str", "str"],
                value=[],
                interactive=False,
                wrap=True,
                label="直近イベント（要約）",
            )

        def _load(range_sel: str):
            limit = None
            date_filter = "all"
            if range_sel == "latest10":
                limit = 10
            elif range_sel == "latest20":
                limit = 20
            elif range_sel in ("today", "7days", "30days"):
                date_filter = range_sel

            items = _load_items(limit, date_filter)
            m = _metrics(items)

            kpi_md = (
                f"**総イベント**: {m['total']}　"
                f"**成功**: {m['success']}　"
                f"**失敗(試行)**: {m['attempts']}　"
                f"**初回成功**: {m['initial']}  \n"
                f"**成功率**: {m['success_rate']:.1f}%　"
                f"**直近10件成功率**: {m['recent_success_rate']:.1f}%　"
                f"**平均試行/成功**: {m['avg_attempts_per_success']:.2f}　"
                f"**連勝**: {m['streak_win']}　**連敗**: {m['streak_lose']}"
            )

            fig_cat = _make_cat_plot(m["categories"])
            fig_day = _make_daily_plot(m["by_day"])

            rows = []
            for x in items[:10]:
                ts = x.get("timestamp", "")
                st = x.get("status", "")
                rs = (x.get("reason") or x.get("summary") or "")[:80]
                rows.append([ts, st, rs])

            src_text = "Sources: " + " / ".join(
                f"{str(d)}: {len(list(d.glob('patch_*.json')))} file(s)" for d in PATCH_HISTORY_DIRS
            )

            return kpi_md, fig_cat, fig_day, rows, src_text

        # 初回ロード
        kpi_text, fc, fd, rows, src_text = _load(range_sel.value)
        kpi.value = kpi_text
        cat_plot.value = fc
        day_plot.value = fd
        table.value = rows
        srcs.value = src_text

        reload_btn.click(_load, inputs=[range_sel], outputs=[kpi, cat_plot, day_plot, table, srcs])

    return demo

def main():
    import os
    port = int(os.getenv("NEXUS_DASHBOARD_PORT", "7860"))
    share = os.getenv("NEXUS_DASHBOARD_SHARE", "0") == "1"
    demo = build_ui()
    # ★ ブロックさせる（prevent_thread_lock を False か、引数自体を削除）
    demo.queue().launch(
        server_name="127.0.0.1",
        server_port=port,
        share=share,
        prevent_thread_lock=False,   # ← ここがポイント
        inbrowser=False,
    )

if __name__ == "__main__":
    main()
