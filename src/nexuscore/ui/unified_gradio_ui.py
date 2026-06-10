from __future__ import annotations

import gradio as gr

from ._state import AppState
from .ai_revision_tab import build_ai_revision_tab
from .code_prompt_tab import build_code_prompt_tab
from .dynamic_run_tab import build_dynamic_run_tab
from .history_diff_tab import build_history_diff_tab
from .settings_tab import build_settings_tab
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

            with gr.Tab("Dynamic Run"):
                build_dynamic_run_tab()

            with gr.Tab("Settings"):
                build_settings_tab(app_state)

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
