"""
4.5: 統合 Gradio UI

「解析→修正→テスト→履歴」まで一画面で閉じるタブ構成
各タブは個別モジュールに分割済み:
  - code_prompt_tab.py
  - ai_revision_tab.py
  - test_runner_tab.py
  - history_diff_tab.py
"""

from __future__ import annotations

import gradio as gr

from ._state import AppState
from ._llm_init import HAS_LLM, HAS_SELF_HEALING, HAS_WHISPER, _router, transcribe_audio
from .ai_revision_tab import build_ai_revision_tab
from .test_runner_tab import build_test_runner_tab as _build_test_runner_tab


def run_test_handler(command: str, test_file: str, current_state: AppState):
    """Deprecated: use test_runner_tab.run_test_handler instead."""
    import subprocess
    import sys
    from pathlib import Path

    try:
        cmd = [sys.executable, "-m", "pytest", "-q"]
        if test_file and test_file.strip():
            cmd.append(test_file)
        result = subprocess.run(cmd, shell=False, capture_output=True, text=True, cwd=Path.cwd())
        output = result.stdout + result.stderr if result.stderr else result.stdout
        current_state.latest_test_result = output
        status_md = f"**ステータス:** {'✅ 成功' if result.returncode == 0 else '❌ 失敗'}\n\n**Return Code:** {result.returncode}"
        return output, status_md, current_state
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Test execution failed: {e}", exc_info=True)
        return f"❌ エラー: {e}", "**ステータス:** ❌ エラー", current_state
from .code_prompt_tab import build_code_prompt_tab
from .history_diff_tab import build_history_diff_tab
from .test_runner_tab import build_test_runner_tab


def build_unified_ui() -> gr.Blocks:
    """統合 Gradio UI を構築"""
    with gr.Blocks(title="NexusCore Unified UI") as demo:
        gr.Markdown("# NexusCore Unified UI")
        gr.Markdown("解析→修正→テスト→履歴まで一画面で完結")

        app_state = gr.State(value=AppState())

        with gr.Tabs():
            with gr.Tab("Code / Prompt"):
                build_code_prompt_tab(app_state)

            with gr.Tab("AI Revision"):
                build_ai_revision_tab(app_state)

            with gr.Tab("Test Runner"):
                build_test_runner_tab(app_state)

            with gr.Tab("History & Diff"):
                build_history_diff_tab(app_state)

    return demo


def launch_unified_ui(
    server_name: str = "127.0.0.1",
    server_port: int = 7860,
    inbrowser: bool = False,
    share: bool = False,
) -> None:
    """統合 Gradio UI を起動"""
    demo = build_unified_ui()
    demo.queue().launch(
        server_name=server_name,
        server_port=server_port,
        inbrowser=inbrowser,
        share=share,
        show_error=True,
        theme=gr.themes.Soft(),
    )


if __name__ == "__main__":
    launch_unified_ui()
