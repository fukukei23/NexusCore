"""
E2E テスト用 conftest.py

fixtures/test_db.py で定義された fixture を tests/e2e/ 全体で利用可能にする。
"""

import os

import pytest

from tests.e2e.fixtures.test_db import e2e_test_api_key  # noqa: F401


@pytest.fixture(autouse=True, scope="session")
def _set_e2e_api_key(e2e_test_api_key):
    """E2E テスト全体で NEXUSCORE_API_KEY 環境変数を設定する"""
    os.environ["NEXUSCORE_API_KEY"] = e2e_test_api_key
