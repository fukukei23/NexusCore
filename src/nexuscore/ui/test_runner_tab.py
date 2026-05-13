from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

import gradio as gr

from ._state import AppState, list_dirs_with_py, list_files_in_dir

logger = logging.getLogger(__name__)


def build_test_runner_tab(state: gr.State) -> None:
    with gr.Column():
        gr.Markdown("## Test Runner")
        gr.Markdown("pytest を実行して結果を表示します。")

        with gr.Row():
            with gr.Column():
                test_command_input = gr.Textbox(
                    label="テストコマンド",
                    value="pytest -q",
                    lines=1,
                )

                use_saved_btn = gr.Button("Code/Promptで保存したファイルを使う", variant="secondary")

                with gr.Row():
                    test_file_input = gr.Textbox(
                        label="テストファイル（直接入力またはフォルダ/ファイルから選択）",
                        placeholder="例: sandbox_output/generated_code.py",
                        scale=3,
                    )
                    refresh_btn = gr.Button("一覧更新", scale=1)

                with gr.Row():
                    dir_dropdown = gr.Dropdown(
                        label="フォルダ選択",
                        choices=list_dirs_with_py(),
                        interactive=True,
                        scale=1,
                    )
                    file_dropdown = gr.Dropdown(
                        label="ファイル選択",
                        choices=[],
                        interactive=True,
                        scale=1,
                    )

                run_test_button = gr.Button("テスト実行", variant="primary")

            with gr.Column():
                test_output = gr.Textbox(
                    label="テスト結果",
                    lines=25,
                    interactive=False,
                )

                test_status = gr.Markdown("**ステータス:** 未実行")

        def load_saved_file(current_state: AppState) -> str:
            if current_state.current_file_path:
                return current_state.current_file_path
            return "まだファイルが保存されていません。Code/Promptタブでコードを保存してください。"

        use_saved_btn.click(
            fn=load_saved_file,
            inputs=[state],
            outputs=[test_file_input],
        )

        dir_dropdown.change(
            fn=lambda d: gr.update(choices=list_files_in_dir(d)),
            inputs=[dir_dropdown],
            outputs=[file_dropdown],
        )
        file_dropdown.change(
            fn=lambda d, f: str(Path(d) / f) if d and f else "",
            inputs=[dir_dropdown, file_dropdown],
            outputs=[test_file_input],
        )
        refresh_btn.click(
            fn=lambda: gr.update(choices=list_dirs_with_py()),
            outputs=[dir_dropdown],
        )

    def run_test_handler(
        command: str, test_file: str, current_state: AppState
    ) -> tuple[str, str, AppState]:
        try:
            cmd_list = [sys.executable, "-m", "pytest", "-q"]
            if test_file.strip():
                cmd_list.append(test_file)

            result = subprocess.run(
                cmd_list,
                shell=False,
                capture_output=True,
                text=True,
                cwd=Path.cwd(),
            )

            output = result.stdout + result.stderr if result.stderr else result.stdout
            success = result.returncode == 0

            current_state.latest_test_result = output

            status_md = f"**ステータス:** {'成功' if success else '失敗'}\n\n**Return Code:** {result.returncode}"

            return output, status_md, current_state
        except Exception as e:
            logger.error(f"Test execution failed: {e}", exc_info=True)
            return f"Error: {e}", "**ステータス:** Error", current_state

    run_test_button.click(
        fn=run_test_handler,
        inputs=[test_command_input, test_file_input, state],
        outputs=[test_output, test_status, state],
    )
