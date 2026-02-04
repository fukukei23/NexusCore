"""
Test script to verify the coverage implementation works correctly.
"""
import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

# Add the source directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from nexuscore.agents.tester_agent import TesterAgent


def test_get_coverage_no_file():
    """Test that _get_coverage_for_module returns 0.0 when no coverage file exists."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        agent = TesterAgent(project_root=tmp_dir)
        coverage = agent._get_coverage_for_module("test_module")
        assert coverage == 0.0, f"Expected 0.0, got {coverage}"
        print("✓ _get_coverage_for_module returns 0.0 when no coverage file exists")


def test_run_tests_with_proper_mock():
    """Test that _run_tests_and_get_coverage works with proper subprocess mocking."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        agent = TesterAgent(project_root=tmp_dir)
        test_file = Path(tmp_dir) / "test_example.py"
        test_file.write_text("def test_example():\n    assert True\n")

        # Create proper mocks for subprocess.run
        def mock_run_side_effect(args, **kwargs):
            if "coverage" in args and "json" in args:
                # coverage json command
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = '{"totals": {"percent_covered": 85.5}}'
                mock_result.stderr = ""
                return mock_result
            else:
                # coverage run pytest command
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = ""
                mock_result.stderr = ""
                return mock_result

        with patch('subprocess.run', side_effect=mock_run_side_effect):
            coverage = agent._run_tests_and_get_coverage("test_module", test_file)
            assert coverage == 85.5, f"Expected 85.5, got {coverage}"
            print("✓ _run_tests_and_get_coverage returns proper coverage value")


def test_run_tests_failure_handling():
    """Test that _run_tests_and_get_coverage handles test failures correctly."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        agent = TesterAgent(project_root=tmp_dir)
        test_file = Path(tmp_dir) / "test_fail.py"
        test_file.write_text("def test_fail():\n    assert False\n")

        def mock_run_side_effect(args, **kwargs):
            if "coverage" in args and "json" in args:
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = '{"totals": {"percent_covered": 50.0}}'
                mock_result.stderr = ""
                return mock_result
            else:
                mock_result = Mock()
                mock_result.returncode = 1  # Test failure
                mock_result.stdout = ""
                mock_result.stderr = "Test failed"
                return mock_result

        with patch('subprocess.run', side_effect=mock_run_side_effect):
            coverage = agent._run_tests_and_get_coverage("test_module", test_file)
            # Even if tests fail, we should get coverage if JSON is valid
            assert coverage == 50.0, f"Expected 50.0, got {coverage}"
            print("✓ _run_tests_and_get_coverage handles test failures correctly")


def test_module_coverage_extraction():
    """Test that _get_coverage_for_module can extract specific module coverage."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        agent = TesterAgent(project_root=tmp_dir)

        # Create a mock .coverage file
        coverage_file = Path(tmp_dir) / ".coverage"
        coverage_file.write_text("")

        def mock_run_side_effect(args, **kwargs):
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = '''{
                "files": {
                    "src/nexuscore/utils/helper.py": {
                        "summary": {"percent_covered": 90.0}
                    }
                },
                "totals": {"percent_covered": 75.0}
            }'''
            mock_result.stderr = ""
            return mock_result

        with patch('subprocess.run', side_effect=mock_run_side_effect):
            coverage = agent._get_coverage_for_module("helper")
            assert coverage == 90.0, f"Expected 90.0, got {coverage}"
            print("✓ _get_coverage_for_module extracts specific module coverage")


if __name__ == "__main__":
    print("Running coverage implementation tests...\n")

    try:
        test_get_coverage_no_file()
        test_run_tests_with_proper_mock()
        test_run_tests_failure_handling()
        test_module_coverage_extraction()

        print("\n✅ All coverage implementation tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
