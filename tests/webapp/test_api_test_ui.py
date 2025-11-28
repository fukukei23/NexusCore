"""
4.5: Flask SaaS UI - External API テスト UI のスモークテスト（リファクタ版）

HTTP 500 が出ないことと、重要な文字列が必ず含まれていることを検証する。

共通ヘルパーと UI キーワード表を使用して、保守性を向上。
"""

from __future__ import annotations

import pytest

from tests.webapp.helpers import assert_page_keywords, login_user
from tests.webapp.ui_keywords import API_TEST_PAGE_KEYWORDS


def test_api_test_page_renders(client, app, test_user, test_project, test_api_key):
    """API Test ページ（/api-test/）が 200 を返し、重要な文字列が含まれていることを確認"""
    with app.app_context():
        login_user(client, test_user)
        response = client.get("/api-test/")
        assert_page_keywords(response, API_TEST_PAGE_KEYWORDS)


def test_api_test_page_shows_project_select(client, app, test_user, test_project):
    """API Test ページにプロジェクト選択が表示されることを確認"""
    with app.app_context():
        login_user(client, test_user)
        response = client.get("/api-test/")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "Test Project" in html


def test_api_test_page_without_api_keys(client, app, test_user, test_project):
    """API Key がない場合でも API Test ページが 200 を返すことを確認"""
    with app.app_context():
        login_user(client, test_user)
        response = client.get("/api-test/")
        assert_page_keywords(response, ["API Test"])


def test_api_test_page_post_handles_missing_fields(client, app, test_user, test_project):
    """API Test ページの POST で必須フィールドが欠けている場合でも 500 にならないことを確認"""
    with app.app_context():
        login_user(client, test_user)
        response = client.post("/api-test/", data={
            "requirement": "Test requirement",
        })
        # 200 を確認（エラーメッセージが表示されるが、500 にはならない）
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        # エラーメッセージまたはフォームが含まれていることを確認
        assert "API Test" in html or "error" in html.lower() or "required" in html.lower()
