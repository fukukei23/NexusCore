"""C4: /api/v1/execute project_path バリデーションのテスト（2026-08-05）.

パスインジェクション型IDOR対策。機密システムパス・機密ディレクトリ・
シンボリックリンク攻撃を拒否し、正当なプロジェクトパスは許可する。
"""
import os

import pytest

from nexuscore.api.routes.execute import validate_project_path


class TestRejectsSystemPaths:
    """機密システムパス配下を拒否する（realpath 解決後・前方一致）."""

    @pytest.mark.parametrize(
        "forbidden_path",
        [
            "/etc",
            "/etc/passwd",
            "/etc/nginx/nginx.conf",
            "/root",
            "/root/.bashrc",
            "/var/log/syslog",
            "/proc/1",
            "/sys/kernel",
            "/usr/bin/python",
            "/boot/vmlinuz",
            "/bin/sh",
            "/lib/libc.so",
        ],
    )
    def test_rejects_system_paths(self, forbidden_path: str):
        with pytest.raises(ValueError, match="機密システムパス"):
            validate_project_path(forbidden_path)


class TestRejectsSensitiveDirNames:
    """クレデンシャル配置ディレクトリ（.ssh/.gnupg/.aws）を含むパスを拒否する."""

    @pytest.mark.parametrize(
        "sensitive_path",
        [
            "/home/user/.ssh/config",
            "/home/user/.gnupg/pubring.kbx",
            "/home/user/.aws/credentials",
            "/tmp/project/.ssh/key",
            "/tmp/proj/.aws/cred",
            "/home/user/.gnupg",
        ],
    )
    def test_rejects_sensitive_dir_names(self, sensitive_path: str):
        with pytest.raises(ValueError, match="機密ディレクトリ"):
            validate_project_path(sensitive_path)


class TestAllowsValidPaths:
    """正当なプロジェクトパスは許可する（既存テストの /tmp/test を含む）."""

    @pytest.mark.parametrize(
        "valid_path",
        [
            "/tmp/test",
            "/tmp/my-project",
            "/home/user/projects/myapp",
            "/workspace/repo",
            "/tmp/does-not-exist-12345",  # 実在しなくてもパス文字列として検証
        ],
    )
    def test_allows_valid_paths(self, valid_path: str):
        result = validate_project_path(valid_path)
        assert result == os.path.realpath(valid_path)
        assert result.startswith(("/", ))

    def test_returns_resolved_absolute_path(self):
        """相対パスや .. を含む入力も realpath で絶対解決して返す."""
        result = validate_project_path("/tmp/./test/../myapp")
        assert os.path.isabs(result)
        assert result == os.path.realpath("/tmp/./test/../myapp")


class TestSymlinkAttackMitigation:
    """シンボリックリンクで機密パスを指す攻撃を realpath で回避する."""

    def test_rejects_symlink_to_forbidden(self, tmp_path):
        evil_link = tmp_path / "evil-to-etc"
        os.symlink("/etc", str(evil_link))
        with pytest.raises(ValueError, match="機密システムパス"):
            validate_project_path(str(evil_link))

    def test_rejects_symlink_to_ssh(self, tmp_path):
        ssh_dir = tmp_path / "fakehome" / ".ssh"
        ssh_dir.mkdir(parents=True)
        evil_link = tmp_path / "evil-to-ssh"
        os.symlink(str(ssh_dir), str(evil_link))
        with pytest.raises(ValueError, match="機密ディレクトリ"):
            validate_project_path(str(evil_link))
