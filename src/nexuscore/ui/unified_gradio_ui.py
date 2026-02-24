"""
4.5: 統合 Gradio UI

「解析→修正→テスト→履歴」まで一画面で閉じるタブ構成
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import gradio as gr

# 既存のモジュールをインポート
try:
    from nexuscore.modules.whisper_handler import transcribe_audio

    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False
    transcribe_audio = None

try:
    from nexuscore.agents.debugger_agent import DebuggerAgent
    from nexuscore.integration.github_pr_comment import load_run_markdown
    from nexuscore.services.self_healing_service import SelfHealingService

    HAS_SELF_HEALING = True
except ImportError:
    HAS_SELF_HEALING = False
    SelfHealingService = None
    DebuggerAgent = None
    load_run_markdown = None

logger = logging.getLogger(__name__)


@dataclass
class AppState:
    """アプリケーション全体で共有する State"""

    current_file_path: str | None = None
    generated_code: str | None = None
    latest_test_result: str | None = None
    latest_run_id: str | None = None
    before_code: dict[str, str] = field(default_factory=dict)  # ファイルパス -> コード
    after_code: dict[str, str] = field(default_factory=dict)  # ファイルパス -> コード


# ============================================================================
# Tab 1: Code / Prompt
# ============================================================================


def build_code_prompt_tab(state: gr.State) -> None:
    """
    Tab 1: Code / Prompt（Whisper + 自然文プロンプト → 初期コード生成）
    """
    with gr.Column():
        gr.Markdown("## 📝 Code / Prompt")
        gr.Markdown("音声入力またはテキストプロンプトからコードを生成します。")

        with gr.Row():
            with gr.Column():
                # 音声入力
                audio_input = gr.Audio(
                    label="🎙️ 音声入力（Whisper）",
                    type="filepath",
                    visible=HAS_WHISPER,
                )
                transcribe_button = gr.Button("音声を文字起こし", visible=HAS_WHISPER)

                # テキストプロンプト
                prompt_input = gr.Textbox(
                    label="💬 自然文プロンプト",
                    placeholder="例: 素数判定関数を作成してください",
                    lines=5,
                )

                # ファイル名
                filename_input = gr.Textbox(
                    label="📄 ファイル名（オプション）",
                    placeholder="例: prime_checker.py",
                )

                generate_code_button = gr.Button("🔁 コード生成", variant="primary")

            with gr.Column():
                generated_code_output = gr.Code(
                    label="✅ 生成されたコード",
                    language="python",
                    lines=20,
                    interactive=True,
                )

                save_code_button = gr.Button("💾 コードを保存")

    # イベントハンドラ
    if HAS_WHISPER:

        def transcribe_handler(audio_path: str) -> str:
            """音声を文字起こし"""
            try:
                if not audio_path:
                    return ""
                text = transcribe_audio(audio_path)
                return text
            except Exception as e:
                logger.error(f"Transcription failed: {e}", exc_info=True)
                return f"❌ エラー: {e}"

        transcribe_button.click(
            fn=transcribe_handler,
            inputs=[audio_input],
            outputs=[prompt_input],
        )

    def generate_code_handler(
        prompt: str, filename: str, current_state: AppState
    ) -> tuple[str, AppState]:
        """プロンプトからコードを生成"""
        if not prompt.strip():
            return "💡 プロンプトを入力してください。", current_state

        try:
            # TODO: LLM を使ってコード生成（既存のコード生成ロジックを再利用）
            # 暫定的にプレースホルダー
            generated = f"""# Generated from: {prompt}

def placeholder_function():
    \"\"\"Generated code placeholder\"\"\"
    pass
"""
            # State を更新
            current_state.generated_code = generated
            if filename:
                current_state.current_file_path = filename

            return generated, current_state
        except Exception as e:
            logger.error(f"Code generation failed: {e}", exc_info=True)
            return f"❌ エラー: {e}", current_state

    def save_code_handler(
        code: str, filename: str, current_state: AppState
    ) -> tuple[str, AppState]:
        """コードを保存"""
        if not code.strip():
            return "💡 コードが空です。", current_state

        try:
            file_path = filename or "generated_code.py"
            save_path = Path("sandbox_output") / file_path
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_text(code, encoding="utf-8")

            current_state.current_file_path = str(save_path)
            current_state.generated_code = code
            current_state.before_code[str(save_path)] = code

            return f"✅ 保存しました: {save_path}", current_state
        except Exception as e:
            logger.error(f"Save failed: {e}", exc_info=True)
            return f"❌ エラー: {e}", current_state

    generate_code_button.click(
        fn=generate_code_handler,
        inputs=[prompt_input, filename_input, state],
        outputs=[generated_code_output, state],
    )

    save_code_button.click(
        fn=save_code_handler,
        inputs=[generated_code_output, filename_input, state],
        outputs=[gr.Textbox(visible=False), state],  # 保存結果は別途表示
    )

    # 戻り値なし（Gradio Blocks 内で直接構築）


# ============================================================================
# Tab 2: AI Revision
# ============================================================================


def build_ai_revision_tab(state: gr.State) -> None:
    """
    Tab 2: AI Revision（LLMで修正・パッチ生成）
    """
    with gr.Column():
        gr.Markdown("## 🤖 AI Revision")
        gr.Markdown("既存コードを LLM で修正・パッチ生成します。")

        with gr.Row():
            with gr.Column():
                code_input = gr.Code(
                    label="📝 修正対象コード",
                    language="python",
                    lines=20,
                    interactive=True,
                )

                revision_prompt = gr.Textbox(
                    label="💬 修正指示",
                    placeholder="例: エラーハンドリングを追加してください",
                    lines=5,
                )

                with gr.Row():
                    generate_patch_button = gr.Button("🔧 パッチ生成", variant="primary")
                    apply_patch_button = gr.Button("✅ パッチ適用", variant="secondary")

            with gr.Column():
                patch_output = gr.Code(
                    label="📋 生成されたパッチ（Unified Diff）",
                    language="diff",
                    lines=20,
                    interactive=False,
                )

                revision_result = gr.Textbox(
                    label="📊 修正結果",
                    lines=10,
                    interactive=False,
                )

    def generate_patch_handler(
        code: str, prompt: str, current_state: AppState
    ) -> tuple[str, str, AppState]:
        """パッチを生成"""
        if not code.strip() or not prompt.strip():
            return "", "💡 コードと修正指示を入力してください。", current_state

        try:
            # TODO: DebuggerAgent を使ってパッチ生成
            # 暫定的にプレースホルダー
            patch = f"""--- a/{current_state.current_file_path or 'file.py'}
+++ b/{current_state.current_file_path or 'file.py'}
@@ -1,1 +1,2 @@
 {code}
+# Modified by AI: {prompt}
"""
            return patch, "✅ パッチを生成しました。", current_state
        except Exception as e:
            logger.error(f"Patch generation failed: {e}", exc_info=True)
            return "", f"❌ エラー: {e}", current_state

    def apply_patch_handler(patch: str, current_state: AppState) -> tuple[str, AppState]:
        """パッチを適用"""
        if not patch.strip():
            return "💡 パッチが空です。", current_state

        try:
            # TODO: PatchApplier を使ってパッチ適用
            # 暫定的にプレースホルダー
            file_path = current_state.current_file_path
            if file_path and Path(file_path).exists():
                # パッチ適用のロジック（簡易版）
                current_state.after_code[file_path] = "Modified code"
                return "✅ パッチを適用しました。", current_state
            else:
                return "❌ ファイルが見つかりません。", current_state
        except Exception as e:
            logger.error(f"Patch apply failed: {e}", exc_info=True)
            return f"❌ エラー: {e}", current_state

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

    # 戻り値なし（Gradio Blocks 内で直接構築）


# ============================================================================
# Tab 3: Test Runner
# ============================================================================


def build_test_runner_tab(state: gr.State) -> None:
    """
    Tab 3: Test Runner（pytest 実行＋結果表示）
    """
    with gr.Column():
        gr.Markdown("## 🧪 Test Runner")
        gr.Markdown("pytest を実行して結果を表示します。")

        with gr.Row():
            with gr.Column():
                test_command_input = gr.Textbox(
                    label="📝 テストコマンド",
                    value="pytest -q",
                    lines=1,
                )

                test_file_input = gr.Textbox(
                    label="📄 テストファイル（オプション）",
                    placeholder="例: tests/test_sample.py",
                )

                run_test_button = gr.Button("▶️ テスト実行", variant="primary")

            with gr.Column():
                test_output = gr.Textbox(
                    label="📊 テスト結果",
                    lines=25,
                    interactive=False,
                )

                test_status = gr.Markdown("**ステータス:** 未実行")

    def run_test_handler(
        command: str, test_file: str, current_state: AppState
    ) -> tuple[str, str, AppState]:
        """テストを実行"""
        try:
            # テストコマンドを構築（リスト形式でコマンドインジェクション対策）
            if test_file.strip():
                cmd_list = [command, test_file]
            else:
                cmd_list = [command]

            # テスト実行
            result = subprocess.run(
                cmd_list,
                shell=False,  # セキュリティ: コマンドインジェクション対策
                capture_output=True,
                text=True,
                cwd=Path.cwd(),
            )

            output = result.stdout + result.stderr if result.stderr else result.stdout
            success = result.returncode == 0

            # State を更新
            current_state.latest_test_result = output

            # ステータス表示
            status_md = f"**ステータス:** {'✅ 成功' if success else '❌ 失敗'}\n\n**Return Code:** {result.returncode}"

            return output, status_md, current_state
        except Exception as e:
            logger.error(f"Test execution failed: {e}", exc_info=True)
            error_msg = f"❌ エラー: {e}"
            return error_msg, "**ステータス:** ❌ エラー", current_state

    run_test_button.click(
        fn=run_test_handler,
        inputs=[test_command_input, test_file_input, state],
        outputs=[test_output, test_status, state],
    )

    # 戻り値なし（Gradio Blocks 内で直接構築）


# ============================================================================
# Tab 4: History & Diff
# ============================================================================


def build_history_diff_tab(state: gr.State) -> None:
    """
    Tab 4: History & Diff（過去 Run・差分ビュー・Self-Healing Run トリガー）
    """
    with gr.Column():
        gr.Markdown("## 📜 History & Diff")
        gr.Markdown("過去の Run 履歴と Before/After 差分を表示します。")

        with gr.Row():
            with gr.Column():
                # Run ID 選択
                run_id_input = gr.Textbox(
                    label="🔍 Run ID",
                    placeholder="例: sh-1234567890-123-abc1234",
                )

                load_run_button = gr.Button("📥 Run を読み込み", variant="primary")

                # Self-Healing Run トリガー
                gr.Markdown("### 🤖 Self-Healing Run")
                repo_full_name_input = gr.Textbox(
                    label="📦 Repository (owner/repo)",
                    placeholder="例: owner/repo",
                )
                pr_number_input = gr.Number(
                    label="🔢 PR Number",
                    value=0,
                    precision=0,
                )
                head_sha_input = gr.Textbox(
                    label="🔀 Head SHA",
                    placeholder="例: abc1234",
                )

                trigger_self_healing_button = gr.Button("🚀 Self-Healing を実行", variant="primary")

            with gr.Column():
                # Before / After コード表示
                before_code_output = gr.Code(
                    label="📄 Before",
                    language="python",
                    lines=20,
                    interactive=False,
                )

                after_code_output = gr.Code(
                    label="📄 After",
                    language="python",
                    lines=20,
                    interactive=False,
                )

                diff_summary_output = gr.Markdown(
                    label="📊 Diff Summary",
                )

                self_healing_result = gr.Textbox(
                    label="🤖 Self-Healing 結果",
                    lines=10,
                    interactive=False,
                )

    def load_run_handler(run_id: str, current_state: AppState) -> tuple[str, str, str, AppState]:
        """Run を読み込み"""
        if not run_id.strip():
            return "", "", "💡 Run ID を入力してください。", current_state

        try:
            # Run レポートを読み込み
            if load_run_markdown:
                markdown_content = load_run_markdown(run_id)
            else:
                # フォールバック: ファイルから直接読み込み
                from nexuscore.integration.run_report_generator import get_markdown_report_path

                report_path = get_markdown_report_path(run_id)
                if report_path.exists():
                    markdown_content = report_path.read_text(encoding="utf-8")
                else:
                    markdown_content = f"❌ Run レポートが見つかりません: {report_path}"

            # TODO: Before/After コードを抽出（簡易版）
            # State から取得
            file_path = current_state.current_file_path
            before_code = current_state.before_code.get(file_path, "") if file_path else ""
            after_code = current_state.after_code.get(file_path, "") if file_path else ""

            current_state.latest_run_id = run_id

            return before_code, after_code, markdown_content, current_state
        except Exception as e:
            logger.error(f"Load run failed: {e}", exc_info=True)
            return "", "", f"❌ エラー: {e}", current_state

    def trigger_self_healing_handler(
        repo_full_name: str,
        pr_number: int,
        head_sha: str,
        current_state: AppState,
    ) -> tuple[str, AppState]:
        """Self-Healing Run を実行"""
        if not repo_full_name.strip() or not head_sha.strip() or pr_number <= 0:
            return "💡 Repository、PR Number、Head SHA を入力してください。", current_state

        if not HAS_SELF_HEALING:
            return "❌ Self-Healing Service が利用できません。", current_state

        try:
            # SelfHealingService を初期化
            project_root = Path.cwd()
            service = SelfHealingService(project_root=str(project_root))

            # Self-Healing を実行
            result = service.run_for_pull_request(
                repo_full_name=repo_full_name,
                pr_number=pr_number,
                head_sha=head_sha,
            )

            # 結果をフォーマット
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
        except Exception as e:
            logger.error(f"Self-Healing execution failed: {e}", exc_info=True)
            return f"❌ エラー: {e}", current_state

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

    # 戻り値なし（Gradio Blocks 内で直接構築）


# ============================================================================
# メイン UI 構築
# ============================================================================


def run_test_handler(
    command: str, test_file: str, current_state: AppState
) -> tuple[str, str, AppState]:
    """
    テストを実行するハンドラー関数

    コマンドインジェクション対策のため、shell=False と引数リスト形式を使用。
    """
    try:
        # テストコマンドを構築（コマンドインジェクション対策: 引数リスト形式を使用）
        cmd: list[str]
        if test_file and test_file.strip():
            cmd = [command, test_file]
        else:
            cmd = [command]

        # テスト実行（shell=False で安全に実行）
        result = subprocess.run(
            cmd,
            shell=False,
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )

        output = result.stdout + result.stderr if result.stderr else result.stdout
        success = result.returncode == 0

        # State を更新
        current_state.latest_test_result = output

        # ステータス表示
        status_md = f"**ステータス:** {'✅ 成功' if success else '❌ 失敗'}\n\n**Return Code:** {result.returncode}"

        return output, status_md, current_state
    except Exception as e:
        logger.error(f"Test execution failed: {e}", exc_info=True)
        error_msg = f"❌ エラー: {e}"
        return error_msg, "**ステータス:** ❌ エラー", current_state


def build_unified_ui() -> gr.Blocks:
    """
    統合 Gradio UI を構築
    """
    with gr.Blocks(title="NexusCore Unified UI", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🤖 NexusCore Unified UI")
        gr.Markdown("解析→修正→テスト→履歴まで一画面で完結")

        # State を初期化
        app_state = gr.State(value=AppState())

        # タブ構成
        with gr.Tabs():
            with gr.Tab("📝 Code / Prompt"):
                build_code_prompt_tab(app_state)

            with gr.Tab("🤖 AI Revision"):
                build_ai_revision_tab(app_state)

            with gr.Tab("🧪 Test Runner"):
                build_test_runner_tab(app_state)

            with gr.Tab("📜 History & Diff"):
                build_history_diff_tab(app_state)

    return demo


def launch_unified_ui(
    server_name: str = "127.0.0.1",
    server_port: int = 7860,
    inbrowser: bool = False,
    share: bool = False,
) -> None:
    """
    統合 Gradio UI を起動
    """
    demo = build_unified_ui()
    demo.queue().launch(
        server_name=server_name,
        server_port=server_port,
        inbrowser=inbrowser,
        share=share,
        show_error=True,
    )


if __name__ == "__main__":
    launch_unified_ui()
