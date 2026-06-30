"""utils.py の純粋関数テスト。"""
from pathlib import Path
from brownfield import utils as U

def test_repo_root_resolves_to_nexuscore_root():
    """REPO_ROOT は NexusCore 仓库根（.git があるディレクトリ）。"""
    assert (U.REPO_ROOT / ".git").exists() or (U.REPO_ROOT / "pyproject.toml").exists()
    assert U.REPO_ROOT.name == "NexusCore"

def test_package_dir_is_brownfield():
    assert U.PACKAGE_DIR.name == "brownfield"
    assert U.PACKAGE_DIR.parent.name == "tools"

def test_detect_latest_snapshot_empty(tmp_path):
    """存在しない/空ディレクトリは空文字列。"""
    assert U.detect_latest_snapshot(str(tmp_path / "noexist")) == ""
    assert U.detect_latest_snapshot(str(tmp_path)) == ""

def test_detect_latest_snapshot_picks_newest(tmp_path):
    (tmp_path / "20260701_120000").mkdir()
    (tmp_path / "20260701_180000").mkdir()
    result = U.detect_latest_snapshot(str(tmp_path))
    assert result.endswith("20260701_180000")

def test_constants_values():
    assert "structure" in U.PHASE_KEYS
    assert "ai_export" in U.PHASE_KEYS
    assert "gemini-single-file" in U.DEFAULT_PROFILES
    assert U.DEFAULT_OUT == U.REPO_ROOT / "brownfield_snapshots"
    assert U.ORCHESTRATOR_MODULE_NAME == "nexuscore.core.orchestrator"
