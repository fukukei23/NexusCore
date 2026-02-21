"""
4.5: Flask SaaS UI - External API テスト UI のスモークテスト（リファクタ版）

注意: このテストファイルは Flask レガシー前提です。
CR-FASTAPI-010 で Flask API が削除されたため、このテストファイルは skip されます。
FastAPI 側のテストは tests/api/test_fastapi_*.py を参照してください。
"""
import pytest

# CR-FASTAPI-010: Flask レガシー前提のテストは削除済み
# FastAPI 側のテストは tests/api/test_fastapi_*.py を参照してください
pytest.skip(
    "Flask legacy api_test_ui tests have been removed in CR-FASTAPI-010. "
    "Use FastAPI tests in tests/api/test_fastapi_*.py instead.",
    allow_module_level=True
)


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
