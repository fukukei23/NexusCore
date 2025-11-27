"""mock_github_pr_webhook.py のテスト"""
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# tools/ はプロジェクトルートから直接インポート可能
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# tools ディレクトリをパスに追加
tools_dir = project_root / "tools"
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

from mock_github_pr_webhook import build_sample_payload


def test_build_sample_payload():
    """build_sample_payload が正しい構造のペイロードを生成するテスト"""
    payload = build_sample_payload("owner/repo", 123, "abc123def456")

    assert payload["action"] == "opened"
    assert payload["number"] == 123
    assert payload["repository"]["full_name"] == "owner/repo"
    assert payload["repository"]["name"] == "repo"
    assert payload["repository"]["owner"]["login"] == "owner"
    assert payload["pull_request"]["number"] == 123
    assert payload["pull_request"]["head"]["sha"] == "abc123def456"
    assert payload["pull_request"]["head"]["ref"] == "refs/pull/123/head"
    assert payload["pull_request"]["base"]["ref"] == "main"


def test_build_sample_payload_with_slash_in_repo():
    """リポジトリ名にスラッシュが含まれる場合のテスト"""
    payload = build_sample_payload("owner/sub-repo", 456, "xyz789")

    assert payload["repository"]["full_name"] == "owner/sub-repo"
    assert payload["repository"]["name"] == "sub-repo"
    assert payload["repository"]["owner"]["login"] == "owner"


@patch('tools.mock_github_pr_webhook.requests')
def test_mock_webhook_imports_requests(mock_requests):
    """requests ライブラリがインポートできることを確認"""
    # インポート時に requests がチェックされる
    import tools.mock_github_pr_webhook
    assert hasattr(tools.mock_github_pr_webhook, 'requests')

