"""
NexusCore SaaS基盤 - Gradioダッシュボード

既存の Orchestrator / NPE / Agents を統合した Gradio UI。

既存の RequirementAgent Gradio UI を参考にしつつ、
複数プロジェクト・複数ユーザーで共通利用できるテンプレ化を実現。
"""

from __future__ import annotations

import gradio as gr

# 既存のエージェントをインポート（必要に応じて）
try:
    from nexuscore.agents.coder_agent import CoderAgent
    from nexuscore.agents.context_agent import ContextAgent
    from nexuscore.agents.debugger_agent import DebuggerAgent
    from nexuscore.agents.patch_applier import PatchApplier
except ImportError:
    # エージェントが存在しない場合は None として扱う
    ContextAgent = None
    DebuggerAgent = None
    CoderAgent = None
    PatchApplier = None


def create_nexus_dashboard(
    project_id: int | None = None, project_path: str | None = None
) -> gr.Blocks:
    """
    NexusCore Gradioダッシュボードを作成

    Args:
        project_id: プロジェクトID（オプション）
        project_path: プロジェクトパス（オプション）

    Returns:
        Gradio Blocks アプリケーション
    """
    with gr.Blocks(title="NexusCore Dashboard") as app:
        gr.Markdown("# NexusCore Dashboard")

        with gr.Tabs():
            # Tab1: 解析
            with gr.Tab("解析"):
                gr.Markdown("## プロジェクト概要・コンテキスト")
                project_info = gr.Textbox(label="Project Info", interactive=False)
                context_display = gr.Textbox(label="Context", lines=10, interactive=False)
                analyze_btn = gr.Button("Analyze Project")

                def analyze_project(proj_id: int | None, proj_path: str | None):
                    """プロジェクトを解析"""
                    if not proj_path:
                        return "No project path specified", "No context available"

                    try:
                        # ContextAgent を使用してコンテキストを取得
                        if ContextAgent:
                            context_agent = ContextAgent(project_root=proj_path)
                            context = context_agent.get_context()
                            return f"Project: {proj_path}", str(context)
                        else:
                            return f"Project: {proj_path}", "ContextAgent not available"
                    except Exception as e:
                        return f"Error: {proj_path}", f"Analysis failed: {str(e)}"

                analyze_btn.click(
                    fn=analyze_project,
                    inputs=[
                        gr.Number(value=project_id, visible=False),
                        gr.Textbox(value=project_path, visible=False),
                    ],
                    outputs=[project_info, context_display],
                )

            # Tab2: 修正
            with gr.Tab("修正"):
                gr.Markdown("## 自己修復フロー")
                error_log = gr.Textbox(
                    label="Error Log", lines=10, placeholder="Paste error log here..."
                )
                patch_preview = gr.Textbox(label="Patch Preview", lines=20, interactive=False)
                apply_patch_btn = gr.Button("Apply Patch", variant="primary")
                patch_status = gr.Textbox(label="Status", interactive=False)

                def generate_patch(error_log_text: str, proj_path: str | None):
                    """パッチを生成"""
                    if not error_log_text or not proj_path:
                        return "No error log or project path", ""

                    try:
                        if DebuggerAgent and PatchApplier:
                            DebuggerAgent(project_root=proj_path)
                            # 簡易版：実際の実装では、より詳細な処理が必要
                            patch_text = f"# Generated patch for: {proj_path}\n# Error: {error_log_text[:100]}"
                            return patch_text, "Patch generated (preview mode)"
                        else:
                            return "DebuggerAgent or PatchApplier not available", ""
                    except Exception as e:
                        return "", f"Patch generation failed: {str(e)}"

                def apply_patch(patch_text: str, proj_path: str | None):
                    """パッチを適用"""
                    if not patch_text or not proj_path:
                        return "No patch or project path"

                    try:
                        if PatchApplier:
                            applier = PatchApplier()
                            result = applier.apply_patch(
                                patch_text=patch_text,
                                project_path=proj_path,
                                dry_run=False,
                                allow_deletions=False,
                            )
                            if result.get("success"):
                                return "Patch applied successfully"
                            else:
                                return f"Patch application failed: {result.get('error', 'Unknown error')}"
                        else:
                            return "PatchApplier not available"
                    except Exception as e:
                        return f"Patch application failed: {str(e)}"

                generate_btn = gr.Button("Generate Patch")
                generate_btn.click(
                    fn=generate_patch,
                    inputs=[error_log, gr.Textbox(value=project_path, visible=False)],
                    outputs=[patch_preview, patch_status],
                )

                apply_patch_btn.click(
                    fn=apply_patch,
                    inputs=[patch_preview, gr.Textbox(value=project_path, visible=False)],
                    outputs=[patch_status],
                )

            # Tab3: テスト
            with gr.Tab("テスト"):
                gr.Markdown("## テスト実行")
                test_command = gr.Textbox(label="Test Command", value="pytest -q", interactive=True)
                test_output = gr.Textbox(label="Test Output", lines=20, interactive=False)
                run_test_btn = gr.Button("Run Tests", variant="primary")

                def run_tests(cmd: str, proj_path: str | None):
                    """テストを実行"""
                    if not proj_path:
                        return "No project path specified"

                    try:
                        import subprocess

                        result = subprocess.run(
                            cmd.split(),
                            cwd=proj_path,
                            capture_output=True,
                            text=True,
                            timeout=300,
                        )
                        output = f"Return code: {result.returncode}\n\nSTDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
                        return output
                    except subprocess.TimeoutExpired:
                        return "Test execution timed out"
                    except Exception as e:
                        return f"Test execution failed: {str(e)}"

                run_test_btn.click(
                    fn=run_tests,
                    inputs=[test_command, gr.Textbox(value=project_path, visible=False)],
                    outputs=[test_output],
                )

            # Tab4: 履歴
            with gr.Tab("履歴"):
                gr.Markdown("## Run / ExecutionLog / PatchRecord 一覧")
                history_display = gr.Textbox(label="History", lines=20, interactive=False)
                refresh_btn = gr.Button("Refresh History")

                def load_history(proj_id: int | None):
                    """履歴を読み込む"""
                    if not proj_id:
                        return "No project ID specified"

                    try:
                        from nexuscore.webapp.models import Run

                        # 最新のRunを取得
                        runs = (
                            Run.query.filter_by(project_id=proj_id)
                            .order_by(Run.created_at.desc())
                            .limit(10)
                            .all()
                        )

                        history_text = "Recent Runs:\n\n"
                        for run in runs:
                            history_text += f"Run ID: {run.run_id}\n"
                            history_text += f"Status: {run.status}\n"
                            history_text += f"Started: {run.started_at}\n"
                            history_text += f"Finished: {run.finished_at}\n"
                            history_text += "---\n"

                        return history_text
                    except Exception as e:
                        return f"Failed to load history: {str(e)}"

                refresh_btn.click(
                    fn=load_history,
                    inputs=[gr.Number(value=project_id, visible=False)],
                    outputs=[history_display],
                )

    return app


def launch_dashboard(
    project_id: int | None = None, project_path: str | None = None, server_port: int = 7860
):
    """
    ダッシュボードを起動

    Args:
        project_id: プロジェクトID
        project_path: プロジェクトパス
        server_port: サーバーポート
    """
    app = create_nexus_dashboard(project_id=project_id, project_path=project_path)
    app.launch(server_port=server_port, share=False)


if __name__ == "__main__":
    import sys

    project_id = int(sys.argv[1]) if len(sys.argv) > 1 else None
    project_path = sys.argv[2] if len(sys.argv) > 2 else None
    launch_dashboard(project_id=project_id, project_path=project_path)
