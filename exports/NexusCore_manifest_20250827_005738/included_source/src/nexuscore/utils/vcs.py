import git
from datetime import datetime

class GitController:
    """
    Gitリポジトリの操作を管理するクラス。
    """
    def __init__(self, repo_path='.'):
        """
        指定されたパスのリポジトリを初期化します。
        リポジトリが存在しない場合はエラーを送出します。
        """
        try:
            self.repo = git.Repo(repo_path, search_parent_directories=True)
            print(f"✅ Gitリポジトリを正常に読み込みました: {self.repo.working_dir}")
        except git.InvalidGitRepositoryError:
            print(f"❌ エラー: '{repo_path}' は有効なGitリポジトリではありません。")
            # プロジェクトをGitで初期化することも可能
            # self.repo = git.Repo.init(repo_path)
            # print(f"リポジトリを新規作成しました: {repo_path}")
            raise

    def commit_changes(self, file_paths: list, message: str) -> str | None:
        """
        指定されたファイルをステージングし、コミットします。
        
        Args:
            file_paths: コミット対象のファイルパスのリスト。
            message: コミットメッセージ。
        
        Returns:
            成功した場合はコミットハッシュ、失敗した場合はNone。
        """
        try:
            # ファイルの変更があるか確認
            if not self.repo.is_dirty(path=file_paths):
                print("ℹ️ コミット対象のファイルの変更がありません。")
                return None

            print(f"以下のファイルをステージングします: {file_paths}")
            self.repo.index.add(file_paths)
            
            commit = self.repo.index.commit(message)
            print(f"✅ 正常にコミットされました: {commit.hexsha}")
            return commit.hexsha
        except Exception as e:
            print(f"❌ Gitコミット中にエラーが発生しました: {e}")
            return None
