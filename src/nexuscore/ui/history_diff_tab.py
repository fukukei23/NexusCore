from __future__ import annotations

import logging
from pathlib import Path

import gradio as gr

from ._llm_init import HAS_SELF_HEALING, SelfHealingService, load_run_markdown
from ._state import AppState

logger = logging.getLogger(__name__)


def build_history_diff_tab(state: gr.State) -> None:
    with gr.Column():
        gr.Markdown("## History & Diff")
        gr.Markdown("過去の Run 履歴と Before/After 差分を表示します。")

        with gr.Row():
            with gr.Column():
                run_id_input = gr.Textbox(
                    label="Run ID",
                    placeholder="例: sh-1234567890-123-abc1234",
                )

                load_run_button = gr.Button("Run を読み込み", variant="primary")

                gr.Markdown("### Self-Healing Run")
                repo_full_name_input = gr.Textbox(
                    label="Repository (owner/repo)",
                    placeholder="例: owner/repo",
                )
                pr_number_input = gr.Number(
                    label="PR Number",
                    value=0,
                    precision=0,
                )
                head_sha_input = gr.Textbox(
                    label="Head SHA",
                    placeholder="例: abc1234",
                )

                trigger_self_healing_button = gr.Button("Self-Healing を実行", variant="primary")

            with gr.Column():
                before_code_output = gr.Code(
                    label="Before",
                    language="python",
                    lines=20,
                    interactive=False,
                )

                after_code_output = gr.Code(
                    label="After",
                    language="python",
                    lines=20,
                    interactive=False,
                )

                diff_summary_output = gr.Markdown(
                    label="Diff Summary",
                )

                self_healing_result = gr.Textbox(
                    label="Self-Healing 結果",
                    lines=10,
                    interactive=False,
                )

    def load_run_handler(run_id: str, current_state: AppState) -> tuple[str, str, str, AppState]:
        if not run_id.strip():
            return "", "", "Run ID を入力してください。", current_state

        try:
            if load_run_markdown:
                markdown_content = load_run_markdown(run_id)
            else:
                from nexuscore.integration.run_report_generator import get_markdown_report_path

                report_path = get_markdown_report_path(run_id)
                if report_path.exists():
                    markdown_content = report_path.read_text(encoding="utf-8")
                else:
                    markdown_content = f"Run レポートが見つかりません: {report_path}"

            file_path = current_state.current_file_path
            before_code = current_state.before_code.get(file_path, "") if file_path else ""
            after_code = current_state.after_code.get(file_path, "") if file_path else ""

            current_state.latest_run_id = run_id

            return before_code, after_code, markdown_content, current_state
        except Exception as e:  # noqa: BLE001
            logger.error(f"Load run failed: {e}", exc_info=True)
            return "", "", f"Error: {e}", current_state

    def trigger_self_healing_handler(
        repo_full_name: str,
        pr_number: int,
        head_sha: str,
        current_state: AppState,
    ) -> tuple[str, AppState]:
        if not repo_full_name.strip() or not head_sha.strip() or pr_number <= 0:
            return "Repository、PR Number、Head SHA を入力してください。", current_state

        if not HAS_SELF_HEALING:
            return "Self-Healing Service が利用できません。", current_state

        try:
            project_root = Path.cwd()
            service = SelfHealingService(project_root=str(project_root))

            result = service.run_for_pull_request(
                repo_full_name=repo_full_name,
                pr_number=pr_number,
                head_sha=head_sha,
            )

            result_text = f"""Status: {result.get('status', 'unknown')}
Summary: {result.get('summary', 'N/A')}
Run ID: {result.get('run_id', 'N/A')}
Duration: {result.get('duration_seconds', 0):.2f}s
"""
            if result.get("details"):
                details = result["details"]
                if details.get("retry_count"):
                    result_text += f"Retry Count: {details.get('retry_count')}\n"
                if details.get("last_error_class"):
                    result_text += f"Last Error: {details.get('last_error_class')}\n"

            current_state.latest_run_id = result.get("run_id")

            return result_text, current_state
        except Exception as e:  # noqa: BLE001
            logger.error(f"Self-Healing execution failed: {e}", exc_info=True)
            return f"Error: {e}", current_state

    load_run_button.click(
        fn=load_run_handler,
        inputs=[run_id_input, state],
        outputs=[before_code_output, after_code_output, diff_summary_output, state],
    )

    trigger_self_healing_button.click(
        fn=trigger_self_healing_handler,
        inputs=[repo_full_name_input, pr_number_input, head_sha_input, state],
        outputs=[self_healing_result, state],
    )
