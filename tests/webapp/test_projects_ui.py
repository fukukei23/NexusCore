"""
4.5: Flask SaaS UI - プロジェクト一覧・詳細のスモークテスト（リファクタ版）

HTTP 500 が出ないことと、Self-Healing メトリクス系の重要な文字列が必ず含まれていることを検証する。

共通ヘルパーと UI キーワード表を使用して、保守性を向上。
"""

from __future__ import annotations

import pytest

from tests.webapp.helpers import assert_page_keywords, login_user
from tests.webapp.ui_keywords import PROJECTS_PAGE_KEYWORDS, PROJECT_DETAIL_KEYWORDS


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
