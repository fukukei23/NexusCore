# ==============================================================================
# フォルダ: src
# ファイル名: git_manager.py
# ==============================================================================
import subprocess
from pathlib import Path
import pandas as pd
import git
import difflib

class GitManager:
    """Gitリポジトリの操作を管理するクラス"""
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path.resolve()
        try:
            self.repo = git.Repo(self.repo_path)
        except git.InvalidGitRepositoryError:
            raise ValueError(f"指定されたパス '{self.repo_path}' は有効なGitリポジトリではありません。")

    @staticmethod
    def initialize_repo(repo_path: Path):
        """新しいGitリポジトリを初期化する"""
        git.Repo.init(repo_path)
        # ◀️ ここが修正点！ 初期化後に自分自身のインスタンスを返す
        return GitManager(repo_path)

    def get_current_branch(self):
        """現在のブランチ名を取得する"""
        return self.repo.active_branch.name

    def write_file_and_commit(self, file_path: str, content: str, message: str):
        """ファイルに書き込み、ステージングし、コミットする"""
        full_path = self.repo_path / file_path
        
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        self.repo.index.add([file_path])
        self.repo.index.commit(message)

    def read_file(self, file_path: str, commit_hash: str = 'HEAD') -> str:
        """指定されたコミットからファイルの内容を読み込む"""
        try:
            if commit_hash == 'HEAD':
                # HEADの場合、作業ディレクトリの現在のファイルを読み込む
                current_path = self.repo_path / file_path
                if current_path.exists():
                    return current_path.read_text(encoding='utf-8')
                return "" # ファイルが存在しない場合は空文字
            
            commit = self.repo.commit(commit_hash)
            blob = commit.tree / file_path
            return blob.data_stream.read().decode('utf-8')
        except (KeyError, git.exc.GitCommandError):
            return ""

    def get_history(self, limit: int = 20) -> list[dict]:
        """コミット履歴をリストとして取得する"""
        if not self.repo.head.is_valid(): # コミットがまだない場合
            return []
        history = []
        for commit in self.repo.iter_commits(max_count=limit):
            history.append({
                "commit": commit.hexsha,
                "author": commit.author.name,
                "date": commit.committed_datetime.isoformat(),
                "message": commit.message.strip(),
            })
        return history
    
    def get_history_for_ui(self) -> pd.DataFrame:
        """GradioのDataFrame用にコミット履歴を整形する"""
        history = self.get_history()
        if not history:
            return pd.DataFrame(columns=["commit", "author", "date", "message"])
        df = pd.DataFrame(history)
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d %H:%M')
        df['message'] = df['message'].str.split('\n').str[0]
        # commit_shortカラムを削除し、commitカラムを7文字に制限
        df['commit'] = df['commit'].str[:7]
        df = df[['commit', 'author', 'date', 'message']]
        return df

    def get_tracked_files(self) -> list[str]:
        """リポジトリで追跡されているファイルの一覧を取得する"""
        if not self.repo.head.is_valid():
            return []
        # 'git ls-files'をGitPython経由で実行
        return self.repo.git.ls_files().splitlines()

    def checkout(self, commit_or_branch: str):
        """指定されたコミットまたはブランチにチェックアウトする"""
        self.repo.git.checkout(commit_or_branch)
        
    # --- write_fileとcommitを分離 ---
    def write_file(self, file_path: str, content: str):
        """ファイルへの書き込みのみを行う"""
        full_path = self.repo_path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding='utf-8')

    def commit(self, message: str, add_all: bool = True):
        """変更をコミットする"""
        if add_all:
            self.repo.index.add(self.repo.untracked_files)
            self.repo.index.add([item.a_path for item in self.repo.index.diff(None)])
        self.repo.index.commit(message)
        
    def run_pytest(self, project_path: str) -> str:
        """リポジトリ内でpytestを実行する"""
        try:
            result = subprocess.run(
                ["pytest"], cwd=project_path, capture_output=True,
                text=True, encoding="utf-8", timeout=30
            )
            output = "--- stdout ---\n" + (result.stdout or "（なし）")
            if result.stderr:
                output += "\n\n--- stderr ---\n" + result.stderr
            return output
        except FileNotFoundError:
            return "❌ `pytest` コマンドが見つかりません。インストールされているか確認してください。"
        except Exception as e:
            return f"❌ テスト実行中に予期せぬエラーが発生しました: {e}"

def get_file_diff(old_content: str, new_content: str, filename: str) -> str:
    """2つのテキストの差分をHTML形式で生成する"""
    diff = difflib.unified_diff(
        old_content.splitlines(keepends=True),
        new_content.splitlines(keepends=True), fromfile=f"a/{filename}", tofile=f"b/{filename}"
    )
    html = '<div class="diff-container">'
    has_changes = False
    for line in diff:
        has_changes = True
        line_escaped = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if line.startswith('+'):
            html += f'<div class="diff-add">{line_escaped}</div>'
        elif line.startswith('-'):
            html += f'<div class="diff-remove">{line_escaped}</div>'
        elif line.startswith('@@'):
            html += f'<div><strong>{line_escaped}</strong></div>'
        else:
            html += f'<div>{line_escaped}</div>'
    html += '</div>'
    return html if has_changes else "変更はありません。"