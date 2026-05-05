"""
4.5: 統合 Gradio UI

「解析→修正→テスト→履歴」まで一画面で閉じるタブ構成
"""

from __future__ import annotations

import glob
import logging
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import gradio as gr

# .secrets.env を読み込み
from dotenv import load_dotenv

_load_path = Path.home() / ".secrets.env"
if _load_path.exists():
    load_dotenv(_load_path)

# LLMルーター
try:
    from nexuscore.llm.llm_router import LLMRouter

    _router = LLMRouter()
    HAS_LLM = True
except Exception as e:
    logging.getLogger(__name__).warning(f"LLMRouter init failed: {e}")
    _router = None
    HAS_LLM = False

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


def list_test_files() -> list[str]:
    """sandbox_output/, tests/, ルート直下の .py ファイル一覧を返す"""
    files: list[str] = []
    for pattern in [
        "sandbox_output/**/*.py",
        "tests/**/*.py",
        "*.py",
    ]:
        for p in glob.glob(pattern, recursive=True):
            files.append(p)
    return sorted(set(files))


def list_dirs_with_py() -> list[str]:
    """.py ファイルを含むディレクトリ一覧を返す"""
    dirs: set[str] = set()
    for p in list_test_files():
        dirs.add(str(Path(p).parent))
    return sorted(dirs)


def list_files_in_dir(directory: str) -> list[str]:
    """指定ディレクトリ内の .py ファイル一覧"""
    if not directory:
        return []
    return sorted(
        str(Path(p).name) for p in list_test_files() if str(Path(p).parent) == directory
    )


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
                    label="📄 ファイル名（保存先: NexusCore/sandbox_output/）",
                    placeholder="例: prime_checker.py（省略時: generated_code.py）",
                )
                save_result_display = gr.Textbox(
                    label="💾 保存結果",
                    interactive=False,
                    visible=True,
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

    def _extract_filename_from_code(code: str) -> str:
        """生成コードから関数名/クラス名を抽出してファイル名を生成する"""
        # クラス名を優先
        match = re.search(r"^class\s+(\w+)", code, re.MULTILINE)
        if match:
            return f"{match.group(1)}.py"
        # 関数名
        match = re.search(r"^def\s+(\w+)", code, re.MULTILINE)
        if match:
            return f"{match.group(1)}.py"
        # どちらもなければタイムスタンプ
        return f"generated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"

    def generate_code_handler(
        prompt: str, filename: str, current_state: AppState
    ) -> tuple[str, str, AppState]:
        """プロンプトからコードを生成"""
        if not prompt.strip():
            return "💡 プロンプトを入力してください。", filename, current_state

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
                generated = result.get("content", "") if result.get("ok") else f"❌ LLM Error: {result.get('reason', 'unknown')}"
                # マークダウンコードブロックを除去
                if generated.startswith("```"):
                    lines = generated.split("\n")
                    generated = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            else:
                generated = "❌ LLM Router が初期化されていません。APIキーを確認してください。"

            current_state.generated_code = generated

            # ファイル名が未入力の場合は自動生成
            auto_filename = filename.strip() if filename.strip() else _extract_filename_from_code(generated)
            current_state.current_file_path = auto_filename

            return generated, auto_filename, current_state
        except Exception as e:
            logger.error(f"Code generation failed: {e}", exc_info=True)
            return f"❌ エラー: {e}", filename, current_state

    def _generate_test_code(code: str, module_stem: str) -> str:
        """ソースコードからpytest形式のテストファイルを自動生成する"""
        # 関数名を全て抽出（プライベート関数除く）
        func_names = re.findall(r"^def\s+([a-zA-Z][a-zA-Z0-9_]*)\s*\(", code, re.MULTILINE)
        # クラス名を抽出
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
                "    \"\"\"モジュールが正常にインポートできることを確認\"\"\"",
                "    pass  # TODO: テストケースを追加してください",
            ]
        else:
            for fn in func_names:
                lines += [
                    f"def test_{fn}():",
                    f"    \"\"\"TODO: {fn}() のテストケースを追加してください\"\"\"",
                    f"    # result = {fn}(...)",
                    f"    # assert result == expected",
                    f"    pass",
                    "",
                ]

        return "\n".join(lines)

    def save_code_handler(
        code: str, filename: str, current_state: AppState
    ) -> tuple[str, AppState]:
        """コードを保存し、テストファイルも自動生成する"""
        if not code.strip():
            return "💡 コードが空です。", current_state

        try:
            file_path = filename or "generated_code.py"
            save_path = Path("sandbox_output") / file_path
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_text(code, encoding="utf-8")

            # テストファイルを自動生成
            module_stem = save_path.stem  # 例: is_prime
            test_filename = f"test_{module_stem}.py"
            test_path = Path("sandbox_output") / test_filename
            test_code = _generate_test_code(code, module_stem)
            test_path.write_text(test_code, encoding="utf-8")

            current_state.current_file_path = str(test_path)  # Test Runnerにはテストファイルを渡す
            current_state.generated_code = code
            current_state.before_code[str(save_path)] = code

            return (
                f"✅ 保存しました: {save_path}\n"
                f"🧪 テストファイル自動生成: {test_path}\n"
                f"（Test Runnerで「保存したファイルを使う」を押すと自動入力されます）"
            ), current_state
        except Exception as e:
            logger.error(f"Save failed: {e}", exc_info=True)
            return f"❌ エラー: {e}", current_state

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
                load_code_btn = gr.Button("📂 Code/Promptで生成したコードを読み込む", variant="secondary")

                code_input = gr.Code(
                    label="📝 修正対象コード",
                    language="python",
                    lines=20,
                    interactive=True,
                )

                revision_prompt = gr.Textbox(
                    label="💬 修正指示",
                    placeholder="例: 型ヒントを追加してください / エラーハンドリングを追加してください",
                    lines=5,
                )

                with gr.Row():
                    generate_patch_button = gr.Button("🔧 修正コードを生成", variant="primary")
                    apply_patch_button = gr.Button("✅ ファイルに書き戻す", variant="secondary")

            with gr.Column():
                patch_output = gr.Code(
                    label="📋 生成されたパッチ（Unified Diff）",
                    language=None,
                    lines=20,
                    interactive=False,
                )

                revision_result = gr.Textbox(
                    label="📊 修正結果",
                    lines=10,
                    interactive=False,
                )

    def load_generated_code(current_state: AppState) -> str:
        """AppStateから生成済みコードを読み込む"""
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
        """修正コードを生成"""
        code = (code or "").strip()
        prompt = (prompt or "").strip()
        if not code or not prompt:
            return "", "💡 コードと修正指示を両方入力してください。", current_state

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
                    return "", f"❌ LLM Error: {result.get('reason', 'unknown')}", current_state
                # マークダウンコードブロックを除去
                if revised.startswith("```"):
                    lines = revised.split("\n")
                    revised = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            else:
                return "", "❌ LLM Router が初期化されていません。", current_state

            return revised, "✅ 修正コードを生成しました。「ファイルに書き戻す」で保存できます。", current_state
        except Exception as e:
            logger.error(f"Patch generation failed: {e}", exc_info=True)
            return "", f"❌ エラー: {e}", current_state

    def apply_patch_handler(patch: str | None, current_state: AppState) -> tuple[str, AppState]:
        """修正コードをファイルに書き戻す"""
        patch = (patch or "").strip()
        if not patch:
            return "💡 修正コードが空です。先に「修正コードを生成」してください。", current_state

        try:
            # test_xxx.py ではなく元のソースファイルに書き戻す
            test_path = current_state.current_file_path or ""
            if test_path.startswith("sandbox_output/test_"):
                source_name = test_path.replace("sandbox_output/test_", "sandbox_output/")
            else:
                source_name = test_path

            file_path = Path(source_name) if source_name else None
            if file_path and file_path.exists():
                current_state.after_code[str(file_path)] = patch
                file_path.write_text(patch, encoding="utf-8")
                return f"✅ {file_path} に書き戻しました。", current_state
            else:
                return "❌ 書き戻し先ファイルが見つかりません。Code/Promptでコードを保存してから使ってください。", current_state
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

                use_saved_btn = gr.Button("📂 Code/Promptで保存したファイルを使う", variant="secondary")

                with gr.Row():
                    test_file_input = gr.Textbox(
                        label="📄 テストファイル（直接入力またはフォルダ/ファイルから選択）",
                        placeholder="例: sandbox_output/generated_code.py",
                        scale=3,
                    )
                    refresh_btn = gr.Button("🔄 一覧更新", scale=1)

                with gr.Row():
                    dir_dropdown = gr.Dropdown(
                        label="📁 フォルダ選択",
                        choices=list_dirs_with_py(),
                        interactive=True,
                        scale=1,
                    )
                    file_dropdown = gr.Dropdown(
                        label="📄 ファイル選択",
                        choices=[],
                        interactive=True,
                        scale=1,
                    )

                run_test_button = gr.Button("▶️ テスト実行", variant="primary")

            with gr.Column():
                test_output = gr.Textbox(
                    label="📊 テスト結果",
                    lines=25,
                    interactive=False,
                )

                test_status = gr.Markdown("**ステータス:** 未実行")

        # 「保存済みファイルを使う」ボタン → AppStateのcurrent_file_pathをtest_file_inputに反映
        def load_saved_file(current_state: AppState) -> str:
            if current_state.current_file_path:
                return current_state.current_file_path
            return "❌ まだファイルが保存されていません。Code/Promptタブでコードを保存してください。"

        use_saved_btn.click(
            fn=load_saved_file,
            inputs=[state],
            outputs=[test_file_input],
        )

        # フォルダ選択 → ファイル一覧更新
        dir_dropdown.change(
            fn=lambda d: gr.update(choices=list_files_in_dir(d)),
            inputs=[dir_dropdown],
            outputs=[file_dropdown],
        )
        # ファイル選択 → テキストボックスにフルパス反映
        file_dropdown.change(
            fn=lambda d, f: str(Path(d) / f) if d and f else "",
            inputs=[dir_dropdown, file_dropdown],
            outputs=[test_file_input],
        )
        # 更新ボタン → フォルダリスト再読み込み
        refresh_btn.click(
            fn=lambda: gr.update(choices=list_dirs_with_py()),
            outputs=[dir_dropdown],
        )

    def run_test_handler(
        command: str, test_file: str, current_state: AppState
    ) -> tuple[str, str, AppState]:
        """テストを実行"""
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
        cmd = [sys.executable, "-m", "pytest", "-q"]
        if test_file and test_file.strip():
            cmd.append(test_file)

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
    with gr.Blocks(title="NexusCore Unified UI") as demo:
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
        theme=gr.themes.Soft(),
    )


if __name__ == "__main__":
    launch_unified_ui()
