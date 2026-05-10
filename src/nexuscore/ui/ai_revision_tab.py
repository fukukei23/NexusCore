"""Tab 2: AI Revision（LLMで修正・パッチ生成）"""

from __future__ import annotations

import logging
from pathlib import Path

import gradio as gr

from ._llm_init import HAS_LLM, _router
from ._state import AppState

logger = logging.getLogger(__name__)


def build_ai_revision_tab(state: gr.State) -> None:
    with gr.Column():
        gr.Markdown("## AI Revision")
        gr.Markdown("既存コードを LLM で修正・パッチ生成します。")

        with gr.Row():
            with gr.Column():
                load_code_btn = gr.Button("Code/Promptで生成したコードを読み込む", variant="secondary")

                code_input = gr.Code(
                    label="修正対象コード",
                    language="python",
                    lines=20,
                    interactive=True,
                )

                revision_prompt = gr.Textbox(
                    label="修正指示",
                    placeholder="例: 型ヒントを追加してください / エラーハンドリングを追加してください",
                    lines=5,
                )

                with gr.Row():
                    generate_patch_button = gr.Button("修正コードを生成", variant="primary")
                    apply_patch_button = gr.Button("ファイルに書き戻す", variant="secondary")

            with gr.Column():
                patch_output = gr.Code(
                    label="生成されたパッチ（Unified Diff）",
                    language=None,
                    lines=20,
                    interactive=False,
                )

                revision_result = gr.Textbox(
                    label="修正結果",
                    lines=10,
                    interactive=False,
                )

    def load_generated_code(current_state: AppState) -> str:
        code = current_state.generated_code or ""
        if not code:
            return "# Code/Promptタブでコードを生成してください"
        return code

    load_code_btn.click(
        fn=load_generated_code,
        inputs=[state],
        outputs=[code_input],
    )

    def generate_patch_handler(
        code: str | None, prompt: str | None, current_state: AppState
    ) -> tuple[str, str, AppState]:
        code = (code or "").strip()
        prompt = (prompt or "").strip()
        if not code or not prompt:
            return "", "コードと修正指示を両方入力してください。", current_state

        try:
            if HAS_LLM:
                result = _router.complete(
                    model="glm:glm-5.1",
                    task="code_generate",
                    system_prompt=(
                        "あなたはPythonコード修正アシスタントです。"
                        "ユーザーが提示したコードに対して、指定された修正を適用した完全なコードを出力してください。"
                        "説明文は不要です。修正後のコードのみを返してください。"
                    ),
                    user_prompt=f"元のコード:\n```python\n{code}\n```\n\n修正指示: {prompt}",
                )
                revised = result.get("content", "") if result.get("ok") else ""
                if not revised:
                    return "", f"LLM Error: {result.get('reason', 'unknown')}", current_state
                if revised.startswith("```"):
                    lines = revised.split("\n")
                    revised = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            else:
                return "", "LLM Router が初期化されていません。", current_state

            return revised, "修正コードを生成しました。「ファイルに書き戻す」で保存できます。", current_state
        except Exception as e:
            logger.error(f"Patch generation failed: {e}", exc_info=True)
            return "", f"Error: {e}", current_state

    def apply_patch_handler(patch: str | None, current_state: AppState) -> tuple[str, AppState]:
        patch = (patch or "").strip()
        if not patch:
            return "修正コードが空です。先に「修正コードを生成」してください。", current_state

        try:
            test_path = current_state.current_file_path or ""
            if test_path.startswith("sandbox_output/test_"):
                source_name = test_path.replace("sandbox_output/test_", "sandbox_output/")
            else:
                source_name = test_path

            file_path = Path(source_name) if source_name else None
            if file_path and file_path.exists():
                current_state.after_code[str(file_path)] = patch
                file_path.write_text(patch, encoding="utf-8")
                return f"{file_path} に書き戻しました。", current_state
            else:
                return "書き戻し先ファイルが見つかりません。Code/Promptでコードを保存してから使ってください。", current_state
        except Exception as e:
            logger.error(f"Patch apply failed: {e}", exc_info=True)
            return f"Error: {e}", current_state

    generate_patch_button.click(
        fn=generate_patch_handler,
        inputs=[code_input, revision_prompt, state],
        outputs=[patch_output, revision_result, state],
    )

    apply_patch_button.click(
        fn=apply_patch_handler,
        inputs=[patch_output, state],
        outputs=[revision_result, state],
    )
