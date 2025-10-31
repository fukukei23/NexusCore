# -*- coding: utf-8 -*-
# File: tools/nexus_export_ui.py
# Version: all-py-first v7.3.3 (UI)
# Date: 2025-08-29
# Purpose: Minimal web UI to drive code_export_gemini_fixed without subprocess encoding issues
# Requirements:
#   pip install gradio==4.* (or compatible)
#   Python 3.10+ recommended
#
# Usage:
#   python tools/nexus_export_ui.py
#   ブラウザで http://127.0.0.1:7868 を開き、プロファイルを選択して実行
#
# Notes:
# - 直接モジュール関数を呼び出し、stdout を捕捉してログ表示します
# - “.venv / exports / logs / 現行 manifest” の除外は CLI と同等です
# - Gemini(≤10MB), GPT-5(≤50MB), Custom の 3プロファイルをサポート
# - ログのファイル保存は code_export_gemini_fixed.py 側が行います

from __future__ import annotations
import io
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import gradio as gr

# 依存モジュール（同一リポジトリ内）
import importlib
export_mod = importlib.import_module("tools.code_export_gemini_fixed")  # noqa

DEFAULT_EXPORTS = str((Path(__file__).resolve().parent.parent / "exports").resolve())
DEFAULT_LOGS    = str((Path(__file__).resolve().parent.parent / "logs").resolve())

PROFILES = {
    "Gemini (≤10MB)": ("gemini-10", 9.5),
    "GPT-5  (≤50MB)": ("gpt5-50", 49.5),
    "Custom":         ("custom", 24.0),
}

def _capture_stdout(fn, *args, **kwargs) -> str:
    """Capture stdout (UTF-8 safe) while calling fn(*args, **kwargs)."""
    buf = io.StringIO()
    old = sys.stdout
    try:
        sys.stdout = buf
        fn(*args, **kwargs)
    finally:
        sys.stdout = old
    return buf.getvalue()

def run_export(roots_text: str, profile_label: str, target_mb: float, max_files: int,
               emit_zip: bool, emit_folder: bool, dry_run: bool,
               exports_dir: str, logs_dir: str):
    """UI から呼ばれる実行関数。code_export_gemini_fixed.export_main を直呼び。"""
    profile_key, default_target = PROFILES.get(profile_label, ("gemini-10", 9.5))
    # target_mb が 0/負値ならプロファイル既定値を使う
    target_val = float(target_mb) if target_mb and target_mb > 0 else float(default_target)

    # roots: 改行/カンマ/スペースのゆるい区切りを許容
    raw = (roots_text or "").replace("\r", "\n").replace(",", " ")
    roots = [r for r in raw.split() if r.strip()]
    if not roots:
        roots = [str(Path(".").resolve())]

    # argparse.Namespace 互換のオブジェクトを組み立てる
    ns = SimpleNamespace(
        roots=roots,
        profile=profile_key,
        target_mb=target_val,
        max_files=int(max_files or 5000),
        emit_zip=bool(emit_zip),
        emit_folder=bool(emit_folder),
        dry_run=bool(dry_run),
        exports_dir=exports_dir or DEFAULT_EXPORTS,
        logs_dir=logs_dir or DEFAULT_LOGS,
    )

    # 実行＆ログ捕捉
    try:
        out_text = _capture_stdout(export_mod.export_main, ns)
    except Exception as e:
        out_text = f"[UI Error] {e}"

    # 直近のログを推定して提示（存在すれば）
    logs_path = Path(ns.logs_dir)
    latest = ""
    try:
        if logs_path.exists():
            cands = sorted(logs_path.glob("NexusCore_export_*_*.txt"))
            if cands:
                latest = str(cands[-1].resolve())
    except Exception:
        pass

    # 可能な出力先も推定（存在すれば）
    exports_path = Path(ns.exports_dir)
    latest_zip = ""
    latest_manifest = ""
    try:
        if exports_path.exists():
            zips = sorted(exports_path.glob(f"NexusCore_{ns.profile.replace('-','')}*.zip"))
            mans = sorted(exports_path.glob("NexusCore_manifest_*"))
            if zips:
                latest_zip = str(zips[-1].resolve())
            if mans:
                latest_manifest = str(mans[-1].resolve())
    except Exception:
        pass

    summary = []
    if latest_manifest:
        summary.append(f"[Manifest] {latest_manifest}")
    if latest_zip:
        summary.append(f"[ZIP]      {latest_zip}")
    if latest:
        summary.append(f"[Log]      {latest}")
    if not summary:
        summary.append("(出力先の検出なし。ドライランか、フィルタにより無出力の可能性)")

    # 画面表示
    return "\n".join(summary), out_text

def _profile_changed(lbl: str):
    key, tgt = PROFILES.get(lbl, ("gemini-10", 9.5))
    return gr.update(value=tgt)

with gr.Blocks(theme=gr.themes.Soft(), title="Nexus Export UI", css="footer{display:none}") as demo:
    gr.Markdown("## Nexus Export UI — Gemini/GPT-5/Custom")

    with gr.Row():
        profile = gr.Dropdown(choices=list(PROFILES.keys()), value="Gemini (≤10MB)", label="プロファイル")
        target  = gr.Number(value=9.5, precision=1, label="Target MB (編集可)")
        maxf    = gr.Number(value=5000, precision=0, label="Max Files (scan cap)")

    with gr.Row():
        roots   = gr.Textbox(value=str(Path('.').resolve()), label="Roots (空白/改行/カンマ区切りOK)", lines=2)
    with gr.Row():
        emit_zip    = gr.Checkbox(value=True, label="ZIP を出力")
        emit_folder = gr.Checkbox(value=True, label="フォルダ(Manifest)を出力")
        dry_run     = gr.Checkbox(value=False, label="ドライラン（プレビューのみ）")

    with gr.Row():
        exports_dir = gr.Textbox(value=DEFAULT_EXPORTS, label="exports 出力先")
        logs_dir    = gr.Textbox(value=DEFAULT_LOGS, label="logs 出力先")

    run_btn  = gr.Button("実行", variant="primary")
    prev_btn = gr.Button("プレビュー（ドライラン）")

    summary = gr.Textbox(label="直近の出力（推定）", lines=3)
    logbox  = gr.Textbox(label="ログ", lines=22)

    run_btn.click(
        fn=run_export,
        inputs=[roots, profile, target, maxf, emit_zip, emit_folder, gr.State(False), exports_dir, logs_dir],
        outputs=[summary, logbox]
    )
    prev_btn.click(
        fn=run_export,
        inputs=[roots, profile, target, maxf, gr.State(False), gr.State(False), gr.State(True), exports_dir, logs_dir],
        outputs=[summary, logbox]
    )
    profile.change(_profile_changed, inputs=[profile], outputs=[target])

if __name__ == "__main__":
    # Windows PowerShell 利用時の文字化けを避けたい場合:
    #   $env:PYTHONIOENCODING="utf-8"
    demo.launch(server_name="127.0.0.1", server_port=7868, show_error=True)
