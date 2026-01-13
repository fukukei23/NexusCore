"""
Pytest configuration for agents tests.

This conftest.py prevents collection of test files with missing dependencies.
"""
import os
import pytest


def pytest_collection_modifyitems(session, config, items):
    """Skip collection of test files with missing dependencies."""
    pass


def pytest_ignore_collect(collection_path, config):
    """
    Ignore specific test files that have missing dependencies.

    This hook is only active when NEXUS_MUTATION_TEST=1 is set.
    Otherwise, it returns False to allow all tests to be collected normally.

    This prevents pytest from attempting to import test files that require
    unavailable dependencies (e.g., 'patch' module) during mutation testing.

    Note: This hook only applies to tests/agents/ directory.
    The root tests/conftest.py handles the broader collection control.
    """
    path_str = str(collection_path)

    # この conftest.py は tests/agents/ 配下のファイルに対してのみ適用
    if "/tests/agents/" not in path_str and "tests/agents/" not in path_str:
        # tests/agents/ 以外のファイルには適用しない（root conftest.py に任せる）
        return False

    # 通常の pytest 実行時は何もしない（全テストを収集可能にする）
    if os.getenv("NEXUS_MUTATION_TEST") != "1":
        return False

    # mutmut 実行時のみ、特定ファイルを除外
    # Files to ignore due to missing 'patch' module dependency
    ignore_files = [
        "test_knowledge_curator_agent.py",
        "test_knowledge_curator_agent_ultimate.py",
        "test_patch_applier.py",
    ]

    if collection_path.name in ignore_files:
        return True

    return False
