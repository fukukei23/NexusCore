"""
Additional comprehensive tests for vcs module to achieve 100% coverage.
Focuses on missing edge cases (lines 50-52: empty repository handling).
"""

import pytest
import git
from unittest.mock import patch, MagicMock, PropertyMock

from nexuscore.utils.vcs import GitController


# ==============================================================================
# Empty Repository Edge Case Tests (Missing Coverage Lines 50-52)
# ==============================================================================


class TestGitControllerEmptyRepo:
    """Test GitController with empty repository (no commits yet)"""

    @patch('nexuscore.utils.vcs.git.Repo')
    def test_commit_changes_empty_repo_value_error(self, mock_repo_class):
        """Commit to empty repository handles ValueError from no HEAD"""
        mock_repo = MagicMock()
        mock_index = MagicMock()

        # Mock repo.head.is_valid() to raise ValueError (empty repo)
        mock_head = PropertyMock(side_effect=ValueError("No HEAD"))
        type(mock_repo).head = mock_head

        mock_repo.index = mock_index
        mock_repo.working_dir = "/test/repo"
        mock_repo_class.return_value = mock_repo

        # Create controller
        controller = GitController()

        # Attempt commit (should handle ValueError gracefully)
        file_paths = ["test_file.py"]
        commit_message = "Initial commit"

        # Mock the commit to succeed
        mock_commit = MagicMock()
        mock_commit.hexsha = "abc123"
        mock_index.commit.return_value = mock_commit

        result = controller.commit_changes(file_paths, commit_message)

        # Should successfully commit even without HEAD
        assert result == "abc123"

    @patch('nexuscore.utils.vcs.git.Repo')
    def test_commit_changes_empty_repo_bad_name(self, mock_repo_class):
        """Commit to empty repository handles git.BadName exception"""
        mock_repo = MagicMock()
        mock_index = MagicMock()
        mock_head = MagicMock()

        # Mock is_valid() to raise git.BadName (empty repo with no HEAD)
        mock_head.is_valid.side_effect = git.BadName("HEAD")

        mock_repo.head = mock_head
        mock_repo.index = mock_index
        mock_repo.working_dir = "/test/repo"
        mock_repo_class.return_value = mock_repo

        controller = GitController()

        # Attempt commit
        file_paths = ["new_file.py"]
        commit_message = "First commit"

        # Mock successful commit
        mock_commit = MagicMock()
        mock_commit.hexsha = "def456"
        mock_index.commit.return_value = mock_commit

        result = controller.commit_changes(file_paths, commit_message)

        # Should handle BadName and proceed with commit
        assert result == "def456"

    @patch('nexuscore.utils.vcs.git.Repo')
    def test_commit_changes_empty_repo_with_files(self, mock_repo_class):
        """First commit to empty repository succeeds"""
        mock_repo = MagicMock()
        mock_index = MagicMock()

        # Simulate empty repo: HEAD doesn't exist
        mock_repo.head.is_valid.side_effect = git.BadName("HEAD")
        mock_repo.index = mock_index
        mock_repo.working_dir = "/test/repo"
        mock_repo_class.return_value = mock_repo

        controller = GitController()

        file_paths = ["README.md", "main.py"]
        commit_message = "Initial commit with files"

        # Mock commit
        mock_commit = MagicMock()
        mock_commit.hexsha = "initial123"
        mock_index.commit.return_value = mock_commit

        result = controller.commit_changes(file_paths, commit_message)

        # Verify files were staged
        mock_index.add.assert_called_once_with(file_paths)

        # Verify commit was made
        mock_index.commit.assert_called_once_with(commit_message)

        assert result == "initial123"

    @patch('nexuscore.utils.vcs.git.Repo')
    def test_commit_changes_non_empty_repo_with_diff(self, mock_repo_class):
        """Commit to non-empty repository with changes"""
        mock_repo = MagicMock()
        mock_index = MagicMock()
        mock_head = MagicMock()

        # Non-empty repo: HEAD is valid, has diff
        mock_head.is_valid.return_value = True
        mock_index.diff.return_value = ["diff1", "diff2"]  # Has changes

        mock_repo.head = mock_head
        mock_repo.index = mock_index
        mock_repo.working_dir = "/test/repo"
        mock_repo_class.return_value = mock_repo

        controller = GitController()

        file_paths = ["modified.py"]
        commit_message = "Update file"

        # Mock commit
        mock_commit = MagicMock()
        mock_commit.hexsha = "update789"
        mock_index.commit.return_value = mock_commit

        result = controller.commit_changes(file_paths, commit_message)

        # Verify HEAD diff was checked
        mock_index.diff.assert_called_once_with("HEAD")

        assert result == "update789"

    @patch('nexuscore.utils.vcs.git.Repo')
    def test_commit_changes_non_empty_repo_no_diff(self, mock_repo_class):
        """Commit to non-empty repository with no changes returns None"""
        mock_repo = MagicMock()
        mock_index = MagicMock()
        mock_head = MagicMock()

        # Non-empty repo: HEAD is valid, but no diff
        mock_head.is_valid.return_value = True
        mock_index.diff.return_value = []  # No changes

        mock_repo.head = mock_head
        mock_repo.index = mock_index
        mock_repo.working_dir = "/test/repo"
        mock_repo_class.return_value = mock_repo

        controller = GitController()

        file_paths = ["unchanged.py"]
        commit_message = "No changes"

        result = controller.commit_changes(file_paths, commit_message)

        # Should return None when no changes
        assert result is None

        # Verify commit was not called
        mock_index.commit.assert_not_called()


# ==============================================================================
# Additional Edge Cases for Complete Coverage
# ==============================================================================


class TestGitControllerAdditionalCases:
    """Additional edge case tests"""

    @patch('nexuscore.utils.vcs.git.Repo')
    def test_commit_changes_empty_file_list(self, mock_repo_class):
        """Empty file list returns None"""
        mock_repo = MagicMock()
        mock_repo.working_dir = "/test/repo"
        mock_repo_class.return_value = mock_repo

        controller = GitController()

        result = controller.commit_changes([], "Empty commit")

        assert result is None

    @patch('nexuscore.utils.vcs.git.Repo')
    def test_commit_changes_exception_during_add(self, mock_repo_class):
        """Exception during git add returns None"""
        mock_repo = MagicMock()
        mock_index = MagicMock()

        # Simulate exception during add
        mock_index.add.side_effect = Exception("Add failed")

        mock_repo.index = mock_index
        mock_repo.working_dir = "/test/repo"
        mock_repo_class.return_value = mock_repo

        controller = GitController()

        result = controller.commit_changes(["file.py"], "Commit message")

        # Should return None on exception
        assert result is None

    @patch('nexuscore.utils.vcs.git.Repo')
    def test_commit_changes_exception_during_commit(self, mock_repo_class):
        """Exception during git commit returns None"""
        mock_repo = MagicMock()
        mock_index = MagicMock()
        mock_head = MagicMock()

        # Setup successful add but failed commit
        mock_head.is_valid.return_value = True
        mock_index.diff.return_value = ["change"]
        mock_index.commit.side_effect = Exception("Commit failed")

        mock_repo.head = mock_head
        mock_repo.index = mock_index
        mock_repo.working_dir = "/test/repo"
        mock_repo_class.return_value = mock_repo

        controller = GitController()

        result = controller.commit_changes(["file.py"], "Commit message")

        # Should return None on commit exception
        assert result is None

    @patch('nexuscore.utils.vcs.git.Repo')
    def test_commit_changes_multiple_files(self, mock_repo_class):
        """Commit multiple files successfully"""
        mock_repo = MagicMock()
        mock_index = MagicMock()

        # Empty repo scenario
        mock_repo.head.is_valid.side_effect = ValueError("No HEAD")
        mock_repo.index = mock_index
        mock_repo.working_dir = "/test/repo"
        mock_repo_class.return_value = mock_repo

        controller = GitController()

        file_paths = ["file1.py", "file2.py", "file3.py"]

        mock_commit = MagicMock()
        mock_commit.hexsha = "multi123"
        mock_index.commit.return_value = mock_commit

        result = controller.commit_changes(file_paths, "Add multiple files")

        # Verify all files were added
        mock_index.add.assert_called_once_with(file_paths)

        assert result == "multi123"

    @patch('nexuscore.utils.vcs.git.Repo')
    def test_git_controller_invalid_repo(self, mock_repo_class):
        """GitController raises exception for invalid repository"""
        # Mock Repo to raise InvalidGitRepositoryError
        mock_repo_class.side_effect = git.InvalidGitRepositoryError("/invalid/path")

        with pytest.raises(git.InvalidGitRepositoryError):
            GitController(repo_path="/invalid/path")

    @patch('nexuscore.utils.vcs.git.Repo')
    def test_git_controller_prints_success_message(self, mock_repo_class, capsys):
        """GitController prints success message on init"""
        mock_repo = MagicMock()
        mock_repo.working_dir = "/test/repo"
        mock_repo_class.return_value = mock_repo

        GitController()

        captured = capsys.readouterr()
        assert "✅" in captured.out
        assert "Gitリポジトリを正常に読み込みました" in captured.out

    @patch('nexuscore.utils.vcs.git.Repo')
    def test_commit_changes_prints_staging_message(self, mock_repo_class, capsys):
        """commit_changes prints staging message"""
        mock_repo = MagicMock()
        mock_index = MagicMock()

        mock_repo.head.is_valid.side_effect = ValueError("No HEAD")
        mock_repo.index = mock_index
        mock_repo.working_dir = "/test/repo"
        mock_repo_class.return_value = mock_repo

        controller = GitController()

        mock_commit = MagicMock()
        mock_commit.hexsha = "test123"
        mock_index.commit.return_value = mock_commit

        capsys.readouterr()  # Clear previous output

        controller.commit_changes(["file.py"], "Test commit")

        captured = capsys.readouterr()
        assert "ステージングします" in captured.out

    @patch('nexuscore.utils.vcs.git.Repo')
    def test_commit_changes_prints_success_message(self, mock_repo_class, capsys):
        """commit_changes prints success message with commit hash"""
        mock_repo = MagicMock()
        mock_index = MagicMock()

        mock_repo.head.is_valid.side_effect = ValueError("No HEAD")
        mock_repo.index = mock_index
        mock_repo.working_dir = "/test/repo"
        mock_repo_class.return_value = mock_repo

        controller = GitController()

        mock_commit = MagicMock()
        mock_commit.hexsha = "abc123def"
        mock_index.commit.return_value = mock_commit

        capsys.readouterr()  # Clear previous output

        controller.commit_changes(["file.py"], "Test commit")

        captured = capsys.readouterr()
        assert "✅" in captured.out
        assert "正常にコミットされました" in captured.out
        assert "abc123def" in captured.out

    @patch('nexuscore.utils.vcs.git.Repo')
    def test_git_controller_invalid_git_repo_error_message(self, mock_repo_class, capsys):
        """GitController prints error message for invalid repository"""
        # Mock Repo to raise InvalidGitRepositoryError
        mock_repo_class.side_effect = git.InvalidGitRepositoryError("/not/a/repo")

        capsys.readouterr()  # Clear previous output

        with pytest.raises(git.InvalidGitRepositoryError):
            GitController(repo_path="/not/a/repo")

        captured = capsys.readouterr()
        assert "❌" in captured.out
        assert "エラー" in captured.out
        assert "有効なGitリポジトリではありません" in captured.out
        assert "/not/a/repo" in captured.out
