"""Tab 1: Code / Prompt（Whisper + 自然文プロンプト → 初期コード生成）"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

import gradio as gr

from ._llm_init import HAS_LLM, HAS_WHISPER, _router, transcribe_audio
from ._state import AppState

logger = logging.getLogger(__name__)


def build_code_prompt_tab(state: gr.State) -> None:
    with gr.Column():
        gr.Markdown("## Code / Prompt")
        gr.Markdown("音声入力またはテキストプロンプトからコードを生成します。")

        with gr.Row():
            with gr.Column():
                audio_input = gr.Audio(
                    label="音声入力（Whisper）",
                    type="filepath",
                    visible=HAS_WHISPER,
                )
                transcribe_button = gr.Button("音声を文字起こし", visible=HAS_WHISPER)

                prompt_input = gr.Textbox(
                    label="自然文プロンプト",
                    placeholder="例: 素数判定関数を作成してください",
                    lines=5,
                )

                filename_input = gr.Textbox(
                    label="ファイル名（保存先: NexusCore/sandbox_output/）",
                    placeholder="例: prime_checker.py（省略時: generated_code.py）",
                )
                save_result_display = gr.Textbox(
                    label="保存結果",
                    interactive=False,
                    visible=True,
                )

                generate_code_button = gr.Button("コード生成", variant="primary")

            with gr.Column():
                generated_code_output = gr.Code(
                    label="生成されたコード",
                    language="python",
                    lines=20,
                    interactive=True,
                )

                save_code_button = gr.Button("コードを保存")

    if HAS_WHISPER:

        def transcribe_handler(audio_path: str) -> str:
            try:
                if not audio_path:
                    return ""
                return transcribe_audio(audio_path)
            except Exception as e:
                logger.error(f"Transcription failed: {e}", exc_info=True)
                return f"Error: {e}"

        transcribe_button.click(
            fn=transcribe_handler,
            inputs=[audio_input],
            outputs=[prompt_input],
        )

    def _extract_filename_from_code(code: str) -> str:
        match = re.search(r"^class\s+(\w+)", code, re.MULTILINE)
        if match:
            return f"{match.group(1)}.py"
        match = re.search(r"^def\s+(\w+)", code, re.MULTILINE)
        if match:
            return f"{match.group(1)}.py"
        return f"generated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"

    def generate_code_handler(
        prompt: str, filename: str, current_state: AppState
    ) -> tuple[str, str, AppState]:
        if not prompt.strip():
            return "プロンプトを入力してください。", filename, current_state

        try:
            if HAS_LLM:
                result = _router.complete(
                    model="glm:glm-5.1",
                    task="code_generate",
                    system_prompt=(
                        "あなたはPythonコード生成アシスタントです。"
                        "ユーザーの要求に応じて、クリーンで実行可能なPythonコードのみを出力してください。"
                        "説明文は不要です。コードブロックのみ返してください。"
                    ),
                    user_prompt=prompt,
                )
                generated = result.get("content", "") if result.get("ok") else f"LLM Error: {result.get('reason', 'unknown')}"
                if generated.startswith("```"):
                    lines = generated.split("\n")
                    generated = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            else:
                generated = "LLM Router が初期化されていません。APIキーを確認してください。"

            current_state.generated_code = generated

            auto_filename = filename.strip() if filename.strip() else _extract_filename_from_code(generated)
            current_state.current_file_path = auto_filename

            return generated, auto_filename, current_state
        except Exception as e:
            logger.error(f"Code generation failed: {e}", exc_info=True)
            return f"Error: {e}", filename, current_state

    def _generate_test_code(code: str, module_stem: str) -> str:
        func_names = re.findall(r"^def\s+([a-zA-Z][a-zA-Z0-9_]*)\s*\(", code, re.MULTILINE)
        class_names = re.findall(r"^class\s+([a-zA-Z][a-zA-Z0-9_]*)", code, re.MULTILINE)

        lines = [
            "import sys",
            "import pytest",
            "sys.path.insert(0, 'sandbox_output')",
            f"from {module_stem} import *",
            "",
        ]

        if not func_names and not class_names:
            lines += [
                "def test_module_loads():",
                '    """モジュールが正常にインポートできることを確認"""',
                "    pass",
            ]
        else:
            for fn in func_names:
                lines += [
                    f"def test_{fn}():",
                    f'    """TODO: {fn}() のテストケースを追加してください"""',
                    f"    # result = {fn}(...)",
                    "    # assert result == expected",
                    "    pass",
                    "",
                ]

        return "\n".join(lines)

    def save_code_handler(
        code: str, filename: str, current_state: AppState
    ) -> tuple[str, AppState]:
        if not code.strip():
            return "コードが空です。", current_state

        try:
            file_path = filename or "generated_code.py"
            save_path = Path("sandbox_output") / file_path
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_text(code, encoding="utf-8")

            module_stem = save_path.stem
            test_filename = f"test_{module_stem}.py"
            test_path = Path("sandbox_output") / test_filename
            test_code = _generate_test_code(code, module_stem)
            test_path.write_text(test_code, encoding="utf-8")

            current_state.current_file_path = str(test_path)
            current_state.generated_code = code
            current_state.before_code[str(save_path)] = code

            return (
                f"保存しました: {save_path}\n"
                f"テストファイル自動生成: {test_path}\n"
                f"（Test Runnerで「保存したファイルを使う」を押すと自動入力されます）"
            ), current_state
        except Exception as e:
            logger.error(f"Save failed: {e}", exc_info=True)
            return f"Error: {e}", current_state

    generate_code_button.click(
        fn=generate_code_handler,
        inputs=[prompt_input, filename_input, state],
        outputs=[generated_code_output, filename_input, state],
    )

    save_code_button.click(
        fn=save_code_handler,
        inputs=[generated_code_output, filename_input, state],
        outputs=[save_result_display, state],
    )
