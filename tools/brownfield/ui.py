"""brownfield orchestrator Gradio UI（build_ui / auto_launch_with_increment / try_build_dir_picker）。

旧 brownfield_orchestrator.py (commit 8e39d984 時点) L235-238（try_build_dir_picker）
+ L318-431（build_ui）+ L432-443（auto_launch_with_increment）をロジック不改で転記。
変更点は import 文の再編成のみ。

★重要: gradio 関連 import（`import gradio as gr`, `from gradio import FileExplorer`）は
すべて関数内 import のまま保持。module-level に上げると lazy __init__.__getattr__ の意味が
なくなり `import brownfield` で gradio が読み込まれる（test_import_brownfield_does_not_load_gradio 壊れる）。
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import List

from .core import run_brownfield_stream
from .utils import (
    detect_latest_snapshot,
    is_orchestrator_importable,
    run_orchestrator_cli,
    run_orchestrator_func,
    ORCHESTRATOR_MODULE_NAME,   # ★ build_ui._kick_orchestrator が参照（計画書 import リストから追加）
    PICKER_ROOT,
    PHASE_KEYS,
    DEFAULT_PROFILES,
    DEFAULT_OUT,
)


# ---------- UI ---------------------------------------------------------------
def try_build_dir_picker():
    try: from gradio import FileExplorer; return FileExplorer
    except Exception: return None

def build_ui():
    import gradio as gr
    FileExplorer = try_build_dir_picker()
    with gr.Blocks(title="Brownfield Orchestrator — One-click UI", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🧰 Brownfield Orchestrator — One-click UI (All-in)")
        with gr.Tabs():
            with gr.TabItem("1. スナップショット作成"):
                gr.Markdown("既存システムの **構造 & 履歴の見える化** をワンクリックで実行し、成果物を保存・ZIPダウンロードできます。")
                with gr.Row():
                    with gr.Column(scale=1):
                        if FileExplorer:
                            picker = FileExplorer(label="解析対象プロジェクト（フォルダ/ファイル複数選択可）", root_dir=str(PICKER_ROOT), file_count="multiple")
                            project_root_tb = gr.Textbox(label="最終的に解析されるルート（自動計算/手動修正可）", value=str(PICKER_ROOT), lines=1)
                            def _sync_picker(selection):
                                from pathlib import Path; import os as _os
                                if not selection: return str(PICKER_ROOT)
                                _ps = [Path(p).resolve() for p in selection if p]
                                if not _ps: return str(PICKER_ROOT)
                                return str(Path(_os.path.commonpath([str(p if p.is_dir() else p.parent) for p in _ps])))
                            picker.change(_sync_picker, inputs=picker, outputs=project_root_tb)
                        else: project_root_tb = gr.Textbox(label="解析対象プロジェクトのルートパス（手入力）", value=str(PICKER_ROOT), lines=1)
                        out_root = gr.Textbox(label="スナップショット出力先（親フォルダ）", value=str(DEFAULT_OUT), lines=1)
                        with gr.Accordion("詳細設定", open=False):
                            richness_dd = gr.Dropdown(label="収集モード (Code Richness)", choices=["Light (fast)", "Code-Rich (more .py)"], value="Light (fast)", info="収集するソースコードの量を調整します。")
                            full_archive_cb = gr.Checkbox(label="ソースコード全体のアーカイブを含める (_source_archive.zip)", value=False, info="リポジトリ全体の完全なコピーをZIPで同梱します。")
                            profiles_text = gr.Textbox(label="AIエクスポート プロフィール(カンマ区切り)", value=",".join(DEFAULT_PROFILES), info="例: gemini-single-file,gpt5-zip")
                            phases = gr.CheckboxGroup(choices=PHASE_KEYS, value=PHASE_KEYS, label="実行するフェーズ（未選択はスキップ）")
                            gr.Markdown("### ポリシー・メタ（manifest に注入）")
                            policy_profile = gr.Textbox(label="policy_profile", placeholder="例: enterprise_finance（未入力なら自動検出 or general）")
                            policy_version = gr.Textbox(label="policy_version", placeholder="例: v1.3")
                            policy_icon = gr.Textbox(label="policy_icon", placeholder="例: 🏦")
                        run_btn = gr.Button("▶ 解析を実行", variant="primary")
                    with gr.Column(scale=1):
                        log_box = gr.Textbox(label="実行ログ（逐次）", lines=22)
                        summary_md = gr.Markdown(label="スナップショット概要", value="準備OK。パラメータを設定して実行してください。")
                        dl_btn = gr.DownloadButton(label="⬇ ZIPをダウンロード", value=None, visible=False)
            with gr.TabItem("2. 自動化サイクル実行"):
                gr.Markdown("### 🚀 自動化サイクル (Orchestrator 実行)")
                gr.Markdown("最新のスナップショットをベースラインとして、`nexuscore.core.orchestrator` モジュールを実行します。")
                with gr.Row():
                    with gr.Column(scale=1):
                        run_mode = gr.Radio(choices=["CLI (-m)", "Function (import)"], value="CLI (-m)", label="Run mode", info="モジュールとして実行します。まずはCLI推奨。")
                        fallback_cb = gr.Checkbox(label="CLI実行失敗時にFunctionモードへ自動フォールバック", value=True, info="モジュールが見つからない場合、Functionモードで再試行します。")
                        autonomy_dd = gr.Dropdown(label="Autonomy Level", choices=["0", "1", "2", "3", "4"], value="2", info="エージェントの自律度。2以上でブランチ作成や自動コミットが有効化されます。")
                        budget_tb = gr.Textbox(label="Budget (USD)", value="1.0")
                        branch_presets = ["feature/nx-{date}-{slug}", "chore/nx-{date}-{slug}", "hotfix/nx-{date}-{slug}", "ai-patch-{YYYYMMDD}", "カスタム..."]
                        branch_dd = gr.Dropdown(label="Branch name", choices=branch_presets, value=branch_presets[0], info="自動コミット時に使用するブランチ名の形式。")
                        branch_tb = gr.Textbox(visible=False, placeholder="カスタムブランチ名を入力")
                        def _toggle_branch_tb(selection): return gr.update(visible=(selection == "カスタム..."))
                        branch_dd.change(_toggle_branch_tb, inputs=branch_dd, outputs=branch_tb)
                        qg_presets = {"Balanced (推奨)": "test-coverage>=80,pylint>=8.0,mypy=clean", "Strict": "test-coverage>=90,pylint>=8.5,mypy=clean", "Fast Iteration": "test-coverage>=60,pylint>=7.0,mypy=warn", "カスタム...": "custom"}
                        qg_dd = gr.Dropdown(label="Quality Gates", choices=list(qg_presets.keys()), value="Balanced (推奨)", info="コード品質の自動チェック基準。")
                        qg_tb = gr.Textbox(visible=False, placeholder="例: test-coverage>=80,security-scan=ok")
                        def _toggle_qg_tb(selection): return gr.update(visible=(selection == "カスタム..."))
                        qg_dd.change(_toggle_qg_tb, inputs=qg_dd, outputs=qg_tb)
                        pol_override = gr.Textbox(label="Policy Profile (Override)", placeholder="例: security_focused_v2", info="manifest内の値を上書きする場合に指定。空欄は既存値に従います。")
                        run_cycle_btn = gr.Button("▶ 自動化サイクルを実行", variant="primary")
                    with gr.Column(scale=1):
                        log_box_cycle = gr.Textbox(label="実行ログ（逐次）", lines=20)
        def _run_snapshot(project_root: str, profiles_csv: str, selected_phases: List[str], out_root_dir: str, p_prof: str, p_ver: str, p_icon: str, richness: str, full_archive: bool):
            profiles = [s.strip() for s in (profiles_csv or "").split(",") if s.strip()]
            gen = run_brownfield_stream(project_root, out_root_dir, profiles, selected_phases, p_prof, p_ver, p_icon, richness, full_archive)
            if gen is None: yield "エラー: 解析プロセスの初期化に失敗しました。", "処理失敗", None, None; return
            for log_inc, summary, zip_path in gen: yield log_inc, (summary or gr.update()), (zip_path or None), (bool(zip_path) and zip_path or None)
        run_btn.click(fn=_run_snapshot, inputs=[project_root_tb, profiles_text, phases, out_root, policy_profile, policy_version, policy_icon, richness_dd, full_archive_cb], outputs=[log_box, summary_md, gr.State(), dl_btn])
        def _kick_orchestrator(out_root_dir: str, autonomy: str, budget: str, branch_dd_val: str, branch_tb_val: str, qg_dd_val: str, qg_tb_val: str, policy_override: str, mode: str, auto_fallback: bool):
            log_buf = []; emit = lambda line: log_buf.append(line) or "".join(log_buf)
            def tee_emit(line: str):
                print(line, end='', flush=True)
                return emit(line)
            def tee_emit_and_run(runner_gen):
                for line in runner_gen: yield tee_emit(line)

            latest = detect_latest_snapshot(out_root_dir)
            if not latest:
                yield tee_emit("[orchestrator] 最新スナップショットが見つかりません。先に解析を実行してください。\n"); return

            yield tee_emit(f"最新スナップショット: {latest}\n")
            manifest_path = Path(latest) / "manifest.json"; policy_from_manifest = ""
            try:
                if manifest_path.exists(): policy_from_manifest = str(json.loads(manifest_path.read_text(encoding="utf-8")).get("policy_profile", ""))
            except Exception: pass
            policy_final = (policy_override or policy_from_manifest or "").strip()
            yield tee_emit(f"使用するポリシープロファイル: {policy_final or '(default)'}\n")
            branch_final = branch_tb_val if branch_dd_val == "カスタム..." else branch_dd_val
            yield tee_emit(f"ブランチ名形式: {branch_final}\n")
            qg_final = qg_tb_val if qg_dd_val == "カスタム..." else qg_presets.get(qg_dd_val, "")
            yield tee_emit(f"品質ゲート: {qg_final}\n\n")

            runner = None
            importable = is_orchestrator_importable()

            if mode.startswith("CLI"):
                if importable:
                    runner = run_orchestrator_cli
                elif auto_fallback:
                    yield tee_emit(f"診断: CLIモード(-m)が選択されましたが、モジュール '{ORCHESTRATOR_MODULE_NAME}' が見つかりません。\n"
                                 f"-> 自動フォールバックが有効なため、Functionモードで実行します。\n\n")
                    runner = run_orchestrator_func
                else:
                    yield tee_emit(f"診断: CLIモード(-m)が選択されましたが、モジュール '{ORCHESTRATOR_MODULE_NAME}' が見つかりません。\n"
                                 f"-> 自動フォールバックが無効なため、処理を中止します。\n")
                    return
            else: # Function mode
                runner = run_orchestrator_func

            if runner:
                yield from tee_emit_and_run(runner(latest, autonomy, budget, branch_final, qg_final, policy_final))
            else: # Should not happen
                yield tee_emit("[FATAL] 実行モードを決定できませんでした。\n")

        run_cycle_btn.click(fn=_kick_orchestrator, inputs=[out_root, autonomy_dd, budget_tb, branch_dd, branch_tb, qg_dd, qg_tb, pol_override, run_mode, fallback_cb], outputs=log_box_cycle)
    return demo

def auto_launch_with_increment(demo, base_port: int, share: bool):
    max_tries = 20
    for i in range(max_tries + 1):
        port = base_port + i
        try:
            demo.queue().launch(server_name="0.0.0.0" if share else "127.0.0.1", server_port=port, share=share, prevent_thread_lock=False)
            print(f"[UI] Launched at http://127.0.0.1:{port} (share={share})"); return
        except OSError as e:
            if "Address already in use" in str(e): print(f"[UI] Port {port} in use. Trying next..."); continue
            raise
    raise RuntimeError(f"Failed to launch UI after {max_tries} increments from base port {base_port}.")
