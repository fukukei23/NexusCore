# --- FILE: src/app.py ---
# メインアプリケーション: FlaskサーバーとGradio UI

import os
import threading
from pathlib import Path

import gradio as gr
from flask import Flask, jsonify, request

from dotenv import load_dotenv

# --- ローカルモジュールのインポート ---
from .git_manager import GitManager, get_file_diff
from .ai_assistant import AIAssistant
from .agents.guardian_agent import GuardianAgent

# --- 初期化 ---
load_dotenv()

# ディレクトリ構造の定義
ROOT = Path(__file__).parent.parent.resolve()
SANDBOX_REPO_PATH = ROOT / "sandbox_repo"

# モジュールのインスタンス化
if not SANDBOX_REPO_PATH.exists():
    SANDBOX_REPO_PATH.mkdir()

if not (SANDBOX_REPO_PATH / ".git").exists():
    print("⚠️ Gitリポジトリが初期化されていません。")
    git_manager = GitManager.initialize_repo(SANDBOX_REPO_PATH)
    print(f"✅ '{SANDBOX_REPO_PATH}' にGitリポジトリを初期化しました。")
else:
    git_manager = GitManager(repo_path=SANDBOX_REPO_PATH)

ai_assistant = AIAssistant(api_key=os.getenv("OPENAI_API_KEY"))

# --- Flaskアプリケーション ---
flask_app = Flask(__name__)

@flask_app.route("/api/status", methods=['GET'])
def get_status():
    """リポジトリの現在の状態を返すAPI"""
    history = git_manager.get_history(limit=10)
    return jsonify({
        "repo_path": str(git_manager.repo_path),
        "current_branch": git_manager.get_current_branch(),
        "recent_history": history
    })

# --- Gradio UIのためのバックエンド関数 ---

def get_history_and_files():
    """UI表示用に履歴とファイルリストを取得"""
    history = git_manager.get_history_for_ui()
    
    if history.empty:
        print("🚀 初回起動シーケンスを開始します。")
        app_dir = SANDBOX_REPO_PATH / "app"
        tests_dir = SANDBOX_REPO_PATH / "tests"
        app_dir.mkdir(exist_ok=True)
        tests_dir.mkdir(exist_ok=True)
        (tests_dir / "__init__.py").touch()
        (SANDBOX_REPO_PATH / "pyproject.toml").write_text("""[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
addopts = "--cov"
[tool.coverage.run]
source = ["app"]
omit = ["*/__init__.py"]
[tool.coverage.report]
fail_under = 90
""", encoding='utf-8')
        git_manager.write_file_and_commit("app/main.py", "# Add your main code here", "feat: Initial commit with app/main.py")
        git_manager.write_file_and_commit("tests/test_main.py", "# Add tests for main.py here", "feat: Initial commit with tests/test_main.py")
        history = git_manager.get_history_for_ui()
        
    files = git_manager.get_tracked_files()
    return history, files

def run_tests_on_current_code():
    """現在の作業ディレクトリのコードに対してテストを実行"""
    return git_manager.run_pytest(project_path=str(SANDBOX_REPO_PATH))

def propose_ai_fix(target_file, user_instruction, history_df):
    """AIにコードの修正案を提案させる"""
    latest_commit_hash = history_df.iloc[0]['commit'] if not history_df.empty else 'HEAD'
    
    current_code = git_manager.read_file(target_file, commit_hash=latest_commit_hash)
    test_file_path = "tests/test_" + os.path.basename(target_file)
    test_code = git_manager.read_file(test_file_path, commit_hash=latest_commit_hash)
    test_results = git_manager.run_pytest(project_path=str(SANDBOX_REPO_PATH))

    ai_response = ai_assistant.generate_fix(
        target_file=target_file,
        current_code=current_code,
        test_code=test_code,
        test_results=test_results,
        user_instruction=user_instruction
    )
    
    suggested_code = ai_response.get("code", "")
    summary = ai_response.get("summary", "要約の生成に失敗しました。")
    diff_html = get_file_diff(current_code, suggested_code, target_file)
    
    return summary, suggested_code, diff_html, gr.update(interactive=True)

def accept_ai_suggestion(target_file, suggested_code, summary):
    """AIの提案を受け入れ、コミットする前にガーディアンAIのレビューを実行する"""
    if not suggested_code:
        return "提案されたコードが空のため、コミットできませんでした。", gr.update()

    current_code = git_manager.read_file(target_file)
    git_manager.write_file(target_file, suggested_code)

    constitution = {
        'min_pylint_score': 7.0,
        'min_coverage_percent': 90.0,
    }
    
    test_file_path = "tests/test_" + os.path.basename(target_file)

    guardian = GuardianAgent(constitution=constitution)
    
    # ✅ 修正点: 不要な 'project_path' 引数を削除
    approved, report = guardian.review_changes(
        code_file_path=target_file,
        test_file_path=test_file_path
    )
    
    if approved:
        commit_message = f"AI提案の適用 (Guardian承認済): {summary}"
        git_manager.commit(commit_message)
        return f"✅ ガーディアンAIが承認。新バージョンをコミットしました。\n\n{report}", git_manager.get_history_for_ui()
    else:
        git_manager.write_file(target_file, current_code)
        return f"❌ ガーディアンAIが却下。コミットは行われませんでした。\n\n{report}", gr.update()

def revert_to_version(commit_hash):
    """指定されたバージョンにロールバックする"""
    if not commit_hash or len(commit_hash) < 7:
        return "コミットハッシュが選択されていません。", gr.update()
    
    try:
        full_hash = git_manager.repo.git.rev_parse(commit_hash)
        git_manager.checkout(full_hash)
        files = git_manager.get_tracked_files()
        return f"✅ バージョン {commit_hash[:7]} にロールバックしました。", gr.update(choices=files)
    except Exception as e:
        return f"❌ ロールバック中にエラーが発生しました: {e}", gr.update()

# --- Gradio UIの構築 ---
def create_gradio_app():
    with gr.Blocks(theme=gr.themes.Soft(), css="""
        .diff-container { padding: 10px; border-radius: 5px; background-color: #f0f0f0; font-family: monospace; white-space: pre-wrap; }
        .diff-add { background-color: #e6ffed; }
        .diff-remove { background-color: #ffebe9; }
    """) as app:
        gr.Markdown("# 🚀 究極のAIアシスト型バージョン管理システム")
        
        ai_suggestion_code = gr.State("")
        ai_suggestion_summary = gr.State("")
        
        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("### 📜 バージョン履歴")
                history_table = gr.DataFrame(headers=["commit", "author", "date", "message"], interactive=False, datatype=["str", "str", "str", "str"])
                
                with gr.Accordion("🔁 ロールバック", open=False):
                    selected_commit = gr.Dropdown(label="戻したいバージョンを選択", choices=[])
                    rollback_btn = gr.Button("このバージョンに戻す")

            with gr.Column(scale=3):
                gr.Markdown("### 🤖 AIによるコード修正")
                target_file_dropdown = gr.Dropdown(label="修正対象ファイル", interactive=True)
                user_instruction_textbox = gr.Textbox(label="追加の指示・修正したい内容", lines=3, placeholder="例: バグを修正して、パフォーマンスを改善してください。")
                propose_fix_btn = gr.Button("🤖 AIに修正案を提案させる", variant="primary")
                
                with gr.Accordion("🔍 AIの提案内容", open=True):
                    ai_summary_output = gr.Markdown(label="AIによる修正の要約")
                    diff_output = gr.HTML(label="差分プレビュー (緑: 追加, 赤: 削除)")

                with gr.Row():
                    accept_btn = gr.Button("✅ この修正を承認する", variant="primary", interactive=False)

            with gr.Column(scale=2):
                gr.Markdown("### 🧪 テスト実行")
                run_test_btn = gr.Button("現在のコードでテストを実行")
                test_result_output = gr.Textbox(label="📊 テスト結果", lines=10, interactive=False)
                
                with gr.Accordion("📄 ファイル内容の確認", open=False):
                    file_content_display = gr.Code(label="ファイル内容", language="python", interactive=False)

        def initial_load():
            history, files = get_history_and_files()
            commit_choices = history['commit'].tolist() if not history.empty else []
            return history, gr.update(choices=files, value=files[0] if files else None), gr.update(choices=commit_choices)
        
        app.load(initial_load, outputs=[history_table, target_file_dropdown, selected_commit])

        propose_fix_btn.click(
            fn=propose_ai_fix,
            inputs=[target_file_dropdown, user_instruction_textbox, history_table],
            outputs=[ai_summary_output, ai_suggestion_code, diff_output, accept_btn],
            show_progress="full"
        ).then(
            fn=lambda summary, code: (summary, code),
            inputs=[ai_summary_output, ai_suggestion_code],
            outputs=[ai_suggestion_summary, ai_suggestion_code]
        )

        accept_btn.click(
            fn=accept_ai_suggestion,
            inputs=[target_file_dropdown, ai_suggestion_code, ai_suggestion_summary],
            outputs=[test_result_output, history_table],
            show_progress="full"
        ).then(
            lambda: ("", "", "", gr.update(interactive=False)),
            outputs=[ai_summary_output, diff_output, ai_suggestion_code, accept_btn]
        )

        run_test_btn.click(fn=run_tests_on_current_code, outputs=test_result_output)
        
        rollback_btn.click(
            fn=revert_to_version,
            inputs=[selected_commit],
            outputs=[test_result_output, target_file_dropdown]
        ).then(
            fn=initial_load, 
            outputs=[history_table, target_file_dropdown, selected_commit]
        )
        
        def show_file_content(filepath):
            if not filepath: return ""
            return git_manager.read_file(filepath, "HEAD")

        target_file_dropdown.change(
            fn=show_file_content,
            inputs=[target_file_dropdown],
            outputs=file_content_display
        )

    return app

# --- アプリケーションの起動 ---
if __name__ == "__main__":
    gradio_app = create_gradio_app()
    
    threading.Thread(
        target=lambda: gradio_app.launch(server_name="0.0.0.0", server_port=7860, quiet=True),
        daemon=True
    ).start()
    print("✅ Gradio UIが http://127.0.0.1:7860 で起動しました。")

    print("✅ Flask APIサーバーが http://127.0.0.1:5000 で起動しました。")
    flask_app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)