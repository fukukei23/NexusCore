"""
self_healing_dashboard.py

NexusCore Self-Healing Code Review の実行履歴を可視化する
簡易 Streamlit ダッシュボード。

起動例:
    streamlit run -m nexuscore.ui.self_healing_dashboard -- --project-root /path/to/project
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import streamlit as st


def load_history(project_root: str) -> list[dict[str, Any]]:
    """
    .nexus/history/self_healing.log.jsonl を読み込んで list[dict] として返す。
    """
    path = Path(project_root) / ".nexus" / "history" / "self_healing.log.jsonl"
    if not path.exists():
        return []

    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except Exception:
                continue
    return records


def main(project_root: str = ".") -> None:
    st.set_page_config(
        page_title="NexusCore Self-Healing Dashboard",
        layout="wide",
    )
    st.title("NexusCore Self-Healing Dashboard")

    records = load_history(project_root)
    st.caption(f"Project root: {Path(project_root).resolve()}")
    st.write(f"Total self-healing runs logged: **{len(records)}**")

    if not records:
        st.info("No self-healing runs found yet. Run SelfHealingService first.")
        return

    # --------------------------------------------------------------
    # サイドバー: フィルタ
    # --------------------------------------------------------------
    statuses = sorted(set(r.get("status", "unknown") for r in records))
    repos = sorted(
        set(r.get("repo_full_name", "unknown") for r in records if r.get("repo_full_name"))
    )

    st.sidebar.header("Filters")
    selected_statuses = st.sidebar.multiselect(
        "Status",
        options=statuses,
        default=statuses,
    )
    selected_repos = st.sidebar.multiselect(
        "Repository",
        options=repos,
        default=repos,
    )

    filtered = [
        r
        for r in records
        if r.get("status", "unknown") in selected_statuses
        and (r.get("repo_full_name") or "unknown") in selected_repos
    ]

    st.write(f"Filtered runs: **{len(filtered)}**")

    # --------------------------------------------------------------
    # ステータス集計
    # --------------------------------------------------------------
    st.subheader("Status Summary")
    counter = Counter(r.get("status", "unknown") for r in filtered)
    col1, col2 = st.columns(2)

    with col1:
        st.write("Counts")
        st.json(counter)

    with col2:
        # 簡易円グラフ
        labels = list(counter.keys())
        values = [counter[k] for k in labels]
        try:
            import pandas as pd

            df = pd.DataFrame({"status": labels, "count": values})
            st.bar_chart(df.set_index("status"))
        except Exception:
            st.write("Bar chart not available (pandas not installed).")

    # --------------------------------------------------------------
    # 最近の実行一覧
    # --------------------------------------------------------------
    st.subheader("Recent Runs")

    # 新しいものが後ろに追加されている前提で、末尾から N 件を表示
    N = 30
    recent = list(reversed(filtered[-N:]))

    for r in recent:
        with st.expander(
            f"[{r.get('status', 'unknown')}] "
            f"{r.get('repo_full_name', '')} "
            f"PR #{r.get('pr_number', '')} "
            f"(run_id={r.get('run_id', '-')})"
        ):
            st.write(f"**Summary**: {r.get('summary', '')}")
            st.write(f"**Session ID**: `{r.get('session_id', '')}`")
            st.write(f"**Head SHA**: `{r.get('head_sha', '')}`")
            st.write(f"**Started**: {r.get('started_at', '')}")
            st.write(f"**Finished**: {r.get('finished_at', '')}")

            details = r.get("details", {})
            if details:
                st.write("**Details (raw)**")
                st.json(details)

            # diffプレビューが markdown で入っていればそのまま表示
            patch_md = details.get("patch_preview") or details.get("patch_preview_markdown")
            if patch_md:
                st.markdown("**Patch Preview**")
                st.markdown(patch_md)

    st.caption("Showing up to 30 recent runs.")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="NexusCore Self-Healing Dashboard")
    parser.add_argument(
        "--project-root",
        type=str,
        default=".",
        help="NexusCore プロジェクトのルートディレクトリ（.nexus/history 配下にログがある前提）",
    )
    return parser.parse_args()


if __name__ == "__main__":
    import os
    import sys

    # 環境変数から取得を試みる（スクリプト起動時に対応）
    project_root = os.getenv("NEXUS_PROJECT_ROOT", ".")

    # コマンドライン引数がある場合は優先
    if len(sys.argv) > 1:
        args = _parse_args()
        project_root = args.project_root

    main(project_root)
