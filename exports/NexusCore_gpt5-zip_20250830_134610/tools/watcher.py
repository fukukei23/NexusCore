# ==============================================================================
# フォルダ: tools/
# ファイル名: watcher.py
# メモ: v3.0 - 変更差分をLLMに送り、開発内容の要約を自動生成・記録する完全自動版。
#
# 使い方:
# python tools/watcher.py
# ==============================================================================
import time
import logging
from collections import deque
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
import threading
import pathspec
import git # GitPythonをインポート

# Chronicle Scribeの記録機能をインポート
from scribe import log_manual_event

# --- 設定 ---
PROMPT_DELAY_SECONDS = 600 # 10分
RECENT_FILES_LIMIT = 20

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# ==============================================================================
# ★★★★★ 要実装 ★★★★★
# ==============================================================================
def summarize_changes_with_llm(diff_text: str, file_list: list) -> str:
    """
    LLMを呼び出して、コードの差分から作業内容の要約を生成する。
    """
    logging.info("LLMに作業内容の要約を問い合わせ中...")
    
    prompt = f"""
    あなたは、チームの開発状況を常に把握している、優秀なテックリードです。
    以下のファイル変更の差分（diff）を分析し、開発者がどのような作業をしていたかを、
    gitのコミットメッセージのように簡潔な一行で要約してください。

    # 変更されたファイルリスト
    {', '.join(file_list)}

    # 変更内容の差分
    ```diff
    {diff_text}
    ```

    # 出力指示
    - 要約のみを、一行のテキストで出力してください。
    - 例: feat(agent): Watcher Agentに自己要約機能を追加
    - 例: fix(scribe): ファイルパスの解決ロジックを修正
    """
    
    # 【要実装】ここに、お客様の環境に合わせたLLM呼び出しコードを記述してください。
    # 例:
    # from your_llm_client import call_gemini
    # return call_gemini(prompt)

    logging.warning("現在、LLM呼び出しはモックアップです。`summarize_changes_with_llm`を実装してください。")
    mock_summary = f"feat(auto-summary): {', '.join(file_list)} を自動的に要約しました。"
    return mock_summary
# ==============================================================================

def load_gitignore_patterns(project_root: str):
    # (v2.0から変更なし)
    gitignore_path = os.path.join(project_root, ".gitignore")
    patterns = []
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r", encoding="utf-8") as f:
            patterns = f.read().splitlines()
    patterns.extend([".git/", "__pycache__/", "*.pyc", "project_chronicle.jsonl", ".idea/", ".vscode/"])
    return pathspec.PathSpec.from_lines('gitwildmatch', patterns)

class DevelopmentEventHandler(FileSystemEventHandler):
    def __init__(self, project_root: str, ignore_spec: pathspec.PathSpec, repo: git.Repo):
        self.project_root = project_root
        self.ignore_spec = ignore_spec
        self.repo = repo
        self.prompt_timer = None
        self.recently_modified_files = deque(maxlen=RECENT_FILES_LIMIT)
        self.lock = threading.Lock()

    def on_modified(self, event):
        # (v2.0から変更なし)
        if event.is_directory: return
        rel_path = os.path.relpath(event.src_path, self.project_root)
        if self.ignore_spec.match_file(rel_path): return

        with self.lock:
            logging.info(f"ファイル変更を検知: {rel_path}")
            if rel_path not in self.recently_modified_files:
                self.recently_modified_files.append(rel_path)
            if self.prompt_timer: self.prompt_timer.cancel()
            self.prompt_timer = threading.Timer(PROMPT_DELAY_SECONDS, self._trigger_auto_summary)
            self.prompt_timer.start()

    def _trigger_auto_summary(self):
        with self.lock:
            if not self.recently_modified_files: return

            logging.info("開発活動の停止を検知。作業内容の自動要約を開始します。")
            
            # 差分を取得
            try:
                # HEAD (最新コミット) との差分を取得
                diff_text = self.repo.git.diff('HEAD', *self.recently_modified_files)
                if not diff_text:
                    logging.info("差分がありませんでした。記録をスキップします。")
                    self.recently_modified_files.clear()
                    return
            except git.exc.GitCommandError as e:
                logging.error(f"Git差分の取得に失敗しました: {e}")
                self.recently_modified_files.clear()
                return

            # LLMで要約を生成
            summary = summarize_changes_with_llm(diff_text, list(self.recently_modified_files))

            # クロニクルに記録
            if summary:
                log_manual_event(self.project_root, summary)
            
            self.recently_modified_files.clear()

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    try:
        repo = git.Repo(project_root)
    except git.InvalidGitRepositoryError:
        logging.error(f"Gitリポジトリが見つかりません: {project_root}")
        logging.error("Watcher Agent v3.0は、差分を検知するためにGit管理下にある必要があります。")
        return

    logging.info(f"🤖 Watcher Agent v3.0 (自己要約モード) を起動します。")
    ignore_spec = load_gitignore_patterns(project_root)
    
    event_handler = DevelopmentEventHandler(project_root, ignore_spec, repo)
    observer = Observer()
    observer.schedule(event_handler, project_root, recursive=True)
    observer.start()

    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logging.info("\n👋 Watcher Agentを停止します。")
    observer.join()

if __name__ == "__main__":
    main()
