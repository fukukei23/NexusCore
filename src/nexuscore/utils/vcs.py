import git
import logging

_logger = logging.getLogger(__name__)


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
            _logger.info("Git repository loaded: %s", self.repo.working_dir)
        except git.InvalidGitRepositoryError:
            _logger.error("'%s' is not a valid Git repository", repo_path)
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
                _logger.info("No changes (no files specified for commit).")
                return None

            # ファイルをステージング
            _logger.info("Staging files: %s", file_paths)
            self.repo.index.add(file_paths)

            # 変更があるかどうかを確認（ステージング後）
            # 空のリポジトリ（HEADがない）の場合はスキップ
            try:
                if self.repo.head.is_valid() and not self.repo.index.diff("HEAD"):
                    _logger.info("No changes in staged files to commit.")
                    return None
            except (ValueError, git.BadName):
                # 空のリポジトリの場合はHEADがないので続行
                pass

            commit = self.repo.index.commit(message)
            _logger.info("Committed successfully: %s", commit.hexsha)
            return commit.hexsha
        except Exception as e:
            _logger.error("Error during git commit: %s", e)
            return None
