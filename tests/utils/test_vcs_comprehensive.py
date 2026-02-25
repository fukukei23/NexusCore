"""
Comprehensive tests for vcs (Version Control System) module.
Covers GitController initialization, commit operations, and error handling.
"""

from unittest.mock import MagicMock, patch

import git
import pytest

from nexuscore.utils.vcs import GitController

# ==============================================================================
# GitController Initialization Tests
# ==============================================================================


class TestGitControllerInit:
    """Test GitController initialization"""

    def test_init_with_valid_repo(self, tmp_path):
        """Initialize with valid git repository"""
        # Create a git repo
        git.Repo.init(tmp_path)

        # Initialize GitController
        controller = GitController(str(tmp_path))

        assert controller.repo is not None
        assert controller.repo.working_dir == str(tmp_path)

    def test_init_searches_parent_directories(self, tmp_path):
        """Initialize searches parent directories for .git"""
        # Create git repo in parent
        git.Repo.init(tmp_path)

        # Create subdirectory
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        # Initialize from subdirectory
        controller = GitController(str(subdir))

        assert controller.repo is not None
        assert controller.repo.working_dir == str(tmp_path)

    def test_init_with_invalid_repo_raises_error(self, tmp_path):
        """Initialize with non-git directory raises error"""
        # Create non-git directory
        non_git_dir = tmp_path / "not_a_repo"
        non_git_dir.mkdir()

        with pytest.raises(git.InvalidGitRepositoryError):
            GitController(str(non_git_dir))

    def test_init_with_current_directory(self):
        """Initialize with current directory (default)"""
        # This assumes we're in a git repo (which we are)
        controller = GitController()

        assert controller.repo is not None

    def test_init_with_nonexistent_path_raises_error(self):
        """Initialize with nonexistent path raises error"""
        with pytest.raises(
            (git.InvalidGitRepositoryError, git.GitCommandError, git.NoSuchPathError)
        ):
            GitController("/nonexistent/path/to/repo")


# ==============================================================================
# GitController commit_changes Tests
# ==============================================================================


class TestGitControllerCommitChanges:
    """Test GitController commit_changes method"""

    def test_commit_single_file(self, tmp_path):
        """Commit a single file successfully"""
        # Setup git repo
        repo = git.Repo.init(tmp_path)

        # Create and modify a file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        # Initialize controller
        controller = GitController(str(tmp_path))

        # Commit the file
        commit_hash = controller.commit_changes(["test.txt"], "Add test file")

        assert commit_hash is not None
        assert len(commit_hash) == 40  # SHA-1 hash length

        # Verify commit exists
        commit = repo.commit(commit_hash)
        assert commit.message == "Add test file"

    def test_commit_multiple_files(self, tmp_path):
        """Commit multiple files successfully"""
        # Setup git repo
        repo = git.Repo.init(tmp_path)

        # Create multiple files
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("Content 1")
        file2.write_text("Content 2")

        controller = GitController(str(tmp_path))

        # Commit both files
        commit_hash = controller.commit_changes(["file1.txt", "file2.txt"], "Add two files")

        assert commit_hash is not None

        # Verify both files are in commit
        commit = repo.commit(commit_hash)
        assert len(commit.stats.files) == 2

    def test_commit_with_no_changes_returns_none(self, tmp_path):
        """Commit with no changes returns None"""
        # Setup git repo
        repo = git.Repo.init(tmp_path)

        # Create and commit a file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Initial content")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial commit")

        controller = GitController(str(tmp_path))

        # Try to commit same file without changes
        result = controller.commit_changes(["test.txt"], "No changes commit")

        assert result is None

    def test_commit_with_multiline_message(self, tmp_path):
        """Commit with multiline message"""
        # Setup git repo
        repo = git.Repo.init(tmp_path)

        # Create file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")

        controller = GitController(str(tmp_path))

        # Commit with multiline message
        multiline_message = """Add test file

This is a detailed commit message
with multiple lines.

- Added test.txt
- Contains test content"""

        commit_hash = controller.commit_changes(["test.txt"], multiline_message)

        assert commit_hash is not None

        # Verify message
        commit = repo.commit(commit_hash)
        assert commit.message == multiline_message

    def test_commit_with_unicode_message(self, tmp_path):
        """Commit with Unicode characters in message"""
        # Setup git repo
        repo = git.Repo.init(tmp_path)

        # Create file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Content")

        controller = GitController(str(tmp_path))

        # Commit with Unicode message
        unicode_message = "日本語のコミットメッセージ 🎉"
        commit_hash = controller.commit_changes(["test.txt"], unicode_message)

        assert commit_hash is not None
        commit = repo.commit(commit_hash)
        assert commit.message == unicode_message

    def test_commit_modified_file(self, tmp_path):
        """Commit a modified file"""
        # Setup git repo
        repo = git.Repo.init(tmp_path)

        # Create and commit initial version
        test_file = tmp_path / "test.txt"
        test_file.write_text("Version 1")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial version")

        # Modify file
        test_file.write_text("Version 2")

        controller = GitController(str(tmp_path))

        # Commit modification
        commit_hash = controller.commit_changes(["test.txt"], "Update to version 2")

        assert commit_hash is not None
        commit = repo.commit(commit_hash)
        assert commit.message == "Update to version 2"

    def test_commit_in_subdirectory(self, tmp_path):
        """Commit files in subdirectory"""
        # Setup git repo
        git.Repo.init(tmp_path)

        # Create subdirectory and file
        subdir = tmp_path / "src"
        subdir.mkdir()
        test_file = subdir / "main.py"
        test_file.write_text("def main(): pass")

        controller = GitController(str(tmp_path))

        # Commit file in subdirectory
        commit_hash = controller.commit_changes(["src/main.py"], "Add main.py")

        assert commit_hash is not None

    def test_commit_with_special_characters_in_filename(self, tmp_path):
        """Commit file with special characters in name"""
        # Setup git repo
        git.Repo.init(tmp_path)

        # Create file with special chars
        test_file = tmp_path / "test file (1).txt"
        test_file.write_text("Content")

        controller = GitController(str(tmp_path))

        # Commit file
        commit_hash = controller.commit_changes(["test file (1).txt"], "Add file with spaces")

        assert commit_hash is not None


# ==============================================================================
# Error Handling Tests
# ==============================================================================


class TestGitControllerErrorHandling:
    """Test error handling in GitController"""

    def test_commit_nonexistent_file_returns_none(self, tmp_path):
        """Commit nonexistent file returns None"""
        # Setup git repo
        git.Repo.init(tmp_path)
        controller = GitController(str(tmp_path))

        # Try to commit nonexistent file
        result = controller.commit_changes(["nonexistent.txt"], "Attempt to commit")

        # Should return None (no changes to commit)
        assert result is None

    @patch("nexuscore.utils.vcs.git.Repo")
    def test_commit_with_git_error_returns_none(self, mock_repo_class, tmp_path):
        """Commit with git error returns None"""
        # Setup mock to raise exception on commit
        mock_repo = MagicMock()
        mock_repo.is_dirty.return_value = True
        mock_repo.index.commit.side_effect = git.GitCommandError("commit", "error")
        mock_repo_class.return_value = mock_repo

        controller = GitController(str(tmp_path))

        # Try to commit
        result = controller.commit_changes(["test.txt"], "Test commit")

        assert result is None

    @patch("nexuscore.utils.vcs.git.Repo")
    def test_commit_with_index_error_returns_none(self, mock_repo_class, tmp_path):
        """Commit with index add error returns None"""
        # Setup mock to raise exception on add
        mock_repo = MagicMock()
        mock_repo.is_dirty.return_value = True
        mock_repo.index.add.side_effect = Exception("Index error")
        mock_repo_class.return_value = mock_repo

        controller = GitController(str(tmp_path))

        # Try to commit
        result = controller.commit_changes(["test.txt"], "Test commit")

        assert result is None


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestGitControllerIntegration:
    """Integration tests with real git operations"""

    def test_multiple_commits_workflow(self, tmp_path):
        """Test workflow with multiple commits"""
        # Setup git repo
        repo = git.Repo.init(tmp_path)
        controller = GitController(str(tmp_path))

        # First commit
        file1 = tmp_path / "file1.txt"
        file1.write_text("Content 1")
        hash1 = controller.commit_changes(["file1.txt"], "First commit")

        # Second commit
        file2 = tmp_path / "file2.txt"
        file2.write_text("Content 2")
        hash2 = controller.commit_changes(["file2.txt"], "Second commit")

        # Third commit (modify file1)
        file1.write_text("Updated content 1")
        hash3 = controller.commit_changes(["file1.txt"], "Update file1")

        assert hash1 is not None
        assert hash2 is not None
        assert hash3 is not None
        assert hash1 != hash2 != hash3

        # Verify commits exist in order
        commits = list(repo.iter_commits())
        assert len(commits) == 3
        assert commits[0].message == "Update file1"
        assert commits[1].message == "Second commit"
        assert commits[2].message == "First commit"

    def test_commit_and_verify_content(self, tmp_path):
        """Commit file and verify its content in repository"""
        # Setup git repo
        repo = git.Repo.init(tmp_path)
        controller = GitController(str(tmp_path))

        # Create and commit file
        test_content = "This is test content\\nWith multiple lines\\n"
        test_file = tmp_path / "test.txt"
        test_file.write_text(test_content)

        commit_hash = controller.commit_changes(["test.txt"], "Add test content")

        assert commit_hash is not None

        # Verify content in commit
        commit = repo.commit(commit_hash)
        blob = commit.tree / "test.txt"
        assert blob.data_stream.read().decode("utf-8") == test_content

    def test_commit_binary_file(self, tmp_path):
        """Commit binary file"""
        # Setup git repo
        git.Repo.init(tmp_path)
        controller = GitController(str(tmp_path))

        # Create binary file
        binary_file = tmp_path / "image.bin"
        binary_data = bytes([0, 1, 2, 3, 255, 254, 253])
        binary_file.write_bytes(binary_data)

        # Commit binary file
        commit_hash = controller.commit_changes(["image.bin"], "Add binary file")

        assert commit_hash is not None

    def test_commit_empty_file(self, tmp_path):
        """Commit empty file"""
        # Setup git repo
        git.Repo.init(tmp_path)
        controller = GitController(str(tmp_path))

        # Create empty file
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")

        # Commit empty file
        commit_hash = controller.commit_changes(["empty.txt"], "Add empty file")

        assert commit_hash is not None


# ==============================================================================
# Edge Cases Tests
# ==============================================================================


class TestGitControllerEdgeCases:
    """Test edge cases and special scenarios"""

    def test_commit_with_empty_message(self, tmp_path):
        """Commit with empty message"""
        # Setup git repo
        repo = git.Repo.init(tmp_path)
        controller = GitController(str(tmp_path))

        # Create file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Content")

        # Commit with empty message
        commit_hash = controller.commit_changes(["test.txt"], "")

        assert commit_hash is not None
        commit = repo.commit(commit_hash)
        assert commit.message == ""

    def test_commit_empty_file_list(self, tmp_path):
        """Commit with empty file list"""
        # Setup git repo
        git.Repo.init(tmp_path)
        controller = GitController(str(tmp_path))

        # Try to commit empty list
        result = controller.commit_changes([], "Empty commit")

        # Should return None (no files to commit)
        assert result is None

    def test_commit_same_file_twice(self, tmp_path):
        """Commit same file listed twice"""
        # Setup git repo
        git.Repo.init(tmp_path)
        controller = GitController(str(tmp_path))

        # Create file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Content")

        # Commit with duplicate entry
        commit_hash = controller.commit_changes(["test.txt", "test.txt"], "Duplicate entry")

        assert commit_hash is not None
        # Should still work (git handles duplicates)

    def test_is_dirty_check_with_specific_paths(self, tmp_path):
        """Test is_dirty with specific file paths"""
        # Setup git repo
        repo = git.Repo.init(tmp_path)

        # Create and commit file1
        file1 = tmp_path / "file1.txt"
        file1.write_text("Content 1")
        repo.index.add(["file1.txt"])
        repo.index.commit("Initial commit")

        # Create file2 (not committed)
        file2 = tmp_path / "file2.txt"
        file2.write_text("Content 2")

        controller = GitController(str(tmp_path))

        # file1 is not dirty (no changes since commit)
        result1 = controller.commit_changes(["file1.txt"], "No changes")
        assert result1 is None

        # file2 is dirty (new file)
        result2 = controller.commit_changes(["file2.txt"], "New file")
        assert result2 is not None
