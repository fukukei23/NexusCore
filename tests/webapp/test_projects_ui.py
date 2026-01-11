"""
4.5: Flask SaaS UI - プロジェクト一覧・詳細のスモークテスト（リファクタ版）

注意: このテストファイルは Flask レガシー前提です。
CR-FASTAPI-010 で Flask API が削除されたため、このテストファイルは skip されます。
FastAPI 側のテストは tests/api/test_fastapi_*.py を参照してください。
"""
import pytest

# CR-FASTAPI-010: Flask レガシー前提のテストは削除済み
# FastAPI 側のテストは tests/api/test_fastapi_*.py を参照してください
pytest.skip(
    "Flask legacy projects_ui tests have been removed in CR-FASTAPI-010. "
    "Use FastAPI tests in tests/api/test_fastapi_*.py instead.",
    allow_module_level=True
)


def test_projects_index_renders_with_cards(client, app, test_user, test_project, test_run_with_metrics):
    """プロジェクト一覧ページ（/projects/）が 200 を返し、カード形式で表示されることを確認"""
    with app.app_context():
        login_user(client, test_user)
        response = client.get("/projects/")
        assert_page_keywords(response, PROJECTS_PAGE_KEYWORDS)


def test_projects_index_shows_metrics(client, app, test_user, test_project, test_run_with_metrics):
    """プロジェクト一覧ページにメトリクス（Exec Time, Retry Count）が表示されることを確認"""
    with app.app_context():
        login_user(client, test_user)
        response = client.get("/projects/")
        assert_page_keywords(response, ["Exec Time", "Retry"])


def test_project_detail_renders_with_metrics(client, app, test_user, test_project, test_run_with_metrics):
    """プロジェクト詳細ページ（/projects/<id>）が 200 を返し、メトリクスセクションが含まれることを確認"""
    with app.app_context():
        login_user(client, test_user)
        response = client.get(f"/projects/{test_project.id}")
        assert_page_keywords(response, PROJECT_DETAIL_KEYWORDS)


def test_project_detail_shows_metrics_section(client, app, test_user, test_project, test_run_with_metrics):
    """プロジェクト詳細ページに「Metrics (Last 30 Runs)」セクションが表示されることを確認"""
    with app.app_context():
        login_user(client, test_user)
        response = client.get(f"/projects/{test_project.id}")
        assert_page_keywords(response, ["Metrics (Last 30 Runs)"])


def test_projects_index_without_runs(client, app, test_user, test_project):
    """プロジェクト一覧ページが Run がない場合でも 200 を返すことを確認"""
    with app.app_context():
        login_user(client, test_user)
        response = client.get("/projects/")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "Test Project" in html
