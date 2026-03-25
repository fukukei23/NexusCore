import git


class GitController:
    """
    Gitリポジトリの操作を管理するクラス。
    """

    def __init__(self, repo_path="."):
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
            # 空のファイルリストの場合は処理しない
            if not file_paths:
                # 既存テストは「変更がありません」または「エラー」を期待するため、表現を合わせる
                print("変更がありません（コミット対象のファイルが指定されていません）。")
                return None

            # ファイルをステージング
            print(f"以下のファイルをステージングします: {file_paths}")
            self.repo.index.add(file_paths)

            # 変更があるかどうかを確認（ステージング後）
            # 空のリポジトリ（HEADがない）の場合はスキップ
            try:
                if self.repo.head.is_valid() and not self.repo.index.diff("HEAD"):
                    print("ℹ️ コミット対象のファイルの変更がありません。")
                    return None
            except (ValueError, git.BadName):
                # 空のリポジトリの場合はHEADがないので続行
                pass

            commit = self.repo.index.commit(message)
            print(f"✅ 正常にコミットされました: {commit.hexsha}")
            return commit.hexsha
        except Exception as e:
            print(f"❌ Gitコミット中にエラーが発生しました: {e}")
            return None
