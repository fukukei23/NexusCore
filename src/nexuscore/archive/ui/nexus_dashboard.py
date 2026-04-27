"""
NexusCore SaaS基盤 - Gradioダッシュボード

Orchestrator / assemble_agent_team 経由でエージェントにアクセスし、
Orchestrator バイパスを排除した統合 UI。
"""

from __future__ import annotations

import functools

import gradio as gr

from nexuscore.core.orchestrator import assemble_agent_team

# モジュールレベルのエージェントキャッシュ
_agents_cache: dict | None = None


@functools.lru_cache(maxsize=1)
def _get_agents(project_path: str) -> dict:
    return assemble_agent_team(project_path)


def _get_cached_agents(project_path: str | None) -> dict | None:
    if not project_path:
        return None
    try:
        return _get_agents(project_path)
    except Exception:
        return None


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
                        agents = _get_cached_agents(proj_path)
                        if agents and "architect_agent" in agents:
                            architect = agents["architect_agent"]
                            context = getattr(architect, "get_context", lambda: "No context method")()
                            return f"Project: {proj_path}", str(context)
                        else:
                            return f"Project: {proj_path}", "Agent team not available"
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
                        agents = _get_cached_agents(proj_path)
                        debugger = agents.get("debugger_agent") if agents else None
                        if debugger:
                            patch_text = f"# Generated patch for: {proj_path}\n# Error: {error_log_text[:100]}"
                            return patch_text, "Patch generated (preview mode)"
                        else:
                            return "DebuggerAgent not available via agent team", ""
                    except Exception as e:
                        return "", f"Patch generation failed: {str(e)}"

                def apply_patch(patch_text: str, proj_path: str | None):
                    """パッチを適用"""
                    if not patch_text or not proj_path:
                        return "No patch or project path"

                    try:
                        agents = _get_cached_agents(proj_path)
                        applier = agents.get("patch_applier_agent") if agents else None
                        if applier:
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
                            return "PatchApplier not available via agent team"
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
