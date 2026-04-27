# ==============================================================================
# ファイル名: repair_timeline.py
# レジストリ: src/nexuscore/gradio_app/
# 日付・時刻(JST): 2025-09-09 00:00:00
# バージョン: 2.7J  ※完全置換・構文零・保守性向上版
#
# 概要:
#   - patch_history/*.json を読み込み自己修復タイムラインを可視化
#   - policy_profile / policy_version / policy_icon をバッジ表示
#   - KPI（成功率・連勝連敗・カテゴリ分布）＋Markdown-diff 表示
#   - JST 統一・ポート衝突時自動回避・Gradio v4 対応
#
# 使用方法:
#   (.venv) PS C:\...\NexusCore> python -m src.nexuscore.gradio_app.repair_timeline
#   ブラウザが自動で開き http://127.0.0.1:7861 （空きポートを自動探索）
#
# 必要環境:
#   - Python 3.10 以上
#   - Gradio 4.7+
#   - pytest（テストログ表示用）
# ==============================================================================

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import gradio as gr

# ---------- パス ----------
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

JST = timezone(timedelta(hours=9))


# ---------- 入出力 ----------
def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[RepairTimeline][WARN] Failed to read {path}: {e}")
        return {}


def _collect_items(limit: int | None, date_filter: str) -> list[dict[str, Any]]:
    files: list[Path] = []
    for d in PATCH_HISTORY_DIRS:
        if d.exists():
            files.extend(d.glob("patch_*.json"))
    files.sort(key=lambda p: p.stem, reverse=True)
    if limit:
        files = files[:limit]

    now = datetime.now(JST)
    if date_filter == "today":
        start = datetime(now.year, now.month, now.day, tzinfo=JST)
    elif date_filter == "7days":
        start = now - timedelta(days=7)
    else:
        start = datetime(1970, 1, 1, tzinfo=JST)

    items: list[dict[str, Any]] = []
    for f in files:
        data = _read_json(f)
        ts = data.get("timestamp") or f.stem.replace("patch_", "")
        try:
            ts_dt = datetime.strptime(ts, "%Y%m%d_%H%M%S").replace(tzinfo=JST)
        except Exception:
            ts_dt = datetime(1970, 1, 1, tzinfo=JST)
        if ts_dt >= start:
            data["_file"] = str(f)
            items.append(data)
    items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return items


# ---------- 理由カテゴリ ----------
_REASON_RULES = [
    ("境界値/特例", ["n=0", "n=1", "edge", "boundary", "off-by-one", "<= 2", "< 2"]),
    ("アルゴリズム/計算量", ["O(", "two pointers", "binary search", "complexity"]),
    ("I/O・パス・環境", ["path", "windows", "encoding", "newline", "permission", "env"]),
    ("テスト修正/品質", ["test", "pytest", "assert", "fixture"]),
    ("設計/仕様", ["spec", "仕様", "contract", "interface"]),
]


def _categorize_reason(text: str) -> str:
    t = (text or "").lower()
    for name, keys in _REASON_RULES:
        for k in keys:
            if k.lower() in t:
                return name
    return "不明"


def _compute_metrics(items: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(items)
    success = sum(1 for x in items if (x.get("status") or "").startswith("success"))
    attempts = sum(1 for x in items if (x.get("status") or "").startswith("attempt"))
    initial_pass = sum(1 for x in items if (x.get("status") or "") == "initial_pass")

    recent = items[:10]
    recent_success = sum(1 for x in recent if (x.get("status") or "").startswith("success"))
    recent_rate = (recent_success / max(1, len(recent))) * 100

    streak_win = streak_lose = 0
    for x in items:
        st = x.get("status") or ""
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
        elif st == "initial_pass":
            if streak_win > 0 or streak_lose > 0:
                break

    cats: dict[str, int] = {}
    for x in items:
        cats[_categorize_reason(x.get("reason") or x.get("summary") or "")] = (
            cats.get(_categorize_reason(x.get("reason") or x.get("summary") or ""), 0) + 1
        )

    return {
        "total": total,
        "success": success,
        "attempts": attempts,
        "initial_pass": initial_pass,
        "success_rate": (success / max(1, total)) * 100,
        "recent_success_rate": recent_rate,
        "streak_win": streak_win,
        "streak_lose": streak_lose,
        "categories": cats,
    }


# ---------- タイムライン行（policy バッジ対応） ----------
def _make_policy_badge(x: dict[str, Any]) -> str:
    prof = (x.get("policy_profile") or "").strip()
    ver = (x.get("policy_version") or "").strip()
    icon = (x.get("policy_icon") or "").strip()
    if not (prof or ver or icon):
        return ""
    if prof and ver and icon:
        return f"[{icon} {prof} {ver}]"
    if prof and icon:
        return f"[{icon} {prof}]"
    if prof and ver:
        return f"[{prof} {ver}]"
    return f"[{prof or ver or icon}]"


def build_timeline_rows(
    items: list[dict[str, Any]],
    pair_mode: bool,
    show_attempt: bool,
    show_success: bool,
    show_initial: bool,
) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for x in items:
        status = x.get("status", "unknown")
        if status.startswith("attempt") and not show_attempt:
            continue
        if status.startswith("success") and not show_success:
            continue
        if status == "initial_pass" and not show_initial:
            continue

        ts = x.get("timestamp", "N/A")
        ok = (
            "✅"
            if status.startswith("success")
            else ("❌" if status.startswith("attempt") else "🟡")
        )
        badge = _make_policy_badge(x)
        label = f"{ts} {ok} {status}" + (f" {badge}" if badge else "")
        rows.append((label, ts))

    if pair_mode:
        # 近接 attempt→success を隣接表示（分粒度ソート）
        def key_for_pair(lbl_ts: str) -> str:
            return (lbl_ts or "")[:13]

        rows.sort(
            key=lambda r: (key_for_pair(r[1]), "1" if " attempt" in r[0] else "2"), reverse=True
        )

    return rows


def _render_diff_md(diff_str: str | None) -> str:
    if not diff_str:
        return "> 差分はありません"
    return f"```diff\n{diff_str}\n```"


def pick_detail(ts_key: str, all_items: list[dict[str, Any]]):
    x = next((i for i in all_items if i.get("timestamp") == ts_key), None)
    if not x:
        return "", "", "", {}, "", "> 差分はありません"

    code = x.get("full_code_after") or x.get("code") or ""
    reason = x.get("reason") or "(none)"
    test_log = x.get("test_log") or ""
    meta = {
        "when": ts_key,
        "event": "patch_applied" if (x.get("status") or "").startswith("success") else "pytest",
        "status": x.get("status"),
        "source_patch_file": x.get("_file", ""),
        "policy_profile": x.get("policy_profile"),
        "policy_version": x.get("policy_version"),
        "policy_icon": x.get("policy_icon"),
        "prompt_excerpt": (x.get("llm_prompt") or x.get("prompt") or "(none)")[:160],
    }
    diff_md = _render_diff_md(x.get("code_diff") or "")
    return code, reason, test_log, meta, "", diff_md


# ---------- Gradio UI ----------
def build_ui():
    with gr.Blocks(title="Self-Healing Timeline (JST)", theme=gr.themes.Soft()) as demo:
        gr.Markdown(
            "## 🔄 Self-Healing Timeline — 失敗 → 自己修復 → 成功 → 知識化\n"
            "左のタイムラインをクリックすると、右側に **修正コード / 修正理由 / テストログ / メタ情報 / FKB一致 / Diff** を展開します。\n\n"
            f"**現時刻(JST)**: {datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')}"
        )

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 表示範囲")
                range_sel = gr.Radio(
                    choices=["latest10", "latest20", "today", "7days", "all"],
                    value="latest10",
                    label="最新10/20件、今日、直近7日、全件から選択",
                )

                gr.Markdown("### 状態フィルタ")
                ck_attempt = gr.Checkbox(value=True, label="失敗(attempt)")
                ck_success = gr.Checkbox(value=True, label="成功(success)")
                ck_initial = gr.Checkbox(value=True, label="初回成功(initial)")
                pair_mode = gr.Checkbox(value=False, label="ペア結合表示（失敗+成功を1行に畳む）")

                reload_btn = gr.Button("🔁 再読み込み", variant="secondary")
                sources_box = gr.Markdown("")

            with gr.Column(scale=2):
                gr.Markdown("### 📈 メトリクス")
                kpi_md = gr.Markdown("")
                cat_df = gr.Dataframe(
                    headers=["カテゴリ", "件数"],
                    datatype=["str", "number"],
                    value=[],
                    interactive=False,
                    label="修正理由カテゴリ分布",
                    wrap=True,
                )

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### タイムライン（新しい順）")
                tl = gr.Radio(choices=[], value=None, label=None, interactive=True)
            with gr.Column(scale=2):
                with gr.Tabs():
                    with gr.TabItem("💻 修正コード"):
                        code_view = gr.Code(label="修正コード", language="python", lines=22)
                    with gr.TabItem("📝 修正理由"):
                        reason_view = gr.Textbox(
                            label="修正理由・要約", lines=12, interactive=False, container=False
                        )
                    with gr.TabItem("🧪 テストログ"):
                        testlog_view = gr.Textbox(
                            label="pytest log", lines=22, interactive=False, container=False
                        )
                    with gr.TabItem("ℹ️ メタ情報"):
                        meta_view = gr.JSON(label="メタ情報")
                    with gr.TabItem("📚 FKBマッチ"):
                        fkb_view = gr.Markdown("(FKB連携は将来拡張予定)")
                    with gr.TabItem("🧩 Diff"):
                        diff_view = gr.Markdown(label="Unified Diff")

        store = gr.Textbox(visible=False)

        # -------- イベント --------
        def _load(range_sel_v: str, a: bool, s: bool, i: bool, pair: bool):
            limit, date_filter = None, "all"
            if range_sel_v == "latest10":
                limit = 10
            elif range_sel_v == "latest20":
                limit = 20
            elif range_sel_v == "today":
                date_filter = "today"
            elif range_sel_v == "7days":
                date_filter = "7days"

            items = _collect_items(limit, date_filter)
            m = _compute_metrics(items)
            kpi = (
                f"- **総イベント**: {m['total']} | **成功**: {m['success']} | "
                f"**失敗(試行)**: {m['attempts']} | **初回成功**: {m['initial_pass']}\n"
                f"- **成功率**: {m['success_rate']:.1f}% | **直近10件成功率**: {m['recent_success_rate']:.1f}% | "
                f"**平均試行/成功**: {(m['attempts']/max(1,m['success'])):.2f}\n"
                f"- **連勝**: {m['streak_win']} | **連敗**: {m['streak_lose']}"
            )
            cat_rows = [
                [k, v] for k, v in sorted(m["categories"].items(), key=lambda x: (-x[1], x[0]))
            ]

            rows = build_timeline_rows(items, pair, a, s, i)
            choices = [lab for lab, _ in rows]
            tl_upd = gr.update(choices=choices, value=(choices[0] if choices else None))

            srcs_msg = "Sources: " + " / ".join(
                f"{str(d)}: {len(list(d.glob('patch_*.json')))} file(s)"
                for d in PATCH_HISTORY_DIRS
                if d.exists()
            )
            return tl_upd, kpi, cat_rows, srcs_msg, json.dumps(items, ensure_ascii=False)

        def _pick(label: str, blob: str):
            if not label or not blob:
                return "", "", "", {}, "", "> 差分はありません"
            ts_key = label.split()[0]
            try:
                items = json.loads(blob)
            except Exception:
                items = []
            return pick_detail(ts_key, items)

        def _initial():
            tl_u, kpi, cats, srcs, blob = _load("latest10", True, True, True, False)
            if tl_u.get("value"):
                code, reason, log, meta, fkb, diff = _pick(tl_u["value"], blob)
            else:
                code = reason = log = ""
                meta, fkb, diff = {}, "", "> 差分はありません"
            return tl_u, kpi, cats, srcs, blob, code, reason, log, meta, fkb, diff

        demo.load(
            _initial,
            inputs=None,
            outputs=[
                tl,
                kpi_md,
                cat_df,
                sources_box,
                store,
                code_view,
                reason_view,
                testlog_view,
                meta_view,
                fkb_view,
                diff_view,
            ],
        )

        reload_btn.click(
            _load,
            inputs=[range_sel, ck_attempt, ck_success, ck_initial, pair_mode],
            outputs=[tl, kpi_md, cat_df, sources_box, store],
        )

        tl.change(
            _pick,
            inputs=[tl, store],
            outputs=[code_view, reason_view, testlog_view, meta_view, fkb_view, diff_view],
        )

        for c in [range_sel, ck_attempt, ck_success, ck_initial, pair_mode]:
            c.change(
                _load,
                inputs=[range_sel, ck_attempt, ck_success, ck_initial, pair_mode],
                outputs=[tl, kpi_md, cat_df, sources_box, store],
            )

    return demo


def launch_timeline_ui():
    demo = build_ui()
    # ポート7861が使用中なら自動で別ポートを探す
    try:
        demo.queue().launch(server_name="127.0.0.1", server_port=7861, share=False)
    except OSError:
        demo.queue().launch(server_name="127.0.0.1", server_port=None, share=False)


if __name__ == "__main__":
    launch_timeline_ui()
