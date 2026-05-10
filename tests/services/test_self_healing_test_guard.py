"""self_healing_service.py のテストガード（tests/ ブロック）のテスト"""

from unittest import mock
from unittest.mock import MagicMock

from nexuscore.services.self_healing_service import SelfHealingService


def test_patch_blocked_when_modifies_tests_dir(tmp_path):
    """tests/ ディレクトリ配下のファイルを変更するパッチがブロックされるテスト"""
    debugger_agent = MagicMock()
    test_patch = """--- a/tests/test_example.py
+++ b/tests/test_example.py
@@ -1,3 +1,3 @@
 def test_example():
-    assert False
+    assert True
"""

    debugger_agent.debug_and_patch = MagicMock(return_value={"patch": test_patch})

    service = SelfHealingService(
        project_root=str(tmp_path),
        debugger_agent=debugger_agent,
    )

    project_path = tmp_path / ".nexus" / "self_healing_sandbox" / "owner_repo_pr_123"
    project_path.mkdir(parents=True)

    with mock.patch("nexuscore.services.self_healing_service.clone_or_update_repo"):
        with mock.patch("nexuscore.services.self_healing_service.run_tests", return_value=(False, "Test failed")):
            result = service.run_for_pull_request(
                repo_full_name="owner/repo",
                pr_number=123,
                head_sha="abc123",
            )

    assert result["status"] == "not_fixed"
    assert "modifies test files" in result["summary"].lower()
    assert "blocked_test_paths" in result["details"]
    assert "b/tests/test_example.py" in result["details"]["blocked_test_paths"]


def test_patch_blocked_when_modifies_test_file(tmp_path):
    """test_*.py ファイルを変更するパッチがブロックされるテスト"""
    debugger_agent = MagicMock()
    test_patch = """--- a/src/test_helper.py
+++ b/src/test_helper.py
@@ -1,1 +1,1 @@
-old
+new
"""

    debugger_agent.debug_and_patch = MagicMock(return_value={"patch": test_patch})

    service = SelfHealingService(
        project_root=str(tmp_path),
        debugger_agent=debugger_agent,
    )

    project_path = tmp_path / ".nexus" / "self_healing_sandbox" / "owner_repo_pr_123"
    project_path.mkdir(parents=True)

    with mock.patch("nexuscore.services.self_healing_service.clone_or_update_repo"):
        with mock.patch("nexuscore.services.self_healing_service.run_tests", return_value=(False, "Test failed")):
            result = service.run_for_pull_request(
                repo_full_name="owner/repo",
                pr_number=123,
                head_sha="abc123",
            )

    assert result["status"] == "not_fixed"
    assert "modifies test files" in result["summary"].lower()
    assert "blocked_test_paths" in result["details"]
    assert "b/src/test_helper.py" in result["details"]["blocked_test_paths"]


def test_patch_allowed_when_no_test_files(tmp_path):
    """テストファイルを変更しないパッチは許可されるテスト"""
    debugger_agent = MagicMock()
    safe_patch = """--- a/src/module.py
+++ b/src/module.py
@@ -1,1 +1,1 @@
-old
+new
"""

    debugger_agent.debug_and_patch = MagicMock(return_value={"patch": safe_patch})

    service = SelfHealingService(
        project_root=str(tmp_path),
        debugger_agent=debugger_agent,
    )

    project_path = tmp_path / ".nexus" / "self_healing_sandbox" / "owner_repo_pr_123"
    project_path.mkdir(parents=True)

    (project_path / "src" / "module.py").parent.mkdir(parents=True)
    (project_path / "src" / "module.py").write_text("old\n")

    with mock.patch("nexuscore.services.self_healing_service.clone_or_update_repo"):
        with mock.patch(
            "nexuscore.services.self_healing_service.run_tests",
            side_effect=[(False, "Test failed"), (True, "All tests passed")],
        ):
            result = service.run_for_pull_request(
                repo_full_name="owner/repo",
                pr_number=123,
                head_sha="abc123",
            )

    assert "blocked_test_paths" not in result.get("details", {})


def test_patch_blocked_with_multiple_test_files(tmp_path):
    """複数のテストファイルを変更するパッチがブロックされるテスト"""
    debugger_agent = MagicMock()
    test_patch = """--- a/tests/test_a.py
+++ b/tests/test_a.py
@@ -1,1 +1,1 @@
-old
+new
--- a/tests/test_b.py
+++ b/tests/test_b.py
@@ -1,1 +1,1 @@
-old
+new
"""

    debugger_agent.debug_and_patch = MagicMock(return_value={"patch": test_patch})

    service = SelfHealingService(
        project_root=str(tmp_path),
        debugger_agent=debugger_agent,
    )

    project_path = tmp_path / ".nexus" / "self_healing_sandbox" / "owner_repo_pr_123"
    project_path.mkdir(parents=True)

    with mock.patch("nexuscore.services.self_healing_service.clone_or_update_repo"):
        with mock.patch("nexuscore.services.self_healing_service.run_tests", return_value=(False, "Test failed")):
            result = service.run_for_pull_request(
                repo_full_name="owner/repo",
                pr_number=123,
                head_sha="abc123",
            )

    assert result["status"] == "not_fixed"
    blocked_paths = result["details"]["blocked_test_paths"]
    assert len(blocked_paths) == 2
    assert "b/tests/test_a.py" in blocked_paths
    assert "b/tests/test_b.py" in blocked_paths
